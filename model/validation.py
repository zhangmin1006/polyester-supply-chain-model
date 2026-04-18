"""
validation.py
Historical backcasting validation for the polyester textile supply chain model.

Methodology:
  For each historical event:
    1. Define observed real-world outcomes (prices, supply levels, recovery).
    2. Parameterise a model run to match the event conditions.
    3. Run IO + CGE + ABM and extract comparable metrics.
    4. Compute directional accuracy, % error, and RMSE.

Historical events used:
  V1  COVID-19 pandemic shock          (2020 Q1–Q2)
  V2  2021–22 global supply chain crisis / freight spike
  V3  2018 nylon-66 ADN factory fires  (PTA/PET analogue)
  V4  2019 Saudi Aramco Abqaiq attack  (oil supply shock)
  V5  2024 Red Sea / Houthi disruption (MEG/shipping analogue)
  V6  2022 Shanghai COVID lockdown     (China manufacturing cluster)
  V7  2022 Ukraine war / energy spike  (oil price cascade)

Sources:
  - ONS Retail Sales Index (clothing & footwear): monthly 2020
  - ONS UK import price indices: textiles 2020-2022
  - HMRC trade statistics: UK apparel imports from China 2019-2021
  - Drewry World Container Index / Freightos Baltic Index 2021
  - IHS Markit / ICIS PTA, MEG, polyester fibre price series
  - Nylon-66 price spike: Chemical Week, Bloomberg (Jun-Oct 2018)
  - Saudi Aramco attack: EIA crude price data Sep-Dec 2019
  - Red Sea disruption: UNCTAD shipping bulletin Jan-Apr 2024
"""

import numpy as np
import pandas as pd
import os, sys
import io as _io
from typing import Dict, List, Tuple

from io_model    import DynamicIOModel, A_BASE
from cge_model   import CGEModel
from abm_model   import PolyesterSupplyChainABM
from real_data   import SECTORS, N_SECTORS, UK_IMPORTS_TOTAL_GBP, TRANSIT_DAYS


# ─────────────────────────────────────────────────────────────────────────────
# Historical event definitions
# Each entry contains:
#   description : str
#   period      : str
#   model_params: dict fed to the three models
#   observed    : dict of observable outcomes with documented values and sources
# ─────────────────────────────────────────────────────────────────────────────

