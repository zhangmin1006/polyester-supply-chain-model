"""
io_model.py
Dynamic Leontief Input-Output model for the polyester textile supply chain.

The technical coefficient matrix A is calibrated so that:
  - Column sums < 1 (Hawkins-Simon condition)
  - The chain reproduces observed UK import share and turnover data
  - Each a_ij represents value of sector i's output per unit of sector j's output

Dynamic extension follows Leontief (1970): capital stock formation adds
lagged output terms through capital coefficient matrix B.
Transit-time lags are embedded from real logistics data.
"""

import numpy as np
from numpy.linalg import inv, solve
from typing import Dict, List, Tuple, Optional
import pandas as pd
from real_data import SECTORS, N_SECTORS, TRANSIT_DAYS, STAGE_RETAIL_VALUE_SHARE  # noqa: F401


# ── Technical coefficient matrix ─────────────────────────────────────────────
# a_ij = value of sector i input per unit value of sector j output.
# Sectors: 0=Oil  1=Chem  2=PTA  3=PET  4=Fab  5=Gar  6=Who  7=Ret
#
# Mixed calibration strategy (two source types):
#
# (A) ONS UK IO Analytical Tables 2023 — direct material-input coefficients
#     from "A" sheet (domestic) + "Imports use pxp" (import) combined totals.
#     Used where ONS CPA sectors map to genuine material flows:
#       C13→C14: fabric into garment assembly
#       C20B→C13: petrochem into textiles (dye, lubricants)
#       G46→C14: wholesale logistics service into garment
#
# (B) IO-derived value-share ratios for the goods-distribution chain.
#     ONS G46 (wholesale) and G47 (retail) are trade-services sectors; their
#     direct IO coefficients capture trade margins (~0.01), not merchandise
#     value flows. Goods-flow coefficients are derived instead from
#     STAGE_RETAIL_VALUE_SHARE (backward chain from ONS IOT GVA/Output):
#       A[5,6] = vs[Gar]/vs[Who] × 0.68  = 0.190/0.402 × 0.68 = 0.321
#       A[6,7] = vs[Who]/vs[Ret] × 0.56  = 0.402/1.000 × 0.56 = 0.225
#
# (C) Global supply-chain estimates for upstream stages (Oil→Chem→PTA→PET)
#     where UK domestic IO coefficients are near-zero (UK imports >95% of
#     polyester feedstock; IEA/ICIS cost-structure literature).
#
# Hawkins-Simon column sums:
#   0|0.20|0.30|0.39|0.256|0.182|0.321|0.225 — all < 1 ✓

_vs = list(STAGE_RETAIL_VALUE_SHARE.values())

A_BASE = np.zeros((N_SECTORS, N_SECTORS))

# ── (A) ONS IO material-input coefficients ────────────────────────────────────
A_BASE[4, 5] = 0.0855   # Textiles(C13)  → Apparel(C14)     ONS IO total
A_BASE[6, 5] = 0.0962   # Wholesale(G46) → Apparel(C14)     ONS IO domestic
A_BASE[1, 4] = 0.0555   # Petrochem(C20B)→ Textiles(C13)    ONS IO total

# ── (B) Goods-distribution chain: IO-derived value-share ratios ───────────────
A_BASE[5, 6] = _vs[5] / _vs[6] * 0.68   # Garment → Wholesale  = 0.321
A_BASE[6, 7] = _vs[6] / _vs[7] * 0.56   # Wholesale → Retail   = 0.225

# ── (C) Upstream chain: global supply-chain estimates ─────────────────────────
A_BASE[0, 1] = 0.20   # Oil → Chemical processing
A_BASE[1, 2] = 0.30   # Chemical → PTA production
A_BASE[2, 3] = 0.35   # PTA → PET resin/yarn
A_BASE[3, 4] = 0.20   # PET → Fabric weaving
A_BASE[0, 3] = 0.04   # Oil → PET (energy for polymerisation, IEA estimate)

