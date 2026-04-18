"""
ghosh_model.py
Ghosh supply-side Input-Output model for the polyester textile supply chain.

The Ghosh (1958) model is the supply-driven counterpart to the Leontief
demand-driven model. Where Leontief traces how final demand pulls backward
through the supply chain, Ghosh traces how primary input constraints push
forward.

Theory
------
Output allocation coefficient matrix B:
    B_ij = z_ij / x_i     (share of sector i's gross output sold to sector j)

Relationship to Leontief A matrix:
    B = diag(x)^{-1} A diag(x)
    i.e. B_ij = A_ij × x_j / x_i

Ghosh inverse:
    G = (I - B)^{-1}

Supply-driven output identity:
    x^T = v^T G
    where v_i = x_i (1 - Σ_j B_ij) is value-added (primary inputs) at sector i.

Supply shock propagation:
    If primary inputs at sector i are reduced by fraction δ:
        Δv_i = -δ × v_i
        Δx^T = Δv^T G      (forward propagation to all downstream sectors)

Interpretation (Dietzenbacher 1997)
------------------------------------
The Ghosh model is interpretable as a price model: a supply shock (reduced
primary input availability) raises the price of that sector's output, which
passes forward as cost increases to downstream buyers. It should NOT be used
as a pure quantity model (it would imply unlimited substitutability of primary
inputs, violating conservation). We use it here as a **forward sensitivity**
tool: which sectors create the largest downstream ripple when their supply is
constrained?

Ghosh forward linkage vs Leontief forward linkage
--------------------------------------------------
The Leontief forward linkage (row sums of L) conflates forward and backward
effects. The Ghosh forward linkage (row sums of G) is the proper supply-side
measure of a sector's forward reach: total output change across all downstream
sectors per unit of primary input shock at the originating sector.

References
----------
  Ghosh A. (1958) "Input-Output Approach in an Allocation System." Economica 25.
  Dietzenbacher E. (1997) "In Vindication of the Ghosh Model." JRS 37:629-651.
  Miller & Blair (2009) §12.3.
"""

import numpy as np
import pandas as pd
from numpy.linalg import inv
from typing import Dict, List, Optional, Tuple

from real_data import SECTORS, N_SECTORS
from io_model import A_BASE


# ── Pre-defined supply shock scenarios (Ghosh equivalents) ───────────────────
# Each entry: {sector_idx: shock_fraction}
# Mirrors the Leontief shock scenarios so results are directly comparable.

GHOSH_SCENARIOS: Dict[str, Dict] = {
    "GS1": {
        "name":        "PTA Primary Input Constraint (China lockdown equivalent)",
        "description": "China's PTA capacity constrained 50% — primary input shock "
                       "propagates forward to PET, Fabric, Garment, Retail.",
        "shocks":      {2: 0.50},          # PTA_Production
    },
    "GS2": {
        "name":        "MEG/Chemical Supply Constraint",
        "description": "Saudi + Middle East chemical primary inputs constrained 25%.",
        "shocks":      {1: 0.25},          # Chemical_Processing
    },
    "GS3": {
        "name":        "Upstream Oil Supply Constraint",
        "description": "Oil extraction primary inputs constrained 20% "
                       "(energy cost shock / resource nationalism).",
        "shocks":      {0: 0.20},          # Oil_Extraction
    },
    "GS4": {
        "name":        "Fabric & Garment Dual Constraint",
        "description": "Fabric (43% China) and Garment (27% China) primary inputs "
                       "simultaneously constrained 40%.",
        "shocks":      {4: 0.40, 5: 0.40},  # Fabric + Garment
    },
    "GS5": {
        "name":        "Multi-Node Upstream Constraint (pandemic equivalent)",
        "description": "PTA, PET, Fabric, Garment primary inputs all constrained 50%. "
                       "Analogous to Leontief S5.",
        "shocks":      {2: 0.50, 3: 0.50, 4: 0.50, 5: 0.50},
    },
}


