"""
mrio_model.py
Multi-Regional Input-Output (MRIO) model for the polyester textile supply chain.

Extends the single-region Leontief model to 8 geographic regions × 8 supply chain
stages = 64-dimensional system.

Regions
-------
  CHN — China
  SAS — South/Southeast Asia (India, Bangladesh, Vietnam, Cambodia, Sri Lanka,
         Pakistan, Myanmar)
  EAS — East Asia ex-China (South Korea, Japan, Taiwan)
  MDE — Middle East (Saudi Arabia, UAE, Iraq)
  AME — Americas (USA, Canada)
  EUR — Europe ex-UK (Turkey, Italy)
  GBR — United Kingdom
  ROW — Rest of World

Calibration: proportional-sourcing assumption
  A_MRIO[r*N+i, s*N+j] = A_BASE[i,j] × regional_shares[i, r]

Interpretation: to produce one unit of sector j output in region s, you need
A_BASE[i,j] units of sector i in total; region r supplies regional_shares[i,r]
of that requirement.

This preserves Hawkins-Simon (column sums of A_MRIO equal column sums of A_BASE).

Limitation: proportional sourcing is a standard MRIO calibration proxy used when
bilateral trade data are unavailable (e.g. no WIOD subscription). Region-specific
IO tables would allow heterogeneous domestic coefficients across regions.

References
----------
  Miller & Blair (2009) Input-Output Analysis: Foundations and Extensions, §3
  Los, Timmer & de Vries (2015) "How important are exports for job growth?" JIE
  Hertel et al. (2012) GTAP 8 Data Base documentation
"""

import numpy as np
import pandas as pd
from numpy.linalg import inv
from typing import Dict, List, Optional, Tuple

from real_data import (
    SECTORS, N_SECTORS, STAGE_GEOGRAPHY, STAGE_RETAIL_VALUE_SHARE,
)
from io_model import A_BASE


# ── Region definitions ────────────────────────────────────────────────────────

REGIONS: List[str] = ["CHN", "SAS", "EAS", "MDE", "AME", "EUR", "GBR", "ROW"]
N_REGIONS: int = len(REGIONS)
N_TOTAL: int = N_REGIONS * N_SECTORS   # 64

REGION_IDX: Dict[str, int] = {r: i for i, r in enumerate(REGIONS)}
SECTOR_IDX: Dict[str, int] = {s: i for i, s in enumerate(SECTORS)}

REGION_LABELS: Dict[str, str] = {
    "CHN": "China",
    "SAS": "South/SE Asia",
    "EAS": "East Asia (ex-CN)",
    "MDE": "Middle East",
    "AME": "Americas",
    "EUR": "Europe (ex-UK)",
    "GBR": "United Kingdom",
    "ROW": "Rest of World",
}

# Map STAGE_GEOGRAPHY country keys → MRIO region codes
COUNTRY_TO_REGION: Dict[str, str] = {
    "China":        "CHN",
    "India":        "SAS",
    "Bangladesh":   "SAS",
    "Vietnam":      "SAS",
    "Cambodia":     "SAS",
    "Sri_Lanka":    "SAS",
    "Pakistan":     "SAS",
    "Myanmar":      "SAS",
    "South_Korea":  "EAS",
    "Japan":        "EAS",
    "Taiwan":       "EAS",
    "Saudi_Arabia": "MDE",
    "UAE":          "MDE",
    "Iraq":         "MDE",
    "USA":          "AME",
    "Canada":       "AME",
    "Turkey":       "EUR",
    "Italy":        "EUR",
    "UK":           "GBR",
    "Other":        "ROW",
}

# ONS IOT 2023 GVA/Output rates by supply chain stage
# Applied uniformly across regions (simplification — see module docstring)
_GVA_RATES = np.array([
    0.684,   # Oil_Extraction    — ONS CPA B
    0.082,   # Chemical_Process  — ONS CPA C20B (refinery-dominated, low VA)
    0.223,   # PTA_Production    — ONS CPA C20 (chemicals)
    0.478,   # PET_Resin_Yarn    — ONS CPA C13 (textiles)
    0.478,   # Fabric_Weaving    — ONS CPA C13
    0.552,   # Garment_Assembly  — ONS CPA C14 (apparel)
    0.528,   # UK_Wholesale      — ONS CPA G46
    0.598,   # UK_Retail         — ONS CPA G47
])


