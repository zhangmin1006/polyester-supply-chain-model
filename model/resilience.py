"""
resilience.py
Supply chain resilience metrics for the polyester textile supply chain.

Metrics implemented:
  1. Herfindahl-Hirschman Index (HHI)     — supplier concentration
  2. Supply Chain Vulnerability Index     — composite geographic risk
  3. Recovery Time                        — weeks to return to 95 % baseline
  4. Total Shortage Volume                — area under shortage curve (£bn)
  5. Rapidity                             — speed of loss of performance
  6. Robustness                           — fraction of performance retained at shock nadir
  7. Redundancy                           — spare supplier capacity available
  8. Resourcefulness                      — ability to reroute (Armington elasticity)
  9. Resilience Triangle Area             — visual metric (Bruneau et al., 2003)
 10. Effective China Dependency Score     — captures upstream concentration

All monetary values in £bn. Quantities normalised to baseline = 1.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from real_data import (
    SECTORS, N_SECTORS, STAGE_GEOGRAPHY, ARMINGTON_ELASTICITY,
    EFFECTIVE_CHINA_DEPENDENCY, SAFETY_STOCK_WEEKS, UK_INDUSTRY,
    UK_IMPORTS_TOTAL_GBP,
)


# ── 1. Herfindahl-Hirschman Index ─────────────────────────────────────────────

def herfindahl_index(sector: str) -> float:
    """HHI = Σ s_i² ∈ [0, 1]. >0.25 = highly concentrated."""
    geo = STAGE_GEOGRAPHY.get(sector, {"Other": 1.0})
    shares = np.array(list(geo.values()))
    return float((shares ** 2).sum())


def hhi_all_sectors() -> pd.DataFrame:
    rows = []
    for s in SECTORS:
        hhi   = herfindahl_index(s)
        geo   = STAGE_GEOGRAPHY.get(s, {})
        china = geo.get("China", 0.0)
        n_sup = len(geo)
        rows.append({
            "Sector":           s,
            "HHI":              round(hhi, 4),
            "HHI_Category":     "High (>0.25)" if hhi > 0.25
                                else ("Medium (0.15-0.25)" if hhi > 0.15 else "Low (<0.15)"),
            "N_Suppliers":      n_sup,
            "China_Share_%":    round(china * 100, 1),
            "Top_Supplier":     max(geo, key=geo.get) if geo else "N/A",
            "Top_Share_%":      round(max(geo.values()) * 100, 1) if geo else 0,
        })
    df = pd.DataFrame(rows)
    return df


# ── 2. Supply Chain Vulnerability Index (SCVI) ────────────────────────────────

def scvi(sector: str) -> float:
    """
    SCVI = HHI × China_share × (1 / Armington_σ) × (1 / Safety_stock_weeks)

    Captures: concentration × geographic lock-in × inelasticity × buffer weakness.
    """
    hhi   = herfindahl_index(sector)
    geo   = STAGE_GEOGRAPHY.get(sector, {})
    china = geo.get("China", 0.0)
    sigma = ARMINGTON_ELASTICITY.get(sector, 2.0)
    ss    = SAFETY_STOCK_WEEKS.get(sector, 4.0)
    return hhi * china * (1 / sigma) * (1 / ss)


def scvi_all_sectors() -> pd.DataFrame:
    rows = []
    for s in SECTORS:
        v = scvi(s)
        rows.append({
            "Sector":        s,
            "SCVI":          round(v, 5),
            "HHI":           round(herfindahl_index(s), 4),
            "China_Share_%": round(STAGE_GEOGRAPHY.get(s, {}).get("China", 0) * 100, 1),
            "Armington_σ":   ARMINGTON_ELASTICITY.get(s, 2.0),
            "SafetyStock_wk": SAFETY_STOCK_WEEKS.get(s, 4.0),
            "Risk_Level":    "Critical" if v > 0.020 else
                             ("High"     if v > 0.010 else
                              ("Medium"  if v > 0.003 else "Low")),
        })
    df = pd.DataFrame(rows).sort_values("SCVI", ascending=False).reset_index(drop=True)
    return df


# ── 3. Resilience Triangle (Bruneau et al., 2003) ─────────────────────────────

def resilience_triangle(output_series: np.ndarray,
                         baseline: float) -> Dict:
    """
    Compute the resilience triangle metrics from a time series of sector output.

    output_series : 1-D array of output values over time (weeks)
    baseline      : pre-shock baseline output

    Returns
    -------
    robustness  : fraction of baseline at nadir (lowest point)
    rapidity    : speed of initial decline (units/week)
    recovery_t  : time to recover to 95 % baseline (weeks)
    triangle_area: area of loss (∫ [baseline - output] dt) / baseline
    resilience_R: 1 - triangle_area / T  (Bruneau resilience score)
    """
    T   = len(output_series)
    loss = np.maximum(0, baseline - output_series) / (baseline + 1e-12)

    nadir_idx = int(np.argmin(output_series))
    nadir_val = float(output_series[nadir_idx])
    robustness = nadir_val / (baseline + 1e-12)

    # Rapidity: average loss rate over the first 4 weeks after shock
    rapidity = float(loss[:nadir_idx + 1].mean()) if nadir_idx > 0 else 0.0

    # Recovery time: first t > nadir_idx where output ≥ 0.95 * baseline
    post_nadir = output_series[nadir_idx:]
    recovered  = np.where(post_nadir >= 0.95 * baseline)[0]
    recovery_t = int(nadir_idx + recovered[0]) if len(recovered) > 0 else T

    # Triangle area (normalised)
    triangle_area = float(loss.sum()) / T

    # Bruneau R score: 1 = perfect resilience, 0 = never recovers
    resilience_R = 1.0 - triangle_area

    return {
        "robustness":     round(robustness,     4),
        "rapidity":       round(rapidity,       4),
        "recovery_weeks": recovery_t,
        "triangle_area":  round(triangle_area,  4),
        "resilience_R":   round(resilience_R,   4),
    }


def resilience_all_sectors(io_results: Dict, baseline_output: np.ndarray) -> pd.DataFrame:
    """
    Compute resilience triangle metrics for all sectors from IO simulation output.
    """
    rows = []
    output_arr = io_results["output"]   # shape (T, N_SECTORS)
    for j, s in enumerate(SECTORS):
        series = output_arr[:, j]
        b = baseline_output[j]
        rt = resilience_triangle(series, b)
        rows.append({"Sector": s, **rt})
    return pd.DataFrame(rows)


# ── 4. Redundancy Index ───────────────────────────────────────────────────────

def redundancy_index(sector: str) -> float:
    """
    Fraction of global capacity NOT held by the top supplier.
    Higher = more redundant = more resilient.
    """
    geo = STAGE_GEOGRAPHY.get(sector, {"Other": 1.0})
    if not geo:
        return 0.0
    top_share = max(geo.values())
    return round(1.0 - top_share, 4)


# ── 5. Effective China Dependency ─────────────────────────────────────────────

def effective_china_dependency_table() -> pd.DataFrame:
    """
    Nominal vs effective China dependency at each stage.
    The gap reveals how apparent supplier diversity collapses upstream.
    """
    rows = []
    for s in SECTORS:
        nominal  = STAGE_GEOGRAPHY.get(s, {}).get("China", 0.0)
        effective = EFFECTIVE_CHINA_DEPENDENCY.get(s, nominal)
        rows.append({
            "Sector":               s,
            "Nominal_China_%":      round(nominal  * 100, 1),
            "Effective_China_%":    round(effective * 100, 1),
            "Hidden_Dependency_%":  round((effective - nominal) * 100, 1),
        })
    return pd.DataFrame(rows)


# ── 6. Comprehensive Resilience Scorecard ────────────────────────────────────

def resilience_scorecard(io_results: Optional[Dict] = None,
                          baseline_output: Optional[np.ndarray] = None) -> pd.DataFrame:
    """
    Full scorecard combining all resilience dimensions per sector.
    Scores normalised to [0, 1] where 1 = most resilient.
    """
    hhi_df  = hhi_all_sectors()
    scvi_df = scvi_all_sectors().set_index("Sector")

    rows = []
    for s in SECTORS:
        hhi   = herfindahl_index(s)
        red   = redundancy_index(s)
        sig   = ARMINGTON_ELASTICITY.get(s, 2.0)
        ss    = SAFETY_STOCK_WEEKS.get(s, 4.0)
        china = EFFECTIVE_CHINA_DEPENDENCY.get(s, 0.0)

        # Score each dimension [0, 1], then average
        hhi_score   = max(0, 1 - hhi / 0.5)            # lower HHI = better
        red_score   = red                                # higher = better
        sub_score   = min(1, sig / 5.0)                 # higher elasticity = better
        buffer_score = min(1, ss / 12.0)                # more buffer = better
        china_score  = max(0, 1 - china)                # lower dependency = better

        composite = np.mean([hhi_score, red_score, sub_score,
                             buffer_score, china_score])

        rows.append({
            "Sector":              s,
            "HHI_Score":           round(hhi_score,    3),
            "Redundancy_Score":    round(red_score,     3),
            "Substitution_Score":  round(sub_score,     3),
            "Buffer_Score":        round(buffer_score,  3),
            "China_Dep_Score":     round(china_score,   3),
            "Composite_Resilience": round(composite,   3),
            "Resilience_Grade":    "A" if composite > 0.75 else
                                   ("B" if composite > 0.60 else
                                    ("C" if composite > 0.45 else
                                     ("D" if composite > 0.30 else "F"))),
        })

    df = pd.DataFrame(rows).sort_values("Composite_Resilience").reset_index(drop=True)
    return df


# ── 7. System-wide metrics ────────────────────────────────────────────────────

def shortage_value_gbp(shortage_series: np.ndarray,
                        sector_idx: int) -> float:
    """
    Convert normalised shortage to £ value at UK retail scale.
    shortage_series : 1-D time series of normalised shortage values
    """
    uk_retail = UK_INDUSTRY["retail"]["turnover_gbp"]
    polyester_share = 0.57 * 0.40   # 57% polyester of textiles, ~40% synthetic apparel
    sector_retail_fraction = [0.03, 0.06, 0.09, 0.13, 0.24, 0.42, 0.58, 1.00][sector_idx]
    return shortage_series.sum() * uk_retail * polyester_share * sector_retail_fraction


def system_resilience_summary(scenario_results: Dict[str, Dict]) -> pd.DataFrame:
    """
    Cross-scenario comparison table.
    scenario_results: {scenario_name: {'io': io_result, 'abm': abm_result}}
    """
    rows = []
    for sc_name, res in scenario_results.items():
        io_r  = res.get("io")
        abm_r = res.get("abm")

        if io_r is not None:
            total_shortage = io_r["shortage"].sum()
            peak_shortage  = io_r["shortage"].max()
            sectors_hit    = (io_r["shortage"].sum(axis=0) > 0).sum()
        else:
            total_shortage = peak_shortage = sectors_hit = np.nan

        if abm_r is not None:
            abm_shortage = abm_r["shortage"].sum()
            # price amplification: max price increase across sectors
            price_amp = (abm_r["prices"].max() - 1.0) * 100
        else:
            abm_shortage = price_amp = np.nan

        rows.append({
            "Scenario":             sc_name,
            "IO_Total_Shortage":    round(total_shortage, 4) if not np.isnan(total_shortage) else None,
            "IO_Peak_Shortage":     round(peak_shortage,  4) if not np.isnan(peak_shortage)  else None,
            "IO_Sectors_Affected":  int(sectors_hit)         if not np.isnan(sectors_hit)    else None,
            "ABM_Total_Shortage":   round(abm_shortage,   4) if not np.isnan(abm_shortage)   else None,
            "Price_Amp_%":          round(price_amp,       2) if not np.isnan(price_amp)      else None,
        })
    return pd.DataFrame(rows)