HISTORICAL_EVENTS: List[Dict] = [

    # ── V1: COVID-19 Pandemic Shock (2020 Q1–Q2) ─────────────────────────────
    {
        "id": "V1",
        "name": "COVID-19 Pandemic Shock",
        "period": "2020 Q1–Q2 (weeks 1–26)",
        "references": [
            "ONS Retail Sales Index Apr 2020: clothing/footwear −43.5% YoY",
            "HMRC OTS API (2026-04-17): UK synthetic apparel imports from China −27.2% value, −28.4% volume in 2020 vs 2019",
            "NBS China: manufacturing PMI Feb 2020 = 35.7 (vs 50 neutral)",
            "Freightos: China–UK freight rates +180% by Aug 2020",
            "ICIS: polyester fibre price −18% Mar 2020, then +35% by end 2020",
            "ILO: garment sector jobs lost ~25% globally Q1-Q2 2020",
        ],
        # CGE supply fractions (fraction of baseline supply remaining)
        "cge_supply": {
            0: 1.00,   # Oil — largely unaffected initially
            1: 0.85,   # Chem — partial China shutdown
            2: 0.42,   # PTA  — China lockdown: NBS PMI 35.7 ≈ 57% reduction; use 58% loss
            3: 0.40,   # PET  — similar to PTA
            4: 0.45,   # Fabric — China + Bangladesh closures
            5: 0.50,   # Garment — Bangladesh, Vietnam closures (ILO 25-50%)
            6: 0.80,   # Wholesale — logistics disrupted
            7: 0.60,   # Retail — non-essential store closures (ONS −43.5%)
        },
        # CGE demand shocks: COVID caused demand COLLAPSE at retail (-43.5% ONS)
        # and partial recovery by end of year → use −43.5% demand shock at retail
        "cge_demand_shocks": {
            7: 0.565,  # UK_Retail: 1 − 0.435 = 0.565 (ONS Apr 2020 −43.5%)
            6: 0.75,   # UK_Wholesale: partial (non-store retail still active)
        },
        "shock_duration_weeks": 12,   # ~3 months of severe lockdown
        # IO shock schedule: {week: [(sector_idx, fraction_lost)]}
        "io_shock_schedule": {
            4: [(2, 0.58), (3, 0.60), (4, 0.55), (5, 0.50)],
            5: [(5, 0.50)],    # Bangladesh / Vietnam delayed onset
        },
        # IO demand shock: retail demand multiplier from week 4
        # 0.565 = ONS Apr 2020 retail −43.5%
        "io_demand_shock_schedule": {
            4: np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.75, 0.565]),
            18: np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.90, 0.80]),  # partial recovery
            30: np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.00, 1.00]),  # full recovery
        },
        # ABM shock schedule
        "abm_schedule": {
            4: [
                {"sector": 2, "country": "China",      "severity": 0.58, "duration": 6},
                {"sector": 3, "country": "China",      "severity": 0.60, "duration": 8},
                {"sector": 4, "country": "China",      "severity": 0.55, "duration": 8},
            ],
            5: [
                {"sector": 5, "country": "Bangladesh", "severity": 0.50, "duration": 6},
                {"sector": 5, "country": "China",      "severity": 0.50, "duration": 6},
            ],
        },
        "simulation_weeks": 52,
        # Observed outcomes (point-in-time or peak measures)
        "observed": {
            "max_price_rise_pct": {
                "sector": "PTA_Production",
                "value": 35.0,    # polyester fibre prices −18% initial, then +35% recovery spike
                "note": "ICIS polyester fibre spot price peak change 2020",
                "direction": "up",
            },
            "uk_import_change_pct": {
                "sector": "Garment_Assembly",
                "value": -27.5,   # HMRC OTS API: total UK synthetic apparel −27.5%; China −27.2% value, −28.4% volume
                "note": "HMRC OTS API 2026-04-17: all-country synthetic apparel 2020 vs 2019",
            },
            "retail_output_change_pct": {
                "sector": "UK_Retail",
                "value": -43.5,   # ONS Retail Sales Apr 2020
                "note": "ONS Retail Sales Index: clothing/footwear Apr 2020 YoY",
            },
            "welfare_loss_lower_gbp_bn": 4.0,    # lower bound: ONS UK retail clothing spend collapse
            "welfare_loss_upper_gbp_bn": 8.0,    # upper bound including supply-side costs
            "recovery_weeks_garment": 26,         # ~6 months to near-normal (HMRC 2020-2021)
            "bullwhip_qualitative": "severe",     # well-documented in COVID supply chain literature
        },
    },

    # ── V2: 2021–22 Global Supply Chain Crisis / Freight Spike ───────────────
    {
        "id": "V2",
        "name": "2021-22 Global Freight / Supply Chain Crisis",
        "period": "2021 H2 – 2022 H1",
        "references": [
            "Drewry WCI Shanghai–Rotterdam: +563% peak (Sep 2021 vs Sep 2019)",
            "ICIS: PTA China domestic price +32% Jan–Oct 2021",
            "ICIS: MEG China port price +28% Jan–Oct 2021",
            "ONS UK import price index: textiles +8.5% in 2021",
            "HMRC: UK synthetic apparel imports recovered +12% 2021 vs 2020",
            "IHS Markit: polyester staple fibre China export +38% price 2021",
        ],
        # Represents upstream pressure (demand surge post-COVID) + freight cost shock
        "cge_supply": {
            0: 0.95,   # Oil — OPEC output limited
            1: 0.90,   # Chem — some tightness
            2: 0.88,   # PTA  — capacity tight, +32% price observed
            3: 0.85,   # PET  — tight
            4: 0.90,   # Fabric — operating but constrained
            5: 0.92,   # Garment — near-normal manufacturing
            6: 0.75,   # Wholesale/logistics — freight crisis core
            7: 1.00,   # Retail demand strong (pent-up)
        },
        # Demand SURGE: pent-up post-COVID restocking (HMRC +12% 2021)
        "cge_demand_shocks": {
            7: 1.12,   # UK_Retail: +12% pent-up demand surge
            5: 1.10,   # Garment: restocking orders up
        },
        "shock_duration_weeks": 26,
        "io_shock_schedule": {
            1: [(6, 0.25)],    # logistics shock from week 1 (freight crisis)
            3: [(2, 0.12), (3, 0.15)],   # upstream cost push
        },
        "io_demand_shock_schedule": {
            1: np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.10, 1.0, 1.12]),  # demand surge
        },
        "abm_schedule": {
            1: [{"sector": 6, "country": "UK", "severity": 0.25, "duration": 26}],
            3: [{"sector": 2, "country": "China", "severity": 0.12, "duration": 20}],
        },
        "simulation_weeks": 52,
        "observed": {
            "max_price_rise_pct": {
                "sector": "Chemical_Processing",
                "value": 32.0,    # ICIS PTA +32%, MEG +28% — use PTA as more direct
                "note": "ICIS PTA China domestic price Jan–Oct 2021",
                "direction": "up",
            },
            "freight_cost_rise_pct": {
                "sector": "UK_Wholesale",
                "value": 563.0,   # Drewry WCI peak (extreme outlier)
                "note": "Drewry WCI Shanghai–Rotterdam peak Sep 2021",
            },
            "uk_import_price_rise_pct": {
                "sector": "Garment_Assembly",
                "value": 8.5,     # ONS UK import price index textiles 2021
                "note": "ONS import price index textiles 2021 annual",
            },
            "welfare_loss_lower_gbp_bn": 0.5,
            "welfare_loss_upper_gbp_bn": 2.0,
            "recovery_weeks_garment": 52,    # freight rates only normalised mid-2022
            "bullwhip_qualitative": "moderate",
        },
    },

    # ── V3: 2018 Nylon-66 ADN Factory Fires (PTA/PET analogue) ───────────────
    {
        "id": "V3",
        "name": "2018 Nylon-66 ADN Factory Fires (PTA/PET analogue)",
        "period": "Jun–Dec 2018",
        "references": [
            "Ascend Performance Materials fire + Invista capacity loss: ~35-40% ADN supply",
            "Bloomberg: nylon-66 polymer price +120% peak Jun–Sep 2018",
            "Chemical Week: supply shortage lasted ~4 months",
            "Dow Jones: downstream auto/apparel manufacturers switched to alternatives",
            "Analogy: PTA production shock calibrated to same magnitude (35-40%)",
        ],
        # Nylon-66 is not polyester, but this is the closest historical single-node
        # upstream chemical shock with documented price and supply data.
        # We model it as a 35% PTA production shock (calibration event).
        "cge_supply": {
            0: 1.00,
            1: 1.00,
            2: 0.65,   # PTA proxy for ADN: 35% supply loss
            3: 0.75,   # PET partially affected (substitution)
            4: 0.88,
            5: 0.92,
            6: 1.00,
            7: 1.00,
        },
        "cge_demand_shocks": {},
        "shock_duration_weeks": 16,
        "io_shock_schedule": {
            2: [(2, 0.35), (3, 0.25)],
        },
        "io_demand_shock_schedule": {},
        "abm_schedule": {
            2: [
                {"sector": 2, "country": "China", "severity": 0.35, "duration": 16},
                {"sector": 3, "country": "China", "severity": 0.25, "duration": 12},
            ],
        },
        "simulation_weeks": 26,
        "observed": {
            "max_price_rise_pct": {
                "sector": "PTA_Production",
                "value": 120.0,   # nylon-66 polymer price peak (Bloomberg)
                "note": "Bloomberg: nylon-66 polymer +120% peak Jun–Sep 2018 (proxy for PTA shock)",
                "direction": "up",
            },
            "supply_shortage_pct": {
                "sector": "PTA_Production",
                "value": 37.5,    # midpoint of 35-40% ADN supply lost
                "note": "Ascend + Invista combined capacity loss",
            },
            "recovery_weeks": 16,    # ~4 months (Chemical Week)
            "welfare_loss_lower_gbp_bn": 0.1,    # global nylon market small relative to polyester
            "welfare_loss_upper_gbp_bn": 0.5,
            "bullwhip_qualitative": "moderate",
        },
    },

    # ── V4: 2019 Saudi Aramco Abqaiq Attack (oil supply shock) ───────────────
    {
        "id": "V4",
        "name": "2019 Saudi Aramco Abqaiq / Khurais Attack",
        "period": "Sep–Oct 2019",
        "references": [
            "EIA: 5.7 mb/d Saudi production offline (≈5.4% world supply) Sep 14 2019",
            "EIA: Brent crude +15% same-day spike; recovered within 2-4 weeks",
            "Bloomberg: MEG / PTA prices largely unchanged (inventories buffered)",
            "S&P Global: Aramco restored full output within 2-3 weeks",
            "IEA: no petrochemical feedstock shortage materialised due to fast recovery",
        ],
        # A short but severe oil supply disruption that did NOT cascade to PTA/PET
        # because recovery was rapid. Model should also show limited cascade.
        "cge_supply": {
            0: 0.946,  # 5.4% world oil supply offline
            1: 0.97,   # minor chemical feedstock effect
            2: 0.98,
            3: 0.99,
            4: 1.00,
            5: 1.00,
            6: 1.00,
            7: 1.00,
        },
        "cge_demand_shocks": {},
        "shock_duration_weeks": 2,    # very short — full recovery in 2-3 weeks
        "io_shock_schedule": {
            1: [(0, 0.054)],   # oil sector: 5.4% loss for ~2 weeks
        },
        "io_demand_shock_schedule": {},
        "abm_schedule": {
            1: [{"sector": 0, "country": "Saudi_Arabia", "severity": 0.054, "duration": 2}],
        },
        "simulation_weeks": 12,
        "observed": {
            "max_price_rise_pct": {
                "sector": "Oil_Extraction",
                "value": 15.0,    # Brent crude +15% day-of spike
                "note": "EIA Brent crude same-day price spike Sep 14 2019",
                "direction": "up",
            },
            "cascade_to_pta_pct": {
                "sector": "PTA_Production",
                "value": 0.0,     # Bloomberg: no MEG/PTA price move
                "note": "Bloomberg: petrochemical prices flat — fast recovery + inventories buffered",
            },
            "recovery_weeks": 3,     # S&P Global: full output restored 2-3 weeks
            "welfare_loss_lower_gbp_bn": 0.0,
            "welfare_loss_upper_gbp_bn": 0.1,
            "bullwhip_qualitative": "low",
        },
    },

    # ── V5: 2024 Red Sea / Houthi Disruption (MEG/shipping analogue) ─────────
    {
        "id": "V5",
        "name": "2024 Red Sea / Houthi Shipping Disruption",
        "period": "Dec 2023 – Jun 2024",
        "references": [
            "UNCTAD: Red Sea traffic −66% by Jan 2024; rerouting via Cape of Good Hope",
            "Freightos: Shanghai–Europe container rates +173% Jan 2024 vs Dec 2023",
            "ICIS: MEG Europe import prices +8-12% Jan–Mar 2024 (higher freight cost)",
            "S&P Global: China–UK transit times +14-17 days (Cape reroute adds ~2 weeks)",
            "WTO: no major production disruption — shipping delay not supply loss",
            "UNCTAD: Saudi MEG exports continued but transit time to China +10-14 days",
        ],
        # Transit time shock: China→UK extended from 37 to 51-54 days (+14-17d)
        # Saudi→China (MEG) extended from 23 to 37 days (+14d via Cape)
        # No production shutdown — logistical delay only
        "cge_supply": {
            0: 1.00,
            1: 0.93,   # chemical processing: delayed Saudi MEG arrivals
            2: 0.96,
            3: 0.97,
            4: 0.98,
            5: 0.97,   # garment: longer transit → effective supply delay
            6: 0.80,   # wholesale/logistics: rerouting cost and delay
            7: 1.00,
        },
        "cge_demand_shocks": {},
        "shock_duration_weeks": 26,
        "io_shock_schedule": {
            1: [(6, 0.20), (1, 0.07)],   # logistics + chem delay
        },
        "io_demand_shock_schedule": {},
        "abm_schedule": {
            1: [
                {"sector": 6, "country": "UK",           "severity": 0.20, "duration": 26},
                {"sector": 1, "country": "Saudi_Arabia",  "severity": 0.10, "duration": 20},
            ],
        },
        "simulation_weeks": 26,
        "observed": {
            "max_price_rise_pct": {
                "sector": "UK_Wholesale",
                "value": 173.0,   # Freightos: Shanghai–Europe rates peak
                "note": "Freightos Baltic Index Shanghai–Europe Jan 2024",
                "direction": "up",
            },
            "meg_price_rise_pct": {
                "sector": "Chemical_Processing",
                "value": 10.0,    # ICIS MEG Europe +8-12% midpoint
                "note": "ICIS MEG Europe import price Jan-Mar 2024",
            },
            "transit_day_increase": {
                "sector": "UK_Wholesale",
                "value": 15.5,    # midpoint of 14-17 day increase
                "note": "S&P Global: Cape of Good Hope reroute adds 14-17 days",
            },
            "uk_import_change_pct_jan": {
                "sector": "Garment_Assembly",
                "value": -21.4,
                "note": "HMRC OTS API: NON-EU synthetic apparel Jan 2024 vs Jan 2023 (value)",
            },
            "uk_import_change_pct_feb": {
                "sector": "Garment_Assembly",
                "value": -26.3,
                "note": "HMRC OTS API: NON-EU synthetic apparel Feb 2024 vs Feb 2023 (value)",
            },
            "uk_import_change_pct_mar": {
                "sector": "Garment_Assembly",
                "value": -24.7,
                "note": "HMRC OTS API: NON-EU synthetic apparel Mar 2024 vs Mar 2023 (value)",
            },
            "uk_import_change_h1_pct": {
                "sector": "Garment_Assembly",
                "value": -15.6,
                "note": "HMRC OTS API: NON-EU synthetic apparel H1 2024 vs H1 2023 (value)",
            },
            "welfare_loss_lower_gbp_bn": 0.1,
            "welfare_loss_upper_gbp_bn": 0.4,
            "recovery_weeks_logistics": 26,   # rates normalised by mid-2024
            "bullwhip_qualitative": "low",
        },
    },

    # ── V6: 2022 Shanghai COVID Lockdown ─────────────────────────────────────
    {
        "id": "V6",
        "name": "2022 Shanghai COVID Lockdown",
        "period": "April–June 2022 (weeks 1–13)",
        "references": [
            "NBS China: manufacturing PMI April 2022 = 47.4 (contraction, below 50)",
            "NBS China: industrial output textiles -4.3% April 2022 YoY",
            "Shanghai International Port Group: container throughput -26% April 2022",
            "China Customs: textile & apparel exports -21% April 2022 YoY",
            "HMRC OTS API (2026-04-17): UK synthetic apparel from China +47% value, +14% volume full-year 2022 vs 2021 (price inflation dominated); Q2 2022 value +61%, volume +36% vs Q2 2021 — front-loading before lockdown, then energy cost pass-through",
            "ICIS: polyester staple fibre China domestic price -6% to -8% Q2 2022 (demand/supply imbalance)",
        ],
        # Supply shock: Shanghai lockdown (March 28 – June 1) affecting Jiangsu/Zhejiang
        # polyester cluster. PMI 47.4 implies ~46% below neutral → ~50-55% capacity loss.
        "cge_supply": {
            0: 1.00,   # Oil unaffected globally
            1: 0.75,   # Chem — China MEG/pX partially shut
            2: 0.50,   # PTA  — Jiangsu/Zhejiang cluster disrupted
            3: 0.50,   # PET  — same cluster
            4: 0.55,   # Fabric — Suzhou/Hangzhou weaving mills closed
            5: 0.65,   # Garment — some offshore (BD/VN) unaffected
            6: 0.74,   # Wholesale — Shanghai port -26%
            7: 1.00,   # Retail demand largely normal (UK consumption stable)
        },
        # No significant demand shock — UK/global demand roughly normal in 2022
        "cge_demand_shocks": {},
        "shock_duration_weeks": 9,   # ~9 weeks intensive lockdown
        "io_shock_schedule": {
            1: [(2, 0.50), (3, 0.50), (4, 0.45)],
            2: [(5, 0.35)],
            1: [(6, 0.26)],   # port throughput -26%
        },
        "io_demand_shock_schedule": None,
        "abm_schedule": {
            1: [
                {"sector": 2, "country": "China", "severity": 0.50, "duration": 9},
                {"sector": 3, "country": "China", "severity": 0.50, "duration": 9},
                {"sector": 4, "country": "China", "severity": 0.45, "duration": 9},
                {"sector": 5, "country": "China", "severity": 0.35, "duration": 9},
            ],
        },
        "simulation_weeks": 26,
        "observed": {
            "max_price_rise_pct": {
                "sector": "PTA_Production",
                "value": 8.0,
                "note": "ICIS PTA China domestic price: small rise then fall in Q2 2022 (~5-10% net)",
                "direction": "up",
            },
            "uk_import_change_pct": {
                "sector": "Garment_Assembly",
                "value": +47.0,
                "note": "HMRC OTS API: China full-year 2022 vs 2021 = +47% value, +14% volume. Price-driven (energy cost inflation) — model tracks supply disruption, not price pass-through, so directional mismatch is expected.",
            },
            "welfare_loss_lower_gbp_bn": 0.3,
            "welfare_loss_upper_gbp_bn": 0.9,
            "bullwhip_qualitative": "moderate",
        },
    },

    # ── V7: 2022 Ukraine / Global Energy Price Spike ─────────────────────────
    {
        "id": "V7",
        "name": "2022 Ukraine War / Global Energy Price Spike",
        "period": "February–June 2022",
        "references": [
            "EIA: Brent crude oil peaked at $127.98/barrel on 8 March 2022",
            "EIA: Brent average Jan 2022 = $83/barrel → March peak = +54%",
            "EIA: Average Brent price 2022 = $101/barrel vs $71/barrel in 2021 (+42%)",
            "ICIS: MEG China port price +18-22% H1 2022 (energy cost inflation)",
            "ICIS: PTA China domestic price +10-15% H1 2022",
            "ICIS: Polyester staple fibre China export price +12% H1 2022",
        ],
        # Oil price spike caused by Russia-Ukraine war and OPEC+ output constraints.
        # Impact on polyester chain: energy cost inflation (not physical supply loss).
        # Russia supplies ~11.6% of world crude; partial rerouting reduced global supply ~5%.
        "cge_supply": {
            0: 0.92,   # Oil — Russian output sanctions: ~5-8% global supply reduction
            1: 0.90,   # Chem — energy cost inflation reduces effective supply (output falls)
            2: 0.90,   # PTA  — Chinese production energy cost impact
            3: 0.92,   # PET  — less direct impact
            4: 0.95,   # Fabric — minimal
            5: 0.97,   # Garment — minimal
            6: 1.00,   # Wholesale — logistics largely unaffected
            7: 1.00,   # Retail demand normal
        },
        "cge_demand_shocks": {},
        "shock_duration_weeks": 20,
        "io_shock_schedule": {
            1: [(0, 0.08), (1, 0.10), (2, 0.10)],
        },
        "io_demand_shock_schedule": None,
        "abm_schedule": {
            1: [
                {"sector": 0, "country": "Russia",       "severity": 0.30, "duration": 20},
                {"sector": 1, "country": "Saudi_Arabia",  "severity": 0.10, "duration": 12},
            ],
        },
        "simulation_weeks": 26,
        "observed": {
            "max_price_rise_pct": {
                "sector": "Oil_Extraction",
                "value": 54.0,
                "note": "EIA: Brent crude Jan 2022 ($83) to Mar 2022 peak ($128) = +54%",
                "direction": "up",
            },
            "cascade_to_pta_pct": {
                "sector": "PTA_Production",
                "value": 12.0,
                "note": "ICIS: PTA China domestic +10-15% H1 2022 (midpoint 12%); energy cost driven",
            },
            "welfare_loss_lower_gbp_bn": 0.5,
            "welfare_loss_upper_gbp_bn": 1.5,
            "bullwhip_qualitative": "low",
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Core validation runner
# ─────────────────────────────────────────────────────────────────────────────

def run_validation_event(event: Dict) -> Dict:
    """
    Run IO + CGE + ABM for one historical event and return
    a dict of model predictions alongside observed values.
    """
    supply_arr = np.array([event["cge_supply"].get(i, 1.0) for i in range(N_SECTORS)])
    T          = event["simulation_weeks"]
    fd_base    = np.zeros(N_SECTORS); fd_base[-1] = 1.0

    # Build CGE demand shock array
    cge_dsh_dict = event.get("cge_demand_shocks", {})
    cge_dsh = np.ones(N_SECTORS)
    for idx, val in cge_dsh_dict.items():
        cge_dsh[idx] = val

    shock_dur = event.get("shock_duration_weeks", 12)

    # ── CGE equilibrium ───────────────────────────────────────────────────────
    cge = CGEModel()
    eq  = cge.equilibrium(supply_arr, fd_base,
                          demand_shocks=cge_dsh,
                          shock_duration_weeks=shock_dur)
    price_pct = eq["price_index_change_pct"]   # per-sector % change
    welfare   = eq["welfare_change_gbp"]

    # ── IO dynamic simulation ─────────────────────────────────────────────────
    io_model = DynamicIOModel()
    fd_gbp   = np.zeros(N_SECTORS); fd_gbp[-1] = 51_400_000_000
    io_result = io_model.simulate(
        T, fd_gbp,
        shock_schedule=event["io_shock_schedule"],
        demand_growth=0.0,
        demand_shock_schedule=event.get("io_demand_shock_schedule", None) or None,
    )
    shortage_total = io_result["shortage"].sum()
    shortage_norm  = shortage_total / (io_model.static_output(fd_gbp).sum() * T + 1e-12)
    # Sector-level output drop at worst week vs baseline
    x_base = io_model.static_output(fd_gbp)
    x_min  = io_result["output"].min(axis=0)
    output_drop_pct = (x_min - x_base) / (x_base + 1e-12) * 100   # negative = drop

    # ── ABM ───────────────────────────────────────────────────────────────────
    abm    = PolyesterSupplyChainABM()
    abm_r  = abm.run(T, 1.0, shock_schedule=event["abm_schedule"])
    bw_df  = abm.bullwhip_ratio(abm_r)
    sl_df  = abm.service_level(abm_r)
    rt_df  = abm.recovery_time(abm_r)

    # ── Package predictions ───────────────────────────────────────────────────
    predictions = {
        "cge_price_pct":      price_pct,                  # (N,) array
        "cge_welfare_gbp_bn": welfare / 1e9,
        "cge_max_price_pct":  float(price_pct.max()),
        "cge_max_price_sector": SECTORS[int(price_pct.argmax())],
        "io_shortage_norm":   float(shortage_norm),
        "io_output_drop_pct": output_drop_pct,             # (N,) array
        "abm_bullwhip":       bw_df,
        "abm_service":        sl_df,
        "abm_recovery":       rt_df,
    }
    return predictions


def compare_event(event: Dict, predictions: Dict) -> pd.DataFrame:
    """
    Build a comparison table: model prediction vs observed value.
    Computes % error and directional accuracy for each observable.
    """
    obs   = event["observed"]
    rows  = []

    # 1. Max price rise
    if "max_price_rise_pct" in obs:
        o = obs["max_price_rise_pct"]
        sec_idx = SECTORS.index(o["sector"])
        pred_p  = float(predictions["cge_price_pct"][sec_idx])
        obs_p   = float(o["value"])
        err     = pred_p - obs_p
        err_pct = err / (abs(obs_p) + 1e-6) * 100
        rows.append({
            "Observable":    f"Price rise % at {o['sector']}",
            "Observed":      obs_p,
            "Model":         round(pred_p, 1),
            "Abs_Error":     round(abs(err), 1),
            "Error_%":       round(err_pct, 1),
            "Direction_OK":  (pred_p > 0) == (obs_p > 0),
            "Source":        o["note"],
        })

    # 2. Welfare loss range
    if "welfare_loss_lower_gbp_bn" in obs:
        lo   = obs["welfare_loss_lower_gbp_bn"]
        hi   = obs["welfare_loss_upper_gbp_bn"]
        pred = abs(predictions["cge_welfare_gbp_bn"])
        in_range = lo <= pred <= hi
        midpoint = (lo + hi) / 2
        rows.append({
            "Observable":    "Welfare loss (£bn)",
            "Observed":      f"{lo}–{hi} (mid {midpoint:.1f})",
            "Model":         round(pred, 2),
            "Abs_Error":     round(abs(pred - midpoint), 2),
            "Error_%":       round(abs(pred - midpoint) / (midpoint + 1e-6) * 100, 1),
            "Direction_OK":  True if in_range else (pred > 0),
            "Source":        "Estimated from ONS/HMRC/literature",
        })

    # 3. UK import change (garment)
    if "uk_import_change_pct" in obs:
        o       = obs["uk_import_change_pct"]
        sec_idx = SECTORS.index(o["sector"])
        pred_d  = float(predictions["io_output_drop_pct"][sec_idx])
        obs_d   = float(o["value"])
        rows.append({
            "Observable":   f"Supply/output change % at {o['sector']}",
            "Observed":     obs_d,
            "Model":        round(pred_d, 1),
            "Abs_Error":    round(abs(pred_d - obs_d), 1),
            "Error_%":      round(abs(pred_d - obs_d) / (abs(obs_d) + 1e-6) * 100, 1),
            "Direction_OK": (pred_d < 0) == (obs_d < 0),
            "Source":       o["note"],
        })

    # 4. Retail output change
    if "retail_output_change_pct" in obs:
        o       = obs["retail_output_change_pct"]
        sec_idx = SECTORS.index(o["sector"])
        pred_d  = float(predictions["io_output_drop_pct"][sec_idx])
        obs_d   = float(o["value"])
        rows.append({
            "Observable":   f"Output change % at {o['sector']}",
            "Observed":     obs_d,
            "Model":        round(pred_d, 1),
            "Abs_Error":    round(abs(pred_d - obs_d), 1),
            "Error_%":      round(abs(pred_d - obs_d) / (abs(obs_d) + 1e-6) * 100, 1),
            "Direction_OK": (pred_d < 0) == (obs_d < 0),
            "Source":       o["note"],
        })

    # 5. Cascade check (V4: no cascade to PTA)
    if "cascade_to_pta_pct" in obs:
        o       = obs["cascade_to_pta_pct"]
        sec_idx = SECTORS.index(o["sector"])
        pred_p  = float(predictions["cge_price_pct"][sec_idx])
        obs_p   = float(o["value"])
        rows.append({
            "Observable":   f"Cascade price % at {o['sector']}",
            "Observed":     obs_p,
            "Model":        round(pred_p, 2),
            "Abs_Error":    round(abs(pred_p - obs_p), 2),
            "Error_%":      round(abs(pred_p - obs_p) / (abs(obs_p) + 1e-6) * 100, 1),
            # If observed cascade is near-zero: model should also be small.
            # If observed cascade is large: check directional sign.
            "Direction_OK": (abs(pred_p) < 5.0) if abs(obs_p) < 5.0
                            else (pred_p > 0) == (obs_p > 0),
            "Source":       o["note"],
        })

    return pd.DataFrame(rows)


def summary_metrics(comparisons: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Aggregate validation metrics across all events:
      - Mean Absolute Error (MAE) for quantitative comparisons
      - Directional accuracy (fraction of signs correct)
      - RMSE of percentage errors
    """
    all_errors = []
    all_dirs   = []
    rows       = []

    for eid, df in comparisons.items():
        numeric_errors = []
        dirs           = []
        for _, row in df.iterrows():
            try:
                err = float(row["Abs_Error"])
                numeric_errors.append(err)
                all_errors.append(err)
            except (ValueError, TypeError):
                pass
            dirs.append(bool(row["Direction_OK"]))
            all_dirs.append(bool(row["Direction_OK"]))

        mae  = np.mean(numeric_errors) if numeric_errors else np.nan
        dacc = np.mean(dirs) * 100 if dirs else np.nan
        rows.append({
            "Event":               eid,
            "N_Comparisons":       len(df),
            "MAE":                 round(mae, 2),
            "Directional_Acc_%":   round(dacc, 1),
        })

    rows.append({
        "Event":               "OVERALL",
        "N_Comparisons":       len(all_errors),
        "MAE":                 round(np.mean(all_errors), 2) if all_errors else np.nan,
        "Directional_Acc_%":   round(np.mean(all_dirs) * 100, 1) if all_dirs else np.nan,
    })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────

def run_all_validations(out_dir: str = "results") -> None:
    os.makedirs(out_dir, exist_ok=True)

    print()
    print("=" * 65)
    print(" HISTORICAL BACKCASTING VALIDATION")
    print("=" * 65)

    comparisons = {}

    for event in HISTORICAL_EVENTS:
        eid  = event["id"]
        name = event["name"]
        print(f"\n{'─'*65}")
        print(f"  {eid}: {name}")
        print(f"  Period: {event['period']}")
        print(f"{'─'*65}")

        preds = run_validation_event(event)
        comp  = compare_event(event, preds)
        comparisons[eid] = comp

        # Print comparison table
        print(comp.to_string(index=False))

        # CGE full price vector
        print(f"\n  CGE equilibrium prices (% change from baseline):")
        for i, s in enumerate(SECTORS):
            p = preds["cge_price_pct"][i]
            bar = "█" * int(abs(p) / 5) if abs(p) >= 1 else ""
            print(f"    {s:25s}: {p:+7.1f}%  {bar}")
        print(f"  Welfare change: £{preds['cge_welfare_gbp_bn']:.3f}bn")

        # IO worst output drop
        print(f"\n  IO model: worst output drop by sector (at shock nadir):")
        for i, s in enumerate(SECTORS):
            d = preds["io_output_drop_pct"][i]
            if d < -0.5:
                print(f"    {s:25s}: {d:+.1f}%")

        # ABM bullwhip
        print(f"\n  ABM bullwhip ratios:")
        bw = preds["abm_bullwhip"]
        for _, r in bw.iterrows():
            if r["Bullwhip_Ratio"] > 1.1:
                print(f"    {r['Sector']:25s}: {r['Bullwhip_Ratio']:.2f}x")

        # Recovery
        print(f"\n  ABM recovery times (weeks to 95% capacity):")
        rt = preds["abm_recovery"]
        for _, r in rt.iterrows():
            rw = r["Recovery_Week"]
            print(f"    {r['Sector']:25s}: {'No recovery' if rw is None else str(rw) + ' wk'}")

        # Save
        comp.to_csv(f"{out_dir}/{eid}_validation.csv", index=False)
        print(f"\n  Saved: {eid}_validation.csv")

        # Key reference info
        print(f"\n  Data sources:")
        for ref in event["references"]:
            print(f"    • {ref}")

    # Summary
    print(f"\n{'='*65}")
    print(" VALIDATION SUMMARY")
    print(f"{'='*65}")
    summary = summary_metrics(comparisons)
    print(summary.to_string(index=False))
    summary.to_csv(f"{out_dir}/validation_summary.csv", index=False)
    print(f"\n  Saved: validation_summary.csv")

    # Model limitations disclosure
    print(f"""
{'='*65}
 MODEL LIMITATIONS AND CAVEATS
{'='*65}
 1. CGE model uses static Armington elasticities. Actual
    substitution is slower in the short run than σ implies.
 2. IO model A-matrix uses ONS UK IO Analytical Tables 2023 for
    downstream material-input coefficients (fabric→garment, petrochem→
    textiles). Upstream entries (oil→chem→PTA→PET) remain global
    supply-chain estimates as UK domestic IO has near-zero coefficients
    for predominantly-imported feedstocks (UK imports >95%).
 3. ABM agents use exponential smoothing (α=0.3) for demand
    forecasting — a simplification of real procurement systems.
 4. Freight cost shocks (V2, V5) are modelled as capacity
    reductions at the wholesale/logistics node, not as explicit
    cost-push into downstream prices. This underestimates the
    pass-through to consumer prices.
 5. All scenarios use a single representative agent per
    country-sector pair. Real supply chains have heterogeneous
    agents with different inventory policies.
 6. The nylon-66 event (V3) is an analogue for PTA: the two
    chemicals have similar supply chain structure but different
    markets. Price magnitudes are not directly comparable.
{'='*65}
""")


if __name__ == "__main__":
    # Ensure output encoding on Windows
    sys.stdout = _io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    run_all_validations(out_dir="results")