# ── Helper functions ──────────────────────────────────────────────────────────

def flat(region: str, sector: str) -> int:
    """Convert (region, sector) pair to flat 64-vector index."""
    return REGION_IDX[region] * N_SECTORS + SECTOR_IDX[sector]


def build_regional_shares() -> np.ndarray:
    """
    Aggregate STAGE_GEOGRAPHY country shares into the 8 MRIO regions.

    Returns
    -------
    shares : (N_SECTORS, N_REGIONS) ndarray
        shares[i, r] = fraction of global sector-i production in region r.
        Each row sums to 1.0.
    """
    shares = np.zeros((N_SECTORS, N_REGIONS))

    for s_idx, sector in enumerate(SECTORS):
        geo = STAGE_GEOGRAPHY.get(sector, {})
        for country, share in geo.items():
            r_code = COUNTRY_TO_REGION.get(country, "ROW")
            r_idx  = REGION_IDX[r_code]
            shares[s_idx, r_idx] += share

    # Normalise rows to 1.0 (guards against rounding discrepancies)
    row_sums = shares.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return shares / row_sums


def build_mrio_matrix(regional_shares: np.ndarray) -> np.ndarray:
    """
    Build the (N_TOTAL × N_TOTAL) MRIO technical coefficient matrix.

    Index convention: flat index = region_idx * N_SECTORS + sector_idx

    A_MRIO[r*N+i, s*N+j] = A_BASE[i,j] × regional_shares[i, r]

    Column sums of A_MRIO equal column sums of A_BASE (Hawkins-Simon preserved).

    Parameters
    ----------
    regional_shares : (N_SECTORS, N_REGIONS)

    Returns
    -------
    A_mrio : (N_TOTAL, N_TOTAL) ndarray
    """
    A_mrio = np.zeros((N_TOTAL, N_TOTAL))

    for r in range(N_REGIONS):
        for s in range(N_REGIONS):
            for i in range(N_SECTORS):
                for j in range(N_SECTORS):
                    if A_BASE[i, j] > 0:
                        row = r * N_SECTORS + i
                        col = s * N_SECTORS + j
                        A_mrio[row, col] = A_BASE[i, j] * regional_shares[i, r]

    return A_mrio


# ── MRIO Model class ──────────────────────────────────────────────────────────

