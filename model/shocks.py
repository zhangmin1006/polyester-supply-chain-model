"""
shocks.py
Shock scenario definitions for the polyester supply chain model.

Each scenario is grounded in a real risk identified in the research:
  S1: PTA production shock          — Eastern China dominates (67% global, GlobalData 2021)
  S2: MEG supply disruption         — Saudi SABIC + China import dependency (43%)
  S3: UK–China geopolitical shock   — trade restriction / tariff escalation
  S4: Port closure (Zhangjiagang)   — largest MEG inventory hub in China
  S5: Multi-node pandemic shock     — simultaneous disruptions (COVID-style)

Shock parameters are calibrated where possible to real events
(e.g., nylon 2018 fire caused 30–40% supply reduction).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
from real_data import SECTORS, MEG_TOTAL_INVENTORY_KT, MEG_PORT_INVENTORY_KT

# Sector index lookup
_S = {s: i for i, s in enumerate(SECTORS)}


@dataclass
class Shock:
    """Definition of a supply chain shock scenario."""
    name:        str
    description: str
    onset_week:  int                        # week shock begins
    # I-O shocks: {sector_idx: fraction_lost}
    io_shocks:   Dict[int, float]
    # CGE supply shocks: {sector_idx: fraction_of_baseline_supply}
    cge_supply:  Dict[int, float]           # supply_shocks array for CGEModel
    # ABM shocks: {week: List[{'sector', 'country', 'severity', 'duration'}]}
    # Multiple shocks can occur in the same week — use lists.
    abm_schedule: Dict[int, List[Dict]]
    # CGE tariff changes: {sector_name: tariff_rate}
    tariffs:     Dict[str, float]
    # Duration (weeks) for recovery analysis
    duration_weeks: int
    # Reference event (for credibility)
    reference:   str = ""


# ── Scenario 1: PTA Production Shock ─────────────────────────────────────────
# Motivation: Eastern China holds 72% of global PTA capacity.
# An event (earthquake, policy, conflict) reduces output by 50%.
# Calibrated to: 2018 nylon factory fires caused ~35-40% supply drop.
SCENARIO_PTA_SHOCK = Shock(
    name        = "S1_PTA_Production_Shock",
    description = (
        "Eastern China PTA production falls 50 % (earthquake / policy disruption). "
        "China holds 67 % of global PTA capacity (GlobalData 2021; was 72 % in earlier estimate). "
        "Calibrated to 2018 nylon ADN fire magnitude (35-40 % drop)."
    ),
    onset_week  = 4,
    io_shocks   = {
        _S["PTA_Production"]: 0.50,          # 50 % PTA output lost
        _S["PET_Resin_Yarn"]: 0.35,          # cascades into PET (lagged)
        _S["Fabric_Weaving"]: 0.20,          # further cascade
    },
    cge_supply  = {i: 1.0 for i in range(len(SECTORS))} | {
        _S["PTA_Production"]: 0.50,
        _S["PET_Resin_Yarn"]: 0.65,
        _S["Fabric_Weaving"]: 0.82,
    },
    abm_schedule = {
        4: [{"sector": _S["PTA_Production"], "country": "China",
             "severity": 0.50, "duration": 12}],
        5: [{"sector": _S["PET_Resin_Yarn"], "country": "China",
             "severity": 0.35, "duration": 10}],
    },
    tariffs     = {},
    duration_weeks = 24,
    reference   = "Analogy: 2018 nylon-66 ADN factory fires; RiSC report PTA concentration analysis",
)


# ── Scenario 2: MEG Supply Disruption ────────────────────────────────────────
# Motivation: China imports 43% of world MEG, mainly from Saudi Arabia.
# A major disruption to Saudi MEG supply (SABIC plant outage / Houthi attacks
# on Red Sea shipping) reduces China MEG supply.
# Buffer: 688 kt in Chinese ports ≈ ~3 weeks at estimated consumption rate.
_meg_buffer_weeks = 3.0   # estimated from 688 kt inventory / ~230 kt/wk implied

SCENARIO_MEG_DISRUPTION = Shock(
    name        = "S2_MEG_Supply_Disruption",
    description = (
        "Saudi MEG export disruption (Red Sea / Strait of Hormuz). "
        f"China imports 43 % of world MEG. Port inventory buffer ≈ {_meg_buffer_weeks:.1f} weeks "
        f"({MEG_TOTAL_INVENTORY_KT:,} kt across Zhangjiagang, Jiangyin, Taicang, Ningbo). "
        "After buffer exhausted, PET resin output falls proportionally."
    ),
    onset_week  = 4,
    io_shocks   = {
        _S["Chemical_Processing"]: 0.25,    # MEG supply down 25 %
        _S["PTA_Production"]:      0.10,    # minor effect (PTA mainly from p-xylene)
        _S["PET_Resin_Yarn"]:      0.20,    # direct input scarcity
    },
    cge_supply  = {i: 1.0 for i in range(len(SECTORS))} | {
        _S["Chemical_Processing"]: 0.75,
        _S["PET_Resin_Yarn"]:      0.80,
    },
    abm_schedule = {
        4: [
            # Saudi Arabia loses 60% of MEG export capacity (origin of disruption)
            {"sector": _S["Chemical_Processing"], "country": "Saudi_Arabia",
             "severity": 0.60, "duration": 8},
            # China loses 43% × 60% = 25.8% ≈ 0.26 of MEG inputs (import dependency)
            # China Chemical (35% of global) × (1-0.26) → sector drop ≈ 25% matching IO
            {"sector": _S["Chemical_Processing"], "country": "China",
             "severity": 0.26, "duration": 8},
        ],
        # Buffer exhaustion: PET disruption begins after 3-week delay
        7: [{"sector": _S["PET_Resin_Yarn"], "country": "China",
             "severity": 0.25, "duration": 10}],
    },
    tariffs     = {},
    duration_weeks = 20,
    reference   = "Logistics_Price_Info.pptx: 688 kt MEG port inventory; 43% China MEG import dependency",
)


# ── Scenario 3: UK–China Geopolitical Trade Shock ─────────────────────────────
# Motivation: UK imports 27.3% directly from China (HMRC 2023), but effective
# China dependency is ~60% at garment stage when upstream traced.
# A tariff escalation or trade restriction scenario.
SCENARIO_GEOPOLITICAL = Shock(
    name        = "S3_UK_China_Trade_Restriction",
    description = (
        "UK imposes 35 % tariff on Chinese synthetic apparel imports "
        "(and equivalently restricted access). "
        "Effective China dependency at garment stage is ~60 % when upstream "
        "Bangladesh/Vietnam fabric sourcing from China is included (RiSC report). "
        "Short-run: supply falls. Medium-run: partial rerouting via Turkey/India."
    ),
    onset_week  = 1,
    io_shocks   = {
        _S["Garment_Assembly"]: 0.35,       # immediate: Chinese garments unavailable
        _S["Fabric_Weaving"]:   0.20,       # fabric sourcing disrupted
    },
    cge_supply  = {i: 1.0 for i in range(len(SECTORS))} | {
        _S["Garment_Assembly"]: 0.65,
        _S["Fabric_Weaving"]:   0.80,
    },
    abm_schedule = {
        1: [
            # China garment: near-total block of Chinese apparel exports under tariff
            # severity 0.90 × China share 0.273 = 24.6% sector loss
            {"sector": _S["Garment_Assembly"], "country": "China",
             "severity": 0.90, "duration": 52},
            # Bangladesh: 40% disruption — Chinese fabric no longer available for
            # Bangladesh assembly (upstream tracing; effective dependency ~30-50%)
            # 0.120 × 0.40 = 4.8% additional sector loss → total ≈ 29% (approaching IO 35%)
            {"sector": _S["Garment_Assembly"], "country": "Bangladesh",
             "severity": 0.40, "duration": 52},
            # Fabric Weaving: China fabric blocked (0.433 × 0.40 ≈ 17% ≈ IO 20%)
            {"sector": _S["Fabric_Weaving"],   "country": "China",
             "severity": 0.40, "duration": 52},
        ],
    },
    tariffs     = {
        "Garment_Assembly": 0.35,
        "Fabric_Weaving":   0.35,
        "PET_Resin_Yarn":   0.15,
    },
    duration_weeks = 52,
    reference   = "HMRC 2023: China 27.3% direct; RiSC report: effective ~60% with upstream tracing",
)


# ── Scenario 4: Port Closure – Zhangjiagang ──────────────────────────────────
# Motivation: Zhangjiagang holds 418 kt MEG (61% of Chinese port inventory).
# A port closure (typhoon, COVID lockdown) blocks MEG inflow to Jiangsu province
# where Yizheng Chemical Fibre (Sinopec) is located.
_zjg_share = MEG_PORT_INVENTORY_KT["Zhangjiagang"] / MEG_TOTAL_INVENTORY_KT

SCENARIO_PORT_CLOSURE = Shock(
    name        = "S4_Zhangjiagang_Port_Closure",
    description = (
        f"Zhangjiagang port closed (typhoon / COVID lockdown). "
        f"Port holds {MEG_PORT_INVENTORY_KT['Zhangjiagang']:,} kt MEG "
        f"({_zjg_share*100:.0f}% of Chinese port inventory, {MEG_TOTAL_INVENTORY_KT:,} kt total). "
        "Yizheng Chemical Fibre (world's largest polyester producer, Sinopec subsidiary) "
        "is located nearby. Direct impact on PET resin / yarn output."
    ),
    onset_week  = 4,
    io_shocks   = {
        _S["Chemical_Processing"]: 0.20,
        _S["PET_Resin_Yarn"]:      0.30,    # Yizheng directly affected
        _S["Fabric_Weaving"]:      0.18,
    },
    cge_supply  = {i: 1.0 for i in range(len(SECTORS))} | {
        _S["Chemical_Processing"]: 0.80,
        _S["PET_Resin_Yarn"]:      0.70,
        _S["Fabric_Weaving"]:      0.82,
    },
    abm_schedule = {
        4: [
            {"sector": _S["PET_Resin_Yarn"], "country": "China",
             "severity": 0.30, "duration": 6},
            {"sector": _S["Chemical_Processing"], "country": "China",
             "severity": 0.20, "duration": 6},
        ],
    },
    tariffs     = {},
    duration_weeks = 16,
    reference   = "Logistics_Price_Info.pptx: Zhangjiagang 418 kt; Yizheng Chemical Fibre (Sinopec)",
)


# ── Scenario 5: Multi-Node Pandemic Shock ────────────────────────────────────
# Motivation: COVID-style simultaneous disruption across multiple nodes.
# Calibrated to observed COVID impacts: China factory shutdowns (Q1 2020),
# shipping delays (37-day China→UK journey extended to 60+ days),
# and demand collapse then surge.
SCENARIO_PANDEMIC = Shock(
    name        = "S5_Multi_Node_Pandemic_Shock",
    description = (
        "Simultaneous multi-stage disruption (COVID-style): "
        "Chinese manufacturing shuts 60 % for 6 weeks; "
        "shipping delays double (37 → 70 day China–UK transit); "
        "Bangladesh/Vietnam assembly disrupted; "
        "demand collapses 40 % then surges 60 % post-lockdown. "
        "Tests end-to-end resilience of the entire supply chain."
    ),
    onset_week  = 4,
    io_shocks   = {
        _S["PTA_Production"]:   0.60,
        _S["PET_Resin_Yarn"]:   0.60,
        _S["Fabric_Weaving"]:   0.55,
        _S["Garment_Assembly"]: 0.50,
        _S["UK_Wholesale"]:     0.20,
    },
    cge_supply  = {i: 1.0 for i in range(len(SECTORS))} | {
        _S["PTA_Production"]:   0.40,
        _S["PET_Resin_Yarn"]:   0.40,
        _S["Fabric_Weaving"]:   0.45,
        _S["Garment_Assembly"]: 0.50,
        _S["UK_Wholesale"]:     0.80,
    },
    abm_schedule = {
        4: [
            {"sector": _S["PTA_Production"], "country": "China",      "severity": 0.60, "duration": 6},
            {"sector": _S["PET_Resin_Yarn"], "country": "China",      "severity": 0.60, "duration": 8},
            {"sector": _S["Fabric_Weaving"], "country": "China",      "severity": 0.55, "duration": 8},
        ],
        5: [{"sector": _S["Garment_Assembly"], "country": "Bangladesh", "severity": 0.50, "duration": 6}],
        6: [{"sector": _S["Garment_Assembly"], "country": "Vietnam",    "severity": 0.45, "duration": 6}],
        10:[{"sector": _S["UK_Wholesale"],     "country": "UK",         "severity": 0.20, "duration": 4}],
    },
    tariffs     = {},
    duration_weeks = 52,
    reference   = "COVID-19 supply chain disruptions 2020-2021; RiSC report vulnerability analysis",
)


# ── Scenario registry ─────────────────────────────────────────────────────────
ALL_SCENARIOS = {
    "S1": SCENARIO_PTA_SHOCK,
    "S2": SCENARIO_MEG_DISRUPTION,
    "S3": SCENARIO_GEOPOLITICAL,
    "S4": SCENARIO_PORT_CLOSURE,
    "S5": SCENARIO_PANDEMIC,
}

# ── Utility: build CGE supply shock array from scenario ───────────────────────

def build_cge_supply_array(scenario: Shock) -> np.ndarray:
    """Return (N_SECTORS,) array of supply fractions for CGEModel."""
    supply = np.ones(len(SECTORS))
    for idx, frac in scenario.cge_supply.items():
        supply[idx] = frac
    return supply


def build_io_shock_schedule(scenario: Shock) -> Dict:
    """
    Return {week: List[(sector_idx, shock_fraction)]} for DynamicIOModel.
    Multiple sectors can be shocked simultaneously.
    """
    schedule: Dict[int, List] = {}
    week = scenario.onset_week
    for idx, frac in scenario.io_shocks.items():
        schedule.setdefault(week, []).append((idx, frac))
    return schedule