class GhoshModel:
    """
    Ghosh supply-side IO model for the 8-sector polyester textile supply chain.

    Parameters
    ----------
    A : (N, N) ndarray, optional
        Leontief technical coefficient matrix. Defaults to A_BASE.
    x_baseline : (N,) ndarray, optional
        Baseline gross output vector. If None, computed from A_BASE and UK
        retail final demand of £51.4 bn.
    """

    UK_RETAIL_GBP: float = 51_400_000_000

    def __init__(
        self,
        A: Optional[np.ndarray] = None,
        x_baseline: Optional[np.ndarray] = None,
    ):
        self.A = A_BASE.copy() if A is None else A.copy()
        self.n = N_SECTORS

        # Baseline gross output: x = L f where f = [0,...,0, UK_retail]
        if x_baseline is None:
            I = np.eye(self.n)
            L = inv(I - self.A)
            fd = np.zeros(self.n)
            fd[-1] = self.UK_RETAIL_GBP
            self.x = L @ fd
        else:
            self.x = x_baseline.copy()

        self._build()

    # ONS IOT 2023 GVA/Output rates — primary inputs (labour + capital) per
    # unit gross output at each supply chain stage (Dietzenbacher 1997 interpretation)
    _GVA_RATES = np.array([
        0.684,   # Oil_Extraction    — ONS CPA B
        0.082,   # Chemical_Process  — ONS CPA C20B
        0.223,   # PTA_Production    — ONS CPA C20
        0.478,   # PET_Resin_Yarn    — ONS CPA C13
        0.478,   # Fabric_Weaving    — ONS CPA C13
        0.552,   # Garment_Assembly  — ONS CPA C14
        0.528,   # UK_Wholesale      — ONS CPA G46
        0.598,   # UK_Retail         — ONS CPA G47
    ])

    def _build(self):
        """
        Derive B matrix, primary-input vector v, and Ghosh inverse G.

        Primary inputs v use ONS IOT GVA rates rather than the IO row-balance
        identity. Our model places all final demand at UK_Retail, which makes
        row-balance derived v_i = 0 for all upstream sectors (their entire
        output goes to intermediate use). Using exogenous GVA rates restores
        non-zero primary inputs at every stage, consistent with the Dietzenbacher
        (1997) price-model interpretation of Ghosh.

        The Ghosh identity x^T = v^T G does NOT hold with exogenous GVA rates
        (it only holds when v equals final demand from the IO row balance).
        G is used here purely as a forward-sensitivity multiplier matrix:
            G_ij = change in sector j gross output per unit of primary input
                   supplied at sector i — tracing forward cost/supply propagation.
        """
        x_inv = np.where(self.x > 0, 1.0 / self.x, 0.0)

        # B_ij = z_ij / x_i = A_ij × x_j / x_i
        self.B = np.diag(x_inv) @ self.A @ np.diag(self.x)

        # Primary-input vector: v_i = GVA_rate[i] × x_i
        self.v = self._GVA_RATES * self.x

        # Ghosh inverse G = (I − B)^{-1}
        self.G = inv(np.eye(self.n) - self.B)

    # ── Linkage analysis ──────────────────────────────────────────────────────

    def forward_linkages(self) -> pd.DataFrame:
        """
        Ghosh forward linkage index for each sector.

        FL_i = row sum of G = total output induced across all sectors
               per unit of primary input at sector i.

        FL_norm > 1 → above-average forward reach (supply-critical sector).
        """
        FL      = self.G.sum(axis=1)
        mean_FL = FL.mean()

        return pd.DataFrame({
            "Sector":         SECTORS,
            "Value_Added_GBP": self.v,
            "VA_Share_%":     self.v / self.v.sum() * 100,
            "FL_Ghosh":       FL,
            "FL_Ghosh_Norm":  FL / mean_FL,
            "Supply_Critical": FL / mean_FL > 1.0,
        })

    def output_multipliers(self) -> pd.DataFrame:
        """
        Ghosh output multiplier: total gross output change per £1 reduction
        in primary inputs at each sector.
        (= row sums of G, same as FL but presented as multipliers)
        """
        m = self.G.sum(axis=1)
        return pd.DataFrame({
            "Sector":            SECTORS,
            "Ghosh_Multiplier":  m,
        })

    def leontief_vs_ghosh_linkages(self) -> pd.DataFrame:
        """
        Compare Leontief backward linkage (demand-pull) with Ghosh forward
        linkage (supply-push) for each sector.

        Key sectors: BL_norm > 1 AND FL_norm > 1 → structurally central.
        """
        I   = np.eye(self.n)
        L   = inv(I - self.A)
        BL  = L.sum(axis=0)
        FL  = self.G.sum(axis=1)

        return pd.DataFrame({
            "Sector":          SECTORS,
            "BL_Leontief":     BL,
            "BL_Norm":         BL / BL.mean(),
            "FL_Ghosh":        FL,
            "FL_Norm":         FL / FL.mean(),
            "Key_Sector":      (BL / BL.mean() > 1.0) & (FL / FL.mean() > 1.0),
            "Supply_Critical": FL / FL.mean() > 1.0,
            "Demand_Critical": BL / BL.mean() > 1.0,
        })

    # ── Supply shock analysis ─────────────────────────────────────────────────

    def supply_shock(
        self,
        sector_shocks: Dict[int, float],
    ) -> Dict:
        """
        Apply primary input supply shock(s) and propagate forward via Ghosh.

        A shock at sector i means its primary inputs (labour + capital) are
        reduced by fraction δ.  The direct output loss is:
            Δx_i_direct = -δ × v_i / GVA_rate_i = -δ × x_i

        Forward propagation via Ghosh inverse:
            Δx_j = Σ_i Δv_i × G[i, j]
        where Δv_i = -δ × v_i (primary input loss at shocked sector i).

        Parameters
        ----------
        sector_shocks : {sector_idx: shock_fraction}
            shock_fraction ∈ [0, 1] — fraction of primary inputs lost.

        Returns
        -------
        dict with:
            v_baseline, v_shocked  : (N,) primary-input vectors
            x_baseline, x_shocked  : (N,) gross output vectors
            delta_v, delta_x       : (N,) absolute changes
            pct_change             : (N,) % change in gross output
            total_output_loss_gbp  : scalar — total output lost across chain
            welfare_proxy_gbp      : VA-weighted downstream loss (welfare proxy)
        """
        v_shocked = self.v.copy()
        for s_idx, frac in sector_shocks.items():
            v_shocked[s_idx] *= (1.0 - frac)

        delta_v = v_shocked - self.v           # (N,) negative for shocked sectors

        # Forward propagation: Δx_j = Σ_i Δv_i × G[i, j]
        delta_x  = delta_v @ self.G            # row-vector × G
        x_shocked = self.x + delta_x
        pct_change = delta_x / (self.x + 1e-12) * 100

        # Welfare proxy: downstream VA lost
        va_rates = self._GVA_RATES
        welfare  = -(delta_x * va_rates)
        welfare[welfare < 0] = 0

        return {
            "v_baseline":            self.v,
            "v_shocked":             v_shocked,
            "x_baseline":            self.x,
            "x_shocked":             x_shocked,
            "delta_v":               delta_v,
            "delta_x":               delta_x,
            "pct_change":            pct_change,
            "total_output_loss_gbp": (-delta_x).clip(min=0).sum(),
            "welfare_proxy_gbp":     welfare.sum(),
        }

    def shock_summary_df(
        self,
        sector_shocks: Dict[int, float],
        scenario_name: str = "",
    ) -> pd.DataFrame:
        """
        Tabular summary of a Ghosh supply shock result.
        """
        res = self.supply_shock(sector_shocks)
        rows = []
        for i, s in enumerate(SECTORS):
            rows.append({
                "Scenario":         scenario_name,
                "Sector":           s,
                "VA_Baseline_GBP":  res["v_baseline"][i],
                "VA_Shocked_GBP":   res["v_shocked"][i],
                "Output_Baseline":  res["x_baseline"][i],
                "Output_Shocked":   res["x_shocked"][i],
                "Output_Change_%":  round(res["pct_change"][i], 2),
                "Directly_Shocked": i in sector_shocks,
            })
        return pd.DataFrame(rows)

    # ── All Ghosh scenarios ───────────────────────────────────────────────────

    def run_all_scenarios(self) -> Dict[str, pd.DataFrame]:
        """
        Run all five Ghosh scenarios (GS1–GS5) and return summary DataFrames.
        """
        results = {}
        for sc_id, sc in GHOSH_SCENARIOS.items():
            df = self.shock_summary_df(sc["shocks"], sc_id)
            results[sc_id] = df
        return results

    def scenarios_comparison(self) -> pd.DataFrame:
        """
        Cross-scenario comparison table: total output loss, welfare proxy,
        worst-hit downstream sector, and Leontief forward-cascade to retail.

        Leontief supply-shock comparison uses the capacity-constraint method:
        reduce output of shocked sectors directly, then compute the cascade
        to retail via the supply-ratio propagation (same mechanism as
        DynamicIOModel.simulate with capacity constraints).
        """
        rows = []
        L = inv(np.eye(self.n) - self.A)
        fd = np.zeros(self.n)
        fd[-1] = self.UK_RETAIL_GBP

        for sc_id, sc in GHOSH_SCENARIOS.items():
            res = self.supply_shock(sc["shocks"])
            worst_idx = res["pct_change"].argmin()

            # Leontief forward cascade: reduce shocked sectors' capacity and
            # propagate the supply constraint forward through the column ratios.
            # For each shocked sector i: available[i] = (1-frac) × x[i]
            # Downstream sector j can achieve at most:
            #   ratio[j] = min over inputs i of available[i] / (A[i,j] × x[j])
            # x_shocked[j] = x[j] × ratio[j]
            capacity = np.ones(self.n)
            for s_idx, frac in sc["shocks"].items():
                capacity[s_idx] *= (1 - frac)

            available = self.x * capacity
            ratio = np.ones(self.n)
            for j in range(self.n):
                for i in range(self.n):
                    needed = self.A[i, j] * self.x[j]
                    if needed > 1e-12:
                        ratio[j] = min(ratio[j], available[i] / needed)
            ratio = np.clip(ratio, 0, 1)
            x_l_sh = self.x * ratio
            leontief_cascade_pct = (x_l_sh[-1] - self.x[-1]) / (self.x[-1] + 1e-12) * 100

            rows.append({
                "Scenario":                sc_id,
                "Name":                    sc["name"],
                "Sectors_Shocked":         ", ".join(SECTORS[i] for i in sc["shocks"]),
                "Total_Output_Loss_GBPbn": round(res["total_output_loss_gbp"] / 1e9, 3),
                "Welfare_Proxy_GBPbn":     round(res["welfare_proxy_gbp"] / 1e9, 3),
                "Ghosh_Retail_Change_%":   round(res["pct_change"][-1], 2),
                "Worst_Sector":            SECTORS[worst_idx],
                "Worst_Sector_Change_%":   round(res["pct_change"][worst_idx], 2),
                "Leontief_Cascade_Retail_%": round(leontief_cascade_pct, 2),
            })
        return pd.DataFrame(rows)

    # ── MRIO Ghosh ────────────────────────────────────────────────────────────

    def mrio_ghosh(
        self,
        mrio_model,
    ) -> "MRIOGhoshResult":
        """
        Build a Ghosh model on top of the 64-sector MRIO system.

        Parameters
        ----------
        mrio_model : MRIOModel instance

        Returns
        -------
        MRIOGhoshResult with G_mrio, forward linkages, and shock methods.
        """
        return MRIOGhoshResult(mrio_model)