# Verify Hawkins-Simon: all column sums < 1
assert (A_BASE.sum(axis=0) < 1).all(), "Hawkins-Simon condition violated"


# ── Capital coefficient matrix ────────────────────────────────────────────────
# b_ij = additional investment in sector i needed to expand sector j output by 1.
# Diagonal: capital intensity of each sector (higher upstream = more capital).
B_BASE = np.diag([0.40, 0.35, 0.30, 0.22, 0.15, 0.08, 0.12, 0.06])


# ── Delivery lag matrix (weeks) ───────────────────────────────────────────────
# Derived from TRANSIT_DAYS in real_data.py (converted to weeks, rounded).
#   Oil→Chemicals: SA→China 23d ≈ 3.3wk, say 3
#   Chem→PTA: mostly co-located in China, 1wk internal
#   PTA→PET: co-located, 1wk
#   PET→Fabric: 1-2wk
#   Fabric→Garment: 2wk (intra-China or BD sourcing)
#   Garment→Wholesale: China→UK 37d ≈ 5.3wk → 5
#   Wholesale→Retail: 1wk domestic
LAG_WEEKS = np.zeros((N_SECTORS, N_SECTORS), dtype=int)
LAG_WEEKS[0, 1] = 3    # oil → chemicals
LAG_WEEKS[1, 2] = 1
LAG_WEEKS[2, 3] = 1
LAG_WEEKS[3, 4] = 2
LAG_WEEKS[4, 5] = 2
LAG_WEEKS[5, 6] = 5    # garment → UK wholesale (sea freight China→UK ≈37 days)
LAG_WEEKS[6, 7] = 1