class MRIOModel:
    """
    Multi-Regional Input-Output model for the polyester textile supply chain.

    System: x = (I - A_MRIO)^{-1} f
    where x, f are 64-vectors (8 regions × 8 sectors).

    Final demand is UK retail only: f[GBR, UK_Retail] = £51.4 bn.
    """

    UK_RETAIL_GBP: float = 51_400_000_000

    def __init__(self):
        self.regional_shares = build_regional_shares()   # (N_SECTORS, N_REGIONS)
        self.A_mrio = build_mrio_matrix(self.regional_shares)

        # Verify Hawkins-Simon on full 64×64 matrix
        col_sums = self.A_mrio.sum(axis=0)
        assert (col_sums < 1.0 - 1e-9).all(), (
            f"MRIO Hawkins-Simon violated. Max col sum = {col_sums.max():.4f}"
        )

        I = np.eye(N_TOTAL)
        self.L_mrio = inv(I - self.A_mrio)   # 64×64 Leontief inverse

        # Value-added rate vector (tiled across regions)
        self.va_rates = np.tile(_GVA_RATES, N_REGIONS)   # (64,)

    # ── Core computations ─────────────────────────────────────────────────────

    def uk_final_demand(self, scale: float = None) -> np.ndarray:
        """Final demand vector: UK retail only."""
        f = np.zeros(N_TOTAL)
        f[flat("GBR", "UK_Retail")] = scale if scale else self.UK_RETAIL_GBP
        return f

    def gross_output(self, f: np.ndarray = None) -> np.ndarray:
        """x = L f — gross output vector (64,)."""
        if f is None:
            f = self.uk_final_demand()
        return self.L_mrio @ f

    # ── Regional production shares ────────────────────────────────────────────

    def regional_shares_table(self) -> pd.DataFrame:
        """
        Production share (%) by region and supply chain stage.
        Rows = sectors, columns = regions.
        """
        rows = []
        for s_idx, sector in enumerate(SECTORS):
            row = {"Sector": sector}
            for r_idx, region in enumerate(REGIONS):
                row[region] = round(self.regional_shares[s_idx, r_idx] * 100, 1)
            rows.append(row)
        return pd.DataFrame(rows)

    # ── Value-added decomposition ─────────────────────────────────────────────

    def value_added_decomposition(
        self, f: np.ndarray = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Decompose the value-added content of UK final textile demand by
        region of origin.

        Value added created in (region r, sector i) per unit of UK demand:
            VA[r, i] = va_rate[i] × x[r, i]

        Returns
        -------
        detail : DataFrame — (region, sector, gross output, value added, share %)
        summary : DataFrame — (region, total VA £bn, VA share %)
        """
        x  = self.gross_output(f)
        va = self.va_rates * x

        rows = []
        for r_idx, region in enumerate(REGIONS):
            for s_idx, sector in enumerate(SECTORS):
                fi = r_idx * N_SECTORS + s_idx
                rows.append({
                    "Region":            region,
                    "Region_Label":      REGION_LABELS[region],
                    "Sector":            sector,
                    "Gross_Output_GBP":  x[fi],
                    "Value_Added_GBP":   va[fi],
                    "Prod_Share_%":      round(self.regional_shares[s_idx, r_idx] * 100, 1),
                })

        detail = pd.DataFrame(rows)

        total_va   = va.sum()
        region_grp = detail.groupby(["Region", "Region_Label"])["Value_Added_GBP"].sum()
        summary    = region_grp.reset_index()
        summary.columns = ["Region", "Region_Label", "Value_Added_GBP"]
        summary["VA_GBP_bn"]   = (summary["Value_Added_GBP"] / 1e9).round(2)
        summary["VA_Share_%"]  = (summary["Value_Added_GBP"] / total_va * 100).round(1)
        summary = summary.sort_values("Value_Added_GBP", ascending=False).reset_index(drop=True)

        return detail, summary

    # ── Linkage analysis ──────────────────────────────────────────────────────

    def backward_linkages(self) -> pd.DataFrame:
        """
        Backward linkage (BL) for each (region, sector) pair.
        BL = column sum of Leontief inverse = total output triggered per unit
        of final demand directed at that region-sector.
        BL_norm > 1 → above-average upstream pull.
        """
        BL      = self.L_mrio.sum(axis=0)
        mean_BL = BL.mean()

        rows = []
        for r_idx, region in enumerate(REGIONS):
            for s_idx, sector in enumerate(SECTORS):
                fi = r_idx * N_SECTORS + s_idx
                rows.append({
                    "Region":         region,
                    "Region_Label":   REGION_LABELS[region],
                    "Sector":         sector,
                    "BL":             round(BL[fi], 4),
                    "BL_Normalised":  round(BL[fi] / mean_BL, 3),
                    "Key_Upstream":   BL[fi] / mean_BL > 1.0,
                })

        return pd.DataFrame(rows).sort_values("BL", ascending=False).reset_index(drop=True)

    def forward_linkages(self) -> pd.DataFrame:
        """
        Forward linkage (FL) for each (region, sector) pair.
        FL = row sum of Leontief inverse = how widely used this region-sector
        is as an input supplier across the rest of the system.
        FL_norm > 1 → above-average downstream influence.
        """
        FL      = self.L_mrio.sum(axis=1)
        mean_FL = FL.mean()

        rows = []
        for r_idx, region in enumerate(REGIONS):
            for s_idx, sector in enumerate(SECTORS):
                fi = r_idx * N_SECTORS + s_idx
                rows.append({
                    "Region":         region,
                    "Region_Label":   REGION_LABELS[region],
                    "Sector":         sector,
                    "FL":             round(FL[fi], 4),
                    "FL_Normalised":  round(FL[fi] / mean_FL, 3),
                    "Key_Downstream": FL[fi] / mean_FL > 1.0,
                })

        return pd.DataFrame(rows).sort_values("FL", ascending=False).reset_index(drop=True)

    def linkage_summary(self) -> pd.DataFrame:
        """
        Aggregated backward and forward linkages at the region level.
        """
        BL_col = self.L_mrio.sum(axis=0)
        FL_col = self.L_mrio.sum(axis=1)

        rows = []
        for r_idx, region in enumerate(REGIONS):
            region_bl = BL_col[r_idx * N_SECTORS:(r_idx + 1) * N_SECTORS]
            region_fl = FL_col[r_idx * N_SECTORS:(r_idx + 1) * N_SECTORS]
            rows.append({
                "Region":        region,
                "Region_Label":  REGION_LABELS[region],
                "Total_BL":      round(region_bl.sum(), 3),
                "Mean_BL":       round(region_bl.mean(), 3),
                "Total_FL":      round(region_fl.sum(), 3),
                "Mean_FL":       round(region_fl.mean(), 3),
            })

        return pd.DataFrame(rows).sort_values("Total_BL", ascending=False).reset_index(drop=True)

    # ── Effective China exposure ──────────────────────────────────────────────

    def effective_china_exposure(self) -> pd.DataFrame:
        """
        MRIO-based effective China exposure for each supply chain stage.

        For each sector j across all regions, compute what fraction of the
        total gross output requirement (direct + indirect, via Leontief) is
        sourced from China:

            china_share[j] = sum_r sum_i L[(CHN,i), (r,j)] * x[(r,j)] /
                             sum_r sum_i L[(*, i), (r,j)] * x[(r,j)]

        Because proportional sourcing is symmetric, this simplifies to
        the regional share for each sector weighted by the Leontief multiplier
        structure. The indirect effects elevate China's share above raw
        production shares because Chinese intermediates also use Chinese inputs.

        Returns
        -------
        DataFrame with columns: Sector, Nominal_China_%, MRIO_China_%,
        Amplification_Factor
        """
        f = self.uk_final_demand()
        x = self.L_mrio @ f   # gross outputs by region-sector

        r_chn = REGION_IDX["CHN"]

        rows = []
        for s_idx, sector in enumerate(SECTORS):
            # Nominal share: direct production geography
            nominal = self.regional_shares[s_idx, r_chn] * 100

            # MRIO share: China's output of this sector / total world output of sector
            china_output  = x[r_chn * N_SECTORS + s_idx]
            world_output  = sum(x[r * N_SECTORS + s_idx] for r in range(N_REGIONS))
            mrio_pct      = china_output / (world_output + 1e-12) * 100

            rows.append({
                "Sector":               sector,
                "Nominal_China_%":      round(nominal, 1),
                "MRIO_China_%":         round(mrio_pct, 1),
                "Amplification_Factor": round(mrio_pct / (nominal + 1e-6), 3),
            })

        return pd.DataFrame(rows)

    # ── Shock analysis ────────────────────────────────────────────────────────

    def regional_shock(
        self,
        shocked_region: str,
        shock_fraction: float,
        shocked_sectors: Optional[List[str]] = None,
        f: np.ndarray = None,
    ) -> pd.DataFrame:
        """
        Apply a supply shock to all sectors (or a subset) in a given region.
        Reduces the shocked region's output rows in A_MRIO by shock_fraction.

        Parameters
        ----------
        shocked_region  : region code, e.g. "CHN"
        shock_fraction  : capacity reduction ∈ [0, 1]
        shocked_sectors : list of sector names; None → all sectors
        f               : final demand vector; None → UK retail £51.4 bn

        Returns
        -------
        DataFrame: region, sector, baseline output, shocked output, % change
        """
        if f is None:
            f = self.uk_final_demand()
        if shocked_sectors is None:
            shocked_sectors = SECTORS

        A_shocked = self.A_mrio.copy()
        r_idx = REGION_IDX[shocked_region]
        for sector in shocked_sectors:
            s_idx = SECTOR_IDX[sector]
            fi    = r_idx * N_SECTORS + s_idx
            A_shocked[fi, :] *= (1 - shock_fraction)   # supply row scaled down

        L_shocked = inv(np.eye(N_TOTAL) - A_shocked)
        x_base    = self.L_mrio  @ f
        x_shocked = L_shocked    @ f
        pct_chg   = (x_shocked - x_base) / (x_base + 1e-12) * 100

        rows = []
        for ri, region in enumerate(REGIONS):
            for si, sector in enumerate(SECTORS):
                fi = ri * N_SECTORS + si
                rows.append({
                    "Region":          region,
                    "Region_Label":    REGION_LABELS[region],
                    "Sector":          sector,
                    "Output_Baseline": round(x_base[fi], 2),
                    "Output_Shocked":  round(x_shocked[fi], 2),
                    "Pct_Change":      round(pct_chg[fi], 2),
                    "Directly_Shocked": (
                        region == shocked_region and sector in shocked_sectors
                    ),
                })

        return pd.DataFrame(rows)

    def china_shock_summary(
        self, shock_fraction: float = 0.50
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Convenience wrapper: 50% China supply shock across all sectors.

        Returns
        -------
        by_region   : output change aggregated by region
        by_sector   : output change aggregated by sector (summed across regions)
        """
        detail = self.regional_shock("CHN", shock_fraction)

        by_region = (
            detail.groupby(["Region", "Region_Label"])[
                ["Output_Baseline", "Output_Shocked"]
            ]
            .sum()
            .reset_index()
        )
        by_region["Pct_Change"] = (
            (by_region["Output_Shocked"] - by_region["Output_Baseline"])
            / (by_region["Output_Baseline"] + 1e-12) * 100
        ).round(2)
        by_region = by_region.sort_values("Pct_Change").reset_index(drop=True)

        by_sector = (
            detail.groupby("Sector")[["Output_Baseline", "Output_Shocked"]]
            .sum()
            .reset_index()
        )
        by_sector["Pct_Change"] = (
            (by_sector["Output_Shocked"] - by_sector["Output_Baseline"])
            / (by_sector["Output_Baseline"] + 1e-12) * 100
        ).round(2)
        by_sector = by_sector.sort_values("Pct_Change").reset_index(drop=True)

        return by_region, by_sector

    # ── Leontief decomposition (domestic vs. foreign) ─────────────────────────

    def leontief_decomposition(self) -> pd.DataFrame:
        """
        Decompose the total output multiplier for UK retail demand into
        domestic (GBR) and foreign components, by region.

        For UK_Retail column of the Leontief inverse:
            L[(r, i), (GBR, Retail)] = output of sector i in region r induced
            per unit of UK retail final demand.

        Returns
        -------
        DataFrame: region, sector, L_coefficient (output induced per £ UK retail)
        """
        gbr_retail_col = flat("GBR", "UK_Retail")
        col = self.L_mrio[:, gbr_retail_col]

        rows = []
        for ri, region in enumerate(REGIONS):
            for si, sector in enumerate(SECTORS):
                fi = ri * N_SECTORS + si
                rows.append({
                    "Region":       region,
                    "Region_Label": REGION_LABELS[region],
                    "Sector":       sector,
                    "L_coeff":      round(col[fi], 6),
                })

        df = pd.DataFrame(rows)
        df["L_Share_%"] = (df["L_coeff"] / df["L_coeff"].sum() * 100).round(2)
        return df.sort_values("L_coeff", ascending=False).reset_index(drop=True)

    # ── Full MRIO report ──────────────────────────────────────────────────────

    def full_report(self) -> Dict[str, pd.DataFrame]:
        """
        Run all MRIO analyses and return results as a dict of DataFrames.
        """
        detail_va, summary_va = self.value_added_decomposition()
        shock_region, shock_sector = self.china_shock_summary(shock_fraction=0.50)

        return {
            "regional_shares":     self.regional_shares_table(),
            "va_detail":           detail_va,
            "va_summary":          summary_va,
            "backward_linkages":   self.backward_linkages(),
            "forward_linkages":    self.forward_linkages(),
            "linkage_summary":     self.linkage_summary(),
            "china_exposure":      self.effective_china_exposure(),
            "china_shock_region":  shock_region,
            "china_shock_sector":  shock_sector,
            "leontief_decomp":     self.leontief_decomposition(),
        }