class MRIOGhoshResult:
    """
    Ghosh model applied to the 64-dimensional MRIO system.

    B_MRIO = diag(1/x_mrio) @ A_MRIO @ diag(x_mrio)
    G_MRIO = (I - B_MRIO)^{-1}
    """

    def __init__(self, mrio_model):
        from mrio_model import REGIONS, N_REGIONS, REGION_LABELS

        self.mrio   = mrio_model
        self.n      = mrio_model.A_mrio.shape[0]   # 64
        self.REGIONS = REGIONS
        self.N_REGIONS = N_REGIONS
        self.REGION_LABELS = REGION_LABELS

        # Baseline output from UK retail final demand
        f       = mrio_model.uk_final_demand()
        self.x  = mrio_model.L_mrio @ f           # (64,)

        # Build B_MRIO = diag(1/x) @ A_MRIO @ diag(x)
        # Safe inversion: sectors with zero output (e.g. GBR Oil) get 0
        with np.errstate(divide="ignore", invalid="ignore"):
            x_inv = np.where(self.x > 0, 1.0 / self.x, 0.0)
        self.B_mrio = np.diag(x_inv) @ mrio_model.A_mrio @ np.diag(self.x)

        # Primary-input vector: use ONS GVA rates tiled across regions.
        # Row-balance approach (v_i = x_i*(1-rowsum(B))) yields v=0 for all
        # upstream sectors because their entire output is intermediate —
        # identical issue to single-region GhoshModel. GVA rates fix this.
        self.v = mrio_model.va_rates * self.x   # (64,) = tiled GVA × outputs

        # Ghosh inverse G_MRIO = (I - B_MRIO)^{-1}
        self.G_mrio = inv(np.eye(self.n) - self.B_mrio)

    def forward_linkages_by_region(self) -> pd.DataFrame:
        """
        Aggregate Ghosh forward linkages from 64-sector MRIO to region level.
        FL_region = sum of row sums of G_MRIO for all sectors in that region.
        """
        from real_data import SECTORS, N_SECTORS

        FL   = self.G_mrio.sum(axis=1)
        mean = FL.mean()

        rows = []
        for r_idx, region in enumerate(self.REGIONS):
            for s_idx, sector in enumerate(SECTORS):
                fi = r_idx * N_SECTORS + s_idx
                rows.append({
                    "Region":        region,
                    "Region_Label":  self.REGION_LABELS[region],
                    "Sector":        sector,
                    "FL_MRIO_Ghosh": round(FL[fi], 4),
                    "FL_Norm":       round(FL[fi] / mean, 3),
                })

        df = pd.DataFrame(rows)

        # Region-level aggregate
        region_agg = (
            df.groupby(["Region", "Region_Label"])["FL_MRIO_Ghosh"]
            .sum()
            .reset_index()
            .sort_values("FL_MRIO_Ghosh", ascending=False)
        )
        return df, region_agg

    def china_supply_shock(
        self, shock_fraction: float = 0.50
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Apply 50% primary input shock to ALL China sectors in the MRIO system.
        Propagates forward via G_MRIO.

        Returns (detail_df, region_summary_df).
        """
        from real_data import SECTORS, N_SECTORS
        from mrio_model import REGION_IDX

        # Use Δv propagation: delta_v @ G_mrio → delta_x (forward cascade)
        delta_v   = np.zeros(self.n)
        r_chn_idx = REGION_IDX["CHN"]
        for s_idx in range(N_SECTORS):
            fi = r_chn_idx * N_SECTORS + s_idx
            delta_v[fi] = -shock_fraction * self.v[fi]

        delta_x    = delta_v @ self.G_mrio
        x_shocked  = self.x + delta_x
        pct_change = delta_x / (self.x + 1e-12) * 100

        rows = []
        for r_idx, region in enumerate(self.REGIONS):
            for s_idx, sector in enumerate(SECTORS):
                fi = r_idx * N_SECTORS + s_idx
                rows.append({
                    "Region":          region,
                    "Region_Label":    self.REGION_LABELS[region],
                    "Sector":          sector,
                    "Output_Baseline": round(self.x[fi], 2),
                    "Output_Shocked":  round(x_shocked[fi], 2),
                    "Pct_Change":      round(pct_change[fi], 2),
                    "Directly_Shocked": region == "CHN",
                })

        detail = pd.DataFrame(rows)

        region_sum = (
            detail.groupby(["Region", "Region_Label"])[
                ["Output_Baseline", "Output_Shocked"]
            ]
            .sum()
            .reset_index()
        )
        region_sum["Pct_Change"] = (
            (region_sum["Output_Shocked"] - region_sum["Output_Baseline"])
            / (region_sum["Output_Baseline"] + 1e-12) * 100
        ).round(2)
        region_sum = region_sum.sort_values("Pct_Change").reset_index(drop=True)

        return detail, region_sum