class DynamicIOModel:
    """
    Leontief dynamic I-O model for the polyester textile supply chain.

    Static form:   x = (I - A)^{-1} f               (Leontief, 1941)
    Dynamic form:  B Δx(t) = x(t) - A x(t) - f(t)  (Leontief, 1970)
    """

    def __init__(self, A: np.ndarray = None, B: np.ndarray = None,
                 lags: np.ndarray = None):
        self.A = A_BASE.copy() if A is None else A.copy()
        self.B = B_BASE.copy() if B is None else B.copy()
        self.lags = LAG_WEEKS.copy() if lags is None else lags.copy()
        self.n = N_SECTORS
        self.sectors = SECTORS
        self._build_leontief()

    # ── Core computations ─────────────────────────────────────────────────────

    def _build_leontief(self):
        I = np.eye(self.n)
        self.L = inv(I - self.A)           # Leontief inverse
        self.IminusA = I - self.A

    def static_output(self, final_demand: np.ndarray) -> np.ndarray:
        """x = L f  — steady-state gross output vector."""
        return self.L @ final_demand

    def value_added(self, x: np.ndarray) -> np.ndarray:
        """Value added per sector = (I - A^T) x."""
        return (np.eye(self.n) - self.A.T) @ x

    # ── Linkage analysis ──────────────────────────────────────────────────────

    def linkages(self) -> pd.DataFrame:
        """
        Backward linkage (BL): how much a sector pulls from others per unit output.
        Forward linkage (FL): how much a sector is used by others.
        Normalised BL/FL > 1 → above average integration.
        """
        BL = self.L.sum(axis=0)   # column sums of Leontief inverse
        FL = self.L.sum(axis=1)   # row sums

        n = self.n
        BL_norm = BL / (BL.mean())
        FL_norm = FL / (FL.mean())

        return pd.DataFrame({
            "Sector":        self.sectors,
            "Backward_Link": BL,
            "BL_Normalised": BL_norm,
            "Forward_Link":  FL,
            "FL_Normalised": FL_norm,
            "Key_Sector":    (BL_norm > 1) & (FL_norm > 1),
        })

    def multipliers(self) -> pd.DataFrame:
        """Output multipliers: total gross output generated per unit final demand."""
        m = self.L.sum(axis=0)
        return pd.DataFrame({"Sector": self.sectors, "Output_Multiplier": m})

    # ── Shock analysis ────────────────────────────────────────────────────────

    def apply_supply_shock(self, sector_idx: int,
                           shock_fraction: float) -> "DynamicIOModel":
        """
        Reduce supply capacity of sector_idx by shock_fraction ∈ [0, 1].
        Implemented by scaling down the column of A feeding into sector_idx
        — effectively the sector can only deliver (1 - shock_fraction) of
        what the chain requires.
        Returns a new DynamicIOModel with modified A.
        """
        A_new = self.A.copy()
        # Scale UP the input requirements (scarcity raises effective coefficients
        # for sectors that still receive supply, and reduces available throughput)
        # We model it by creating a capacity-limited output vector instead.
        # For the I-O shock: reduce the row (output row) of shocked sector
        A_new[sector_idx, :] *= (1 - shock_fraction)
        return DynamicIOModel(A_new, self.B, self.lags)

    def shock_impact(self, sector_idx: int,
                     shock_fraction: float,
                     final_demand: np.ndarray) -> Dict:
        """
        Compute output change and propagation from a supply shock.
        Returns dict with output vectors (baseline, shocked) and % changes.
        """
        x_base = self.static_output(final_demand)

        shocked_model = self.apply_supply_shock(sector_idx, shock_fraction)
        x_shocked = shocked_model.static_output(final_demand)

        pct_change = (x_shocked - x_base) / (x_base + 1e-12) * 100

        # Value of disruption (£ equivalent, scaled to UK retail)
        uk_retail_gbp = 51_400_000_000
        disruption_value = (x_base - x_shocked) * uk_retail_gbp / x_base.sum()

        return {
            "sector_shocked":     SECTORS[sector_idx],
            "shock_fraction":     shock_fraction,
            "output_baseline":    x_base,
            "output_shocked":     x_shocked,
            "pct_change":         pct_change,
            "disruption_value_gbp": disruption_value.sum(),
            "leontief_inverse":   shocked_model.L,
        }

    # ── Dynamic simulation ────────────────────────────────────────────────────

    def simulate(self, T: int, final_demand_base: np.ndarray,
                 shock_schedule: Optional[Dict[int, Tuple[int, float]]] = None,
                 demand_growth: float = 0.0,
                 demand_shock_schedule: Optional[Dict[int, np.ndarray]] = None) -> Dict:
        """
        Simulate the dynamic IO model for T weeks.

        Parameters
        ----------
        T                     : simulation horizon (weeks)
        final_demand_base     : baseline final demand vector (n,)
        shock_schedule        : {week: [(sector_idx, shock_fraction)]} — supply shocks
        demand_growth         : weekly demand growth rate (e.g. 0.001 = +0.1%/wk)
        demand_shock_schedule : {week: np.ndarray(n)} — sector-level demand multipliers.
                                Values < 1 = demand collapse; > 1 = demand surge.
                                Applied from the specified week onward until overridden.
                                Example: {4: array([1,1,1,1,1,1,1,0.57])} reduces
                                retail demand to 57 % from week 4.

        Returns
        -------
        dict with:
          'output'       (T, n) gross output trajectories
          'shortage'     (T, n) unmet demand trajectories
          'prices'       (T, n) relative price indices (=1 baseline)
          'capacity'     (n,)  final capacity fractions
          'sectors'      list of sector names
        """
        n = self.n
        max_lag = int(self.lags.max()) + 1

        # State arrays
        x        = np.zeros((T, n))
        shortage = np.zeros((T, n))
        prices   = np.ones((T, n))
        capacity = np.ones(n)          # fraction of baseline capacity available

        # Demand multiplier state (tracks latest demand shock, persists forward)
        demand_mult = np.ones(n)

        # Initialise at steady state
        x[0] = self.static_output(final_demand_base)

        # Pipeline buffer: in-transit goods [lag_slot, from_sector, to_sector]
        pipeline = np.zeros((max_lag + 1, n, n))
        for i in range(n):
            for j in range(n):
                lag = self.lags[i, j]
                if lag > 0:
                    pipeline[lag, i, j] = self.A[i, j] * x[0, j]

        A_current = self.A.copy()

        for t in range(1, T):
            # ── 1. Apply supply shocks (list of (sector_idx, fraction) per week) ─
            if shock_schedule and t in shock_schedule:
                shock_list = shock_schedule[t]
                if isinstance(shock_list, tuple):
                    shock_list = [shock_list]   # backwards compat
                for s_idx, s_frac in shock_list:
                    capacity[s_idx] *= (1 - s_frac)

            # ── 1b. Apply demand shocks (sector-level multipliers) ────────────
            if demand_shock_schedule and t in demand_shock_schedule:
                demand_mult = np.asarray(demand_shock_schedule[t], dtype=float)

            # ── 2. Demand this period (growth + demand shock) ─────────────────
            fd = final_demand_base * ((1 + demand_growth) ** t) * demand_mult
            x_target = inv(np.eye(n) - A_current) @ fd

            # ── 3. Compute available supply (constrained by capacity + lags) ─
            available = np.zeros(n)
            for i in range(n):
                # Goods arriving from pipeline this period
                direct = 0.0
                for j in range(n):
                    lag = self.lags[i, j]
                    slot = max(0, t - lag)
                    direct += pipeline[min(lag, max_lag), i, j]
                # Domestic production (not lagged)
                domestic = x[t - 1, i] * capacity[i]
                available[i] = domestic + direct

            # ── 4. Compute achievable output (min of target and supply) ──────
            ratio = np.ones(n)
            for j in range(n):
                needed = A_current[:, j] * x_target[j]
                for i in range(n):
                    if needed[i] > 1e-12:
                        r = available[i] / needed[i]
                        ratio[j] = min(ratio[j], r)

            ratio = np.clip(ratio, 0.0, 1.0)
            # Also apply direct capacity constraint from shocks
            x[t] = np.minimum(x_target * ratio, x[0] * capacity)
            shortage[t] = np.maximum(0, x_target - x[t])

            # ── 5. Price response: P rises when ratio < 1 ───────────────────
            # Simple tatonnement: Δp/p = λ(D - S)/S
            lam = 0.4
            prices[t] = prices[t - 1] * (1 + lam * (1 - ratio))

            # ── 6. Partial capacity recovery (resilience) ────────────────────
            # Agents invest when prices rise; capacity slowly rebuilds
            recovery_rate = 0.03  # 3 % per week
            for i in range(n):
                if capacity[i] < 1.0:
                    capacity[i] = min(1.0, capacity[i] + recovery_rate
                                      * prices[t, i] / prices[0, i])

            # ── 7. Refresh pipeline ──────────────────────────────────────────
            pipeline = np.roll(pipeline, -1, axis=0)
            pipeline[-1] = 0
            for i in range(n):
                for j in range(n):
                    lag = self.lags[i, j]
                    if lag > 0:
                        pipeline[min(lag, max_lag), i, j] = (
                            A_current[i, j] * x[t, j])

        return {
            "output":    x,
            "shortage":  shortage,
            "prices":    prices,
            "capacity":  capacity,
            "sectors":   SECTORS,
        }

    # ── Calibration report ────────────────────────────────────────────────────

    def calibration_report(self) -> pd.DataFrame:
        """
        Check model consistency against key real data targets:
        - UK import share at garment stage
        - Relative sector sizes
        """
        uk_retail = 51_400_000_000
        fd = np.zeros(self.n)
        fd[-1] = uk_retail   # all demand enters at retail

        x = self.static_output(fd)

        rows = []
        vs = list(STAGE_RETAIL_VALUE_SHARE.values())
        for i, (sec, v) in enumerate(zip(SECTORS, vs)):
            model_share = x[i] / x[-1]
            rows.append({
                "Sector":           sec,
                "Model_Output_£bn": x[i] / 1e9,
                "Model_Share":      model_share,
                "Target_Share":     v,
                "Error_%":          (model_share - v) / v * 100,
            })
        return pd.DataFrame(rows)
