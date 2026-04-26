"""
policies.py
UK government policy interventions for polyester supply chain resilience.

Five policies spanning the full spectrum of government tools:

  P1 — Strategic Buffer Stockpile
       Mandated minimum inventory at upstream stages.

  P2 — Import Diversification Support
       Subsidised sourcing from non-China countries, shifting base capacities
       in the ABM so non-China agents absorb more demand when China is shocked.

  P3 — Emergency Recovery Investment
       Grants and tax credits that accelerate capacity rebuild after a shock,
       modelled as a multiplier on the IO capital-intensity-weighted recovery rate.

  P4 — Critical Material Reserve Release
       Government releases physical reserves of PTA / PET at shock onset,
       directly supplementing sector capacity for a fixed window.

  P5 — Integrated Resilience Package
       A balanced combination of P1–P4 at moderate levels, representing a
       comprehensive pre-committed resilience strategy.

Each policy is a plain dataclass; no model-specific logic is here.
Application logic lives in IntegratedSupplyChainModel._apply_policy().
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Policy:
    """
    Specification of a UK government policy intervention.

    Parameters
    ----------
    code, name, description : identifiers shown in the UI.

    buffer_sectors : {sector_name: multiplier}
        Safety-stock target at the named stage is scaled by `multiplier`
        (e.g., 2.0 doubles the weeks of buffer held).  Applied to ABM
        agent inventory at simulation start.

    diversify_sectors : {sector_name: divert_fraction}
        Fraction of Chinese capacity shifted to non-China agents at that
        stage (e.g., 0.25 moves 25 % of China share to alternatives).
        Represents government import-credit programmes or supplier-
        development grants that reduce effective China dependency.

    recovery_boost : {sector_name: rate_multiplier}
        Multiplier on the base IO capacity-recovery rate for that sector
        (e.g., 2.0 doubles the weekly rebuild speed).
        Represents emergency investment grants and workforce-retention
        support that compress the rebuild timeline.

    reserve_release : {sector_name: capacity_boost}
        Additional capacity injected at each sector for `release_duration_weeks`
        weeks, starting `release_delay_weeks` after the shock onset.
        Models physical release of government-held material reserves
        (e.g., a national PTA strategic stockpile analogous to oil SPR).

    release_delay_weeks : int (default 2)
        Weeks between shock onset and first reserve release.

    release_duration_weeks : int (default 8)
        How many consecutive weeks the reserve is released.

    cost_estimate_gbp_m : float
        Indicative annual policy cost in £ million (for comparison table).
    """
    code:  str
    name:  str
    description: str

    buffer_sectors:    Dict[str, float] = field(default_factory=dict)
    diversify_sectors: Dict[str, float] = field(default_factory=dict)
    recovery_boost:    Dict[str, float] = field(default_factory=dict)
    reserve_release:   Dict[str, float] = field(default_factory=dict)

    release_delay_weeks:    int   = 2
    release_duration_weeks: int   = 8

    cost_estimate_gbp_m: float = 0.0


# ── Policy definitions ────────────────────────────────────────────────────────

P1_BUFFER = Policy(
    code  = "P1",
    name  = "Strategic Buffer Stockpile",
    description = (
        "Government mandates minimum inventory holdings at the three most "
        "vulnerable upstream stages (PTA, PET/Yarn, Fabric). Safety-stock "
        "targets are doubled relative to commercial norms. Analogous to EU "
        "critical raw-material stockpile rules and US Strategic Petroleum Reserve "
        "logic applied to polyester intermediates.\n\n"
        "**Mechanism:** ABM agents at targeted stages start with 2× their baseline "
        "safety stock. When the shock hits, the larger buffer absorbs the initial "
        "supply deficit and delays the onset of downstream shortages."
    ),
    buffer_sectors = {
        "PTA_Production":  2.0,
        "PET_Resin_Yarn":  2.0,
        "Fabric_Weaving":  1.5,
        "Garment_Assembly": 1.5,
    },
    cost_estimate_gbp_m = 120.0,   # capital cost of holding ~12 weeks extra stock
)

P2_DIVERSIFY = Policy(
    code  = "P2",
    name  = "Import Diversification Support",
    description = (
        "Subsidised trade-finance and supplier-development grants redirect 25 % "
        "of Chinese sourcing capacity to alternative suppliers (India, South Korea, "
        "Bangladesh, Vietnam, Turkey) at the three most China-dependent stages. "
        "Reduces effective China dependency from ~67 % (PTA) to ~50 %, consistent "
        "with the UK's Critical Minerals Strategy diversification targets.\n\n"
        "**Mechanism:** ABM base capacities for China are reduced by 25 %; the "
        "freed share is redistributed to non-China agents proportionally. When "
        "a China-specific shock fires, non-China agents (undisrupted) fill the gap."
    ),
    diversify_sectors = {
        "PTA_Production":   0.25,
        "PET_Resin_Yarn":   0.25,
        "Fabric_Weaving":   0.25,
        "Garment_Assembly": 0.20,
    },
    cost_estimate_gbp_m = 45.0,   # ongoing supplier-development and credit guarantees
)

P3_RECOVERY = Policy(
    code  = "P3",
    name  = "Emergency Recovery Investment",
    description = (
        "Emergency capital grants, business-rate relief, and workforce-retention "
        "payments accelerate capacity rebuild across shocked sectors. The IO model's "
        "base recovery rate is doubled, compressing the typical 6-12 week rebuild "
        "timeline to 3-6 weeks. Analogous to the UK government's COVID Resilience "
        "Fund and BEIS energy-intensive industries support.\n\n"
        "**Mechanism:** The IO capacity-recovery multiplier is scaled 2× for all "
        "sectors, so damaged capacity returns to baseline in half the normal time. "
        "Higher prices already incentivise private recovery; this policy adds "
        "a public-sector floor independent of the price signal."
    ),
    recovery_boost = {s: 2.0 for s in [
        "Chemical_Processing", "PTA_Production", "PET_Resin_Yarn",
        "Fabric_Weaving", "Garment_Assembly",
    ]},
    cost_estimate_gbp_m = 200.0,   # grant programme budget
)

P4_RESERVE = Policy(
    code  = "P4",
    name  = "Critical Material Reserve Release",
    description = (
        "A government-held physical reserve of PTA and PET resin is released "
        "two weeks after shock onset, sustained for eight weeks at 25 % and "
        "15 % of baseline output respectively. Analogous to the IEA coordinated "
        "oil reserve release (60 mb released in 2022) applied to polyester "
        "intermediates. Directly offsets the supply deficit at the source.\n\n"
        "**Mechanism:** Sector capacity is boosted by the reserve fraction for "
        "the release window. Higher effective IO output raises supply fractions "
        "passed to CGE (lower prices) and to ABM (higher pipeline delivery rates), "
        "dampening the bullwhip cascade."
    ),
    reserve_release = {
        "PTA_Production":  0.25,
        "PET_Resin_Yarn":  0.15,
        "Chemical_Processing": 0.10,
    },
    release_delay_weeks    = 2,
    release_duration_weeks = 8,
    cost_estimate_gbp_m    = 350.0,   # reserve acquisition and storage
)

P5_INTEGRATED = Policy(
    code  = "P5",
    name  = "Integrated Resilience Package",
    description = (
        "A pre-committed, balanced combination of P1–P4 at moderate levels, "
        "representing the kind of multi-instrument resilience strategy proposed "
        "in the UK's Resilient Supply Chains Review (2023) and modelled on the "
        "EU Critical Raw Materials Act.\n\n"
        "**Components:**\n"
        "- Buffer stocks at 1.5× (P1 moderate)\n"
        "- 15 % China diversification (P2 moderate)\n"
        "- 1.5× recovery acceleration (P3 moderate)\n"
        "- 15 % / 10 % reserve release for PTA / PET (P4 moderate)\n\n"
        "Lower individual-instrument intensity reduces the cost while "
        "synergistic effects across channels exceed any single policy."
    ),
    buffer_sectors = {
        "PTA_Production": 1.5, "PET_Resin_Yarn": 1.5,
        "Fabric_Weaving": 1.25, "Garment_Assembly": 1.25,
    },
    diversify_sectors = {
        "PTA_Production": 0.15, "PET_Resin_Yarn": 0.15,
        "Fabric_Weaving": 0.15, "Garment_Assembly": 0.10,
    },
    recovery_boost = {s: 1.5 for s in [
        "Chemical_Processing", "PTA_Production", "PET_Resin_Yarn",
        "Fabric_Weaving", "Garment_Assembly",
    ]},
    reserve_release = {
        "PTA_Production": 0.15,
        "PET_Resin_Yarn": 0.10,
    },
    release_delay_weeks    = 2,
    release_duration_weeks = 8,
    cost_estimate_gbp_m    = 180.0,   # blended cost across instruments
)


# ── Registry ──────────────────────────────────────────────────────────────────

ALL_POLICIES: Dict[str, Policy] = {
    "P1": P1_BUFFER,
    "P2": P2_DIVERSIFY,
    "P3": P3_RECOVERY,
    "P4": P4_RESERVE,
    "P5": P5_INTEGRATED,
}
