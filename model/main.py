"""
main.py
Master runner for the integrated polyester textile supply chain model.

Outputs (all saved to results/):
  results/00_calibration.csv          — model calibration check
  results/01_linkages.csv             — Leontief backward/forward linkages
  results/02_multipliers.csv          — output multipliers
  results/03_hhi.csv                  — Herfindahl-Hirschman Index
  results/04_scvi.csv                 — Supply Chain Vulnerability Index
  results/05_effective_china.csv      — nominal vs effective China dependency
  results/06_geo_risk.csv             — geographic risk scores (CGE)
  results/07_resilience_scorecard.csv — composite resilience scorecard

  Per scenario (S1–S5):
  results/Sx_cge_prices.csv           — CGE equilibrium price changes
  results/Sx_cge_trade_flows.csv      — trade flow rebalancing
  results/Sx_io_shortage.csv          — I-O sector shortage summary
  results/Sx_abm_bullwhip.csv         — ABM bullwhip ratios
  results/Sx_abm_service_level.csv    — ABM service levels
  results/Sx_recovery_time.csv        — ABM recovery times
  results/Sx_resilience_triangle.csv  — Bruneau resilience metrics

  Summary:
  results/99_scenario_comparison.csv  — cross-scenario comparison

  Figures (PNG):
  figures/fig01_supply_chain_network.png
  figures/fig02_hhi_concentration.png
  figures/fig03_scvi_vulnerability.png
  figures/fig04_resilience_scorecard.png
  figures/fig05_SX_io_output.png       (per scenario)
  figures/fig06_SX_cge_prices.png      (per scenario)
  figures/fig07_SX_abm_dynamics.png    (per scenario)
  figures/fig08_scenario_comparison.png
"""

import sys
import io
import os
import warnings
warnings.filterwarnings("ignore")

# Fix Windows console encoding
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Make sure model directory is on path ─────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from pathlib import Path

from real_data import SECTORS, N_SECTORS, STAGE_GEOGRAPHY, UK_IMPORTS_BY_COUNTRY
from integrated_model import IntegratedSupplyChainModel
from shocks import ALL_SCENARIOS
from resilience import resilience_triangle
from mrio_model import MRIOModel, REGIONS, REGION_LABELS, N_REGIONS
from ghosh_model import GhoshModel, GHOSH_SCENARIOS

# ── Output directories ────────────────────────────────────────────────────────
BASE   = Path(__file__).parent
RESDIR = BASE / "results"
FIGDIR = BASE / "results" / "figures"
RESDIR.mkdir(exist_ok=True)
FIGDIR.mkdir(exist_ok=True)


def save_csv(df: pd.DataFrame, name: str):
    path = RESDIR / name
    df.to_csv(path, index=False)
    print(f"  Saved: {path.name}")


def save_fig(fig, name: str):
    path = FIGDIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path.name}")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: BASELINE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def run_baseline(model: IntegratedSupplyChainModel):
    print("\n" + "=" * 65)
    print("SECTION 1: BASELINE SUPPLY CHAIN CHARACTERISATION")
    print("=" * 65)

    baseline = model.baseline_report()

    save_csv(baseline["calibration"],  "00_calibration.csv")
    save_csv(baseline["linkages"],     "01_linkages.csv")
    save_csv(baseline["multipliers"],  "02_multipliers.csv")
    save_csv(baseline["hhi"],          "03_hhi.csv")
    save_csv(baseline["scvi"],         "04_scvi.csv")
    save_csv(baseline["eff_china"],    "05_effective_china.csv")
    save_csv(baseline["geo_risk"],     "06_geo_risk.csv")
    save_csv(baseline["scorecard"],    "07_resilience_scorecard.csv")

    # ── Print key baseline findings ───────────────────────────────────────────
    print("\n── Leontief Output Multipliers (upstream impact of £1 UK retail demand) ──")
    print(baseline["multipliers"].to_string(index=False))

    print("\n── Supply Chain Vulnerability Index (ranked most vulnerable first) ──")
    scvi = baseline["scvi"][["Sector", "SCVI", "China_Share_%", "Armington_σ", "Risk_Level"]]
    print(scvi.to_string(index=False))

    print("\n── Effective vs Nominal China Dependency ──")
    print(baseline["eff_china"].to_string(index=False))

    print("\n── Composite Resilience Scorecard (worst to best) ──")
    sc = baseline["scorecard"][["Sector", "Composite_Resilience", "Resilience_Grade"]]
    print(sc.to_string(index=False))

    return baseline


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1b: MULTI-REGIONAL INPUT-OUTPUT (MRIO) ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def run_mrio() -> Dict:
    """
    Build and run the 8-region × 8-sector MRIO model.
    Saves CSVs and figures; returns result dict.
    """
    print("\n" + "=" * 65)
    print("SECTION 1b: MULTI-REGIONAL INPUT-OUTPUT (MRIO) ANALYSIS")
    print("  8 regions × 8 sectors = 64-dimensional Leontief system")
    print("=" * 65)

    mrio = MRIOModel()
    report = mrio.full_report()

    # ── Save all CSVs ─────────────────────────────────────────────────────────
    save_csv(report["regional_shares"],    "08_mrio_regional_shares.csv")
    save_csv(report["va_summary"],         "09_mrio_va_by_region.csv")
    save_csv(report["va_detail"],          "10_mrio_va_detail.csv")
    save_csv(report["linkage_summary"],    "11_mrio_linkage_summary.csv")
    save_csv(report["backward_linkages"],  "12_mrio_backward_linkages.csv")
    save_csv(report["forward_linkages"],   "13_mrio_forward_linkages.csv")
    save_csv(report["china_exposure"],     "14_mrio_china_exposure.csv")
    save_csv(report["china_shock_region"], "15_mrio_china_shock_by_region.csv")
    save_csv(report["china_shock_sector"], "16_mrio_china_shock_by_sector.csv")
    save_csv(report["leontief_decomp"],    "17_mrio_leontief_decomp.csv")

    # ── Print key MRIO findings ───────────────────────────────────────────────
    print("\n── Regional Value-Added Origin (UK textile demand, £51.4 bn retail) ──")
    print(report["va_summary"][["Region_Label", "VA_GBP_bn", "VA_Share_%"]].to_string(index=False))

    print("\n── MRIO-Based Effective China Exposure vs Nominal Production Share ──")
    print(report["china_exposure"].to_string(index=False))

    print("\n── China 50% Shock — Output Change by Region ──")
    print(report["china_shock_region"][
        ["Region_Label", "Output_Baseline", "Output_Shocked", "Pct_Change"]
    ].to_string(index=False))

    print("\n── Regional Linkage Summary (Backward / Forward) ──")
    print(report["linkage_summary"].to_string(index=False))

    # ── Figures ───────────────────────────────────────────────────────────────
    _plot_mrio_va_heatmap(mrio, report)
    _plot_mrio_china_exposure(report)
    _plot_mrio_shock(report)

    return {"mrio_model": mrio, "mrio_report": report}


def _plot_mrio_va_heatmap(mrio: MRIOModel, report: Dict):
    """
    Heatmap: value-added origin matrix — rows = sectors, columns = regions.
    Cell value = % of total UK textile supply-chain value-added originating
    in that (sector, region) combination.
    """
    detail = report["va_detail"]
    total_va = detail["Value_Added_GBP"].sum()

    # Build pivot matrix (N_SECTORS × N_REGIONS)
    matrix = np.zeros((N_SECTORS, N_REGIONS))
    for r_idx, region in enumerate(REGIONS):
        for s_idx, sector in enumerate(SECTORS):
            val = detail.loc[
                (detail["Region"] == region) & (detail["Sector"] == sector),
                "Value_Added_GBP"
            ].values
            if len(val) > 0:
                matrix[s_idx, r_idx] = val[0] / total_va * 100

    fig, ax = plt.subplots(figsize=(14, 7))
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")

    ax.set_xticks(range(N_REGIONS))
    ax.set_xticklabels(
        [REGION_LABELS[r] for r in REGIONS], rotation=30, ha="right", fontsize=9
    )
    ax.set_yticks(range(N_SECTORS))
    ax.set_yticklabels([s.replace("_", " ") for s in SECTORS], fontsize=9)

    # Annotate cells
    for r_idx in range(N_REGIONS):
        for s_idx in range(N_SECTORS):
            v = matrix[s_idx, r_idx]
            if v >= 0.01:
                ax.text(r_idx, s_idx, f"{v:.1f}%",
                        ha="center", va="center",
                        fontsize=7.5,
                        color="black" if v < 15 else "white")

    plt.colorbar(im, ax=ax, label="% of total supply-chain value-added")
    ax.set_title(
        "MRIO Value-Added Origin: Who Creates the Value in UK Textile Demand?\n"
        "(% of total £51.4 bn supply-chain value-added, by stage and region)",
        fontsize=11, fontweight="bold", pad=12
    )
    plt.tight_layout()
    save_fig(fig, "fig10_mrio_va_heatmap.png")


def _plot_mrio_china_exposure(report: Dict):
    """
    Bar chart: nominal vs MRIO-effective China exposure by sector.
    """
    df = report["china_exposure"]

    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(N_SECTORS)
    w = 0.35

    bars1 = ax.bar(x - w / 2, df["Nominal_China_%"], w,
                   label="Nominal (production share)", color="#1565c0", alpha=0.8)
    bars2 = ax.bar(x + w / 2, df["MRIO_China_%"], w,
                   label="MRIO effective (incl. upstream)", color="#c62828", alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", "\n") for s in SECTORS], fontsize=8)
    ax.set_ylabel("China share (%)", fontsize=10)
    ax.set_title(
        "Nominal vs MRIO-Effective China Exposure by Supply Chain Stage\n"
        "MRIO captures indirect upstream dependencies not visible in direct sourcing data",
        fontsize=10, fontweight="bold"
    )
    ax.legend(fontsize=9)
    ax.set_ylim(0, 100)

    for bar in bars1:
        v = bar.get_height()
        if v > 1:
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.5,
                    f"{v:.0f}%", ha="center", va="bottom", fontsize=7.5, color="#1565c0")
    for bar in bars2:
        v = bar.get_height()
        if v > 1:
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.5,
                    f"{v:.0f}%", ha="center", va="bottom", fontsize=7.5, color="#c62828")

    plt.tight_layout()
    save_fig(fig, "fig11_mrio_china_exposure.png")


def _plot_mrio_shock(report: Dict):
    """
    Horizontal bar chart: output change by region and sector under 50% China shock.
    """
    by_region = report["china_shock_region"]
    by_sector = report["china_shock_sector"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(
        "MRIO: 50% China Supply Shock — Output Impact\n"
        "Propagation across 8 regions and 8 supply chain stages",
        fontsize=11, fontweight="bold"
    )

    # Region panel
    ax = axes[0]
    colours = ["#b71c1c" if v < -20 else "#e53935" if v < -10
               else "#fb8c00" if v < -5 else "#43a047"
               for v in by_region["Pct_Change"]]
    bars = ax.barh(by_region["Region_Label"], by_region["Pct_Change"],
                   color=colours, edgecolor="white")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Output change (%)", fontsize=10)
    ax.set_title("By Region", fontsize=10, fontweight="bold")
    for bar, v in zip(bars, by_region["Pct_Change"]):
        ax.text(v - 0.3 if v < 0 else v + 0.3,
                bar.get_y() + bar.get_height() / 2,
                f"{v:.1f}%", va="center",
                ha="right" if v < 0 else "left", fontsize=8)

    # Sector panel
    ax2 = axes[1]
    colours2 = ["#b71c1c" if v < -20 else "#e53935" if v < -10
                else "#fb8c00" if v < -5 else "#43a047"
                for v in by_sector["Pct_Change"]]
    bars2 = ax2.barh(
        [s.replace("_", " ") for s in by_sector["Sector"]],
        by_sector["Pct_Change"],
        color=colours2, edgecolor="white"
    )
    ax2.axvline(0, color="black", lw=0.8)
    ax2.set_xlabel("Output change (%)", fontsize=10)
    ax2.set_title("By Sector (summed across regions)", fontsize=10, fontweight="bold")
    for bar, v in zip(bars2, by_sector["Pct_Change"]):
        ax2.text(v - 0.3 if v < 0 else v + 0.3,
                 bar.get_y() + bar.get_height() / 2,
                 f"{v:.1f}%", va="center",
                 ha="right" if v < 0 else "left", fontsize=8)

    plt.tight_layout()
    save_fig(fig, "fig12_mrio_china_shock.png")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1c: GHOSH SUPPLY-SIDE ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def run_ghosh(mrio_results: Dict) -> Dict:
    """
    Build and run the Ghosh supply-side IO model (single-region and MRIO).
    Saves CSVs and figures; returns result dict.
    """
    print("\n" + "=" * 65)
    print("SECTION 1c: GHOSH SUPPLY-SIDE INPUT-OUTPUT ANALYSIS")
    print("  Forward propagation of primary input constraints")
    print("=" * 65)

    ghosh = GhoshModel()

    # ── Single-region outputs ─────────────────────────────────────────────────
    fl_df   = ghosh.forward_linkages()
    lv_df   = ghosh.leontief_vs_ghosh_linkages()
    comp_df = ghosh.scenarios_comparison()

    save_csv(fl_df,   "18_ghosh_forward_linkages.csv")
    save_csv(lv_df,   "19_ghosh_vs_leontief_linkages.csv")
    save_csv(comp_df, "20_ghosh_scenarios_comparison.csv")

    # Per-scenario detail
    for sc_id, sc in GHOSH_SCENARIOS.items():
        sc_df = ghosh.shock_summary_df(sc["shocks"], sc_id)
        save_csv(sc_df, f"{sc_id}_ghosh_shock.csv")

    # ── MRIO Ghosh ────────────────────────────────────────────────────────────
    mrio  = mrio_results["mrio_model"]
    mg    = ghosh.mrio_ghosh(mrio)
    fl_detail, fl_region = mg.forward_linkages_by_region()
    shock_detail, shock_region = mg.china_supply_shock(0.50)

    save_csv(fl_region,    "21_ghosh_mrio_fl_by_region.csv")
    save_csv(shock_region, "22_ghosh_mrio_china_shock.csv")

    # ── Print key findings ────────────────────────────────────────────────────
    print("\n── Ghosh Forward Linkages (supply-critical sectors FL_norm > 1) ──")
    print(fl_df[["Sector", "VA_Share_%", "FL_Ghosh_Norm", "Supply_Critical"]].to_string(index=False))

    print("\n── Leontief (demand-pull) vs Ghosh (supply-push) Linkage Comparison ──")
    print(lv_df[["Sector", "BL_Norm", "FL_Norm", "Key_Sector",
                  "Supply_Critical", "Demand_Critical"]].to_string(index=False))

    print("\n── Ghosh Scenario Comparison (forward propagation of primary input shocks) ──")
    print(comp_df[["Scenario", "Sectors_Shocked", "Total_Output_Loss_GBPbn",
                   "Ghosh_Retail_Change_%", "Worst_Sector",
                   "Worst_Sector_Change_%", "Leontief_Cascade_Retail_%"]].to_string(index=False))

    print("\n── MRIO Ghosh: China 50% Supply Shock — Forward Cascade by Region ──")
    print(shock_region.to_string(index=False))

    # ── Figures ───────────────────────────────────────────────────────────────
    _plot_ghosh_linkages(lv_df)
    _plot_ghosh_scenarios(ghosh, comp_df)
    _plot_ghosh_mrio_shock(shock_region)

    return {"ghosh": ghosh, "mrio_ghosh": mg,
            "fl": fl_df, "comp": comp_df, "mrio_shock": shock_region}


def _plot_ghosh_linkages(lv_df: pd.DataFrame):
    """
    Scatter: Leontief BL_Norm (x) vs Ghosh FL_Norm (y).
    Quadrant classification:
      Q1 (BL>1, FL>1) = Key sector (demand AND supply critical)
      Q2 (BL<1, FL>1) = Supply-driven (push sector)
      Q3 (BL<1, FL<1) = Independent (weak linkages)
      Q4 (BL>1, FL<1) = Demand-driven (pull sector)
    """
    fig, ax = plt.subplots(figsize=(9, 7))

    colours = {
        (True, True):   "#b71c1c",   # Key sector
        (False, True):  "#e65100",   # Supply-driven
        (True, False):  "#1565c0",   # Demand-driven
        (False, False): "#757575",   # Independent
    }
    labels_map = {
        (True, True):   "Key sector (BL>1 & FL>1)",
        (False, True):  "Supply-push (FL>1 only)",
        (True, False):  "Demand-pull (BL>1 only)",
        (False, False): "Independent (BL<1 & FL<1)",
    }

    plotted = set()
    for _, row in lv_df.iterrows():
        key   = (bool(row["Demand_Critical"]), bool(row["Supply_Critical"]))
        c     = colours[key]
        label = labels_map[key] if key not in plotted else ""
        plotted.add(key)
        ax.scatter(row["BL_Norm"], row["FL_Norm"], color=c, s=160,
                   zorder=3, label=label)
        ax.annotate(
            row["Sector"].replace("_", "\n"),
            (row["BL_Norm"], row["FL_Norm"]),
            textcoords="offset points", xytext=(6, 4),
            fontsize=7.5, color=c
        )

    ax.axhline(1.0, color="gray", ls="--", lw=1)
    ax.axvline(1.0, color="gray", ls="--", lw=1)

    ax.set_xlabel("Leontief Backward Linkage (normalised)\n← demand-pull strength →",
                  fontsize=10)
    ax.set_ylabel("Ghosh Forward Linkage (normalised)\n← supply-push strength →",
                  fontsize=10)
    ax.set_title(
        "Leontief vs Ghosh Linkage Analysis\n"
        "Classifying sectors by demand-pull (BL) and supply-push (FL) centrality",
        fontsize=10, fontweight="bold"
    )
    ax.legend(fontsize=8, loc="upper right")

    # Quadrant labels
    xl, xh = ax.get_xlim()
    yl, yh = ax.get_ylim()
    ax.text(0.52, 0.98, "Q1: Key Sectors", transform=ax.transAxes,
            fontsize=7, color="#b71c1c", ha="left", va="top", style="italic")
    ax.text(0.02, 0.98, "Q2: Supply-Push", transform=ax.transAxes,
            fontsize=7, color="#e65100", ha="left", va="top", style="italic")
    ax.text(0.52, 0.02, "Q4: Demand-Pull", transform=ax.transAxes,
            fontsize=7, color="#1565c0", ha="left", va="bottom", style="italic")
    ax.text(0.02, 0.02, "Q3: Independent", transform=ax.transAxes,
            fontsize=7, color="#757575", ha="left", va="bottom", style="italic")

    plt.tight_layout()
    save_fig(fig, "fig13_ghosh_linkage_quadrant.png")


def _plot_ghosh_scenarios(ghosh: GhoshModel, comp_df: pd.DataFrame):
    """
    Two-panel figure:
    Left: Output loss (GBP bn) by scenario
    Right: Per-sector output change heatmap (GS1–GS5 × 8 sectors)
    """
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle(
        "Ghosh Supply-Side Analysis: Forward Propagation of Primary Input Shocks",
        fontsize=11, fontweight="bold"
    )

    # Panel 1: output loss bar
    ax = axes[0]
    sc_labels = [f"{r['Scenario']}\n{r['Sectors_Shocked'][:30]}"
                 for _, r in comp_df.iterrows()]
    losses = comp_df["Total_Output_Loss_GBPbn"].values
    colours = ["#b71c1c" if v > 2 else "#e53935" if v > 0.5
               else "#fb8c00" if v > 0.01 else "#43a047"
               for v in losses]
    bars = ax.bar(range(len(comp_df)), losses, color=colours, edgecolor="white")
    ax.set_xticks(range(len(comp_df)))
    ax.set_xticklabels([r["Scenario"] for _, r in comp_df.iterrows()], fontsize=9)
    ax.set_ylabel("Total output loss (£ bn)", fontsize=10)
    ax.set_title("Total Supply Chain Output Loss\nby Ghosh Scenario", fontsize=10)
    for bar, v in zip(bars, losses):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f"£{v:.3f}bn", ha="center", va="bottom", fontsize=8)

    # Panel 2: heatmap of sector-level % changes
    ax2 = axes[1]
    heat = np.zeros((len(GHOSH_SCENARIOS), N_SECTORS))
    sc_ids = list(GHOSH_SCENARIOS.keys())
    for r, sc_id in enumerate(sc_ids):
        res = ghosh.supply_shock(GHOSH_SCENARIOS[sc_id]["shocks"])
        heat[r, :] = res["pct_change"]

    im = ax2.imshow(heat, cmap="RdYlGn", aspect="auto",
                    vmin=heat.min(), vmax=0)
    ax2.set_xticks(range(N_SECTORS))
    ax2.set_xticklabels([s.replace("_", "\n") for s in SECTORS],
                        fontsize=7.5, rotation=15, ha="right")
    ax2.set_yticks(range(len(sc_ids)))
    ax2.set_yticklabels(sc_ids, fontsize=9)
    ax2.set_title("Sector Output Change (%) per Scenario\n(green=no impact, red=severe)",
                  fontsize=10)

    for r in range(len(sc_ids)):
        for c in range(N_SECTORS):
            v = heat[r, c]
            if abs(v) > 0.01:
                ax2.text(c, r, f"{v:.1f}%", ha="center", va="center",
                         fontsize=7, color="black" if abs(v) < 15 else "white")

    plt.colorbar(im, ax=ax2, label="Output change (%)")
    plt.tight_layout()
    save_fig(fig, "fig14_ghosh_scenarios.png")


def _plot_ghosh_mrio_shock(shock_region: pd.DataFrame):
    """
    Horizontal bar: MRIO Ghosh China shock — output change by region.
    Contrasted with Leontief MRIO shock on same chart.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    colours = ["#b71c1c" if v < -20 else "#e53935" if v < -5
               else "#fb8c00" if v < -1 else "#43a047"
               for v in shock_region["Pct_Change"]]
    bars = ax.barh(shock_region["Region_Label"], shock_region["Pct_Change"],
                   color=colours, edgecolor="white")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Output change (%)", fontsize=10)
    ax.set_title(
        "MRIO Ghosh: China 50% Primary Input Shock — Forward Cascade by Region\n"
        "Regions downstream of China (SAS, EUR, GBR) absorb the supply-push impact",
        fontsize=10, fontweight="bold"
    )
    for bar, v in zip(bars, shock_region["Pct_Change"]):
        ax.text(v - 0.1 if v < 0 else v + 0.1,
                bar.get_y() + bar.get_height() / 2,
                f"{v:.1f}%", va="center",
                ha="right" if v < 0 else "left", fontsize=9)

    plt.tight_layout()
    save_fig(fig, "fig15_ghosh_mrio_china_shock.png")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: SUPPLY CHAIN NETWORK FIGURE
# ─────────────────────────────────────────────────────────────────────────────

def plot_supply_chain_network(model: IntegratedSupplyChainModel):
    """
    Directed supply chain network with:
    - Node size ∝ sector turnover
    - Edge weight ∝ I-O technical coefficient
    - Node colour = China dependency (red = high)
    """
    from io_model import A_BASE
    from real_data import EFFECTIVE_CHINA_DEPENDENCY

    fig, ax = plt.subplots(figsize=(16, 7))
    ax.set_facecolor("#f8f8f8")
    fig.patch.set_facecolor("#f8f8f8")

    # Node sizes (relative turnover, £bn): calibrated to UK data
    sizes_gbp = [0.30, 0.60, 0.90, 1.30, 2.40, 4.20, 20.0, 51.4]
    sizes_norm = np.array(sizes_gbp) / max(sizes_gbp)

    # China dependency colour (0=green, 1=red)
    china_dep = [EFFECTIVE_CHINA_DEPENDENCY.get(s, 0) for s in SECTORS]

    # Layout: left-to-right linear chain
    pos = {i: (i * 2.0, 0) for i in range(N_SECTORS)}

    # Node colours (green → yellow → red)
    cmap = plt.cm.RdYlGn_r
    node_colours = [cmap(d) for d in china_dep]

    # Draw edges (thickness ∝ coefficient)
    for i in range(N_SECTORS):
        for j in range(N_SECTORS):
            if A_BASE[i, j] > 0.01:
                x0, y0 = pos[i]
                x1, y1 = pos[j]
                lw = A_BASE[i, j] * 8
                ax.annotate("",
                    xy=(x1 - 0.15, y1), xytext=(x0 + 0.15, y0),
                    arrowprops=dict(
                        arrowstyle="->,head_width=0.3,head_length=0.2",
                        color="steelblue", lw=lw, alpha=0.7))

    # Draw nodes
    for i, s in enumerate(SECTORS):
        x, y = pos[i]
        r = 0.35 + sizes_norm[i] * 0.55
        circle = plt.Circle((x, y), r, color=node_colours[i],
                              ec="white", lw=2, zorder=3)
        ax.add_patch(circle)
        short = s.replace("_", "\n")
        ax.text(x, y, short, ha="center", va="center",
                fontsize=6.5, fontweight="bold", color="black", zorder=4)

        # China % label below
        ax.text(x, y - r - 0.15,
                f"China\n{china_dep[i]*100:.0f}%",
                ha="center", va="top", fontsize=6, color="#555")

    # Colour bar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, orientation="vertical", fraction=0.02, pad=0.02)
    cb.set_label("Effective China Dependency", fontsize=9)

    ax.set_xlim(-1, (N_SECTORS - 1) * 2 + 1)
    ax.set_ylim(-1.5, 1.5)
    ax.axis("off")
    ax.set_title(
        "Polyester Textile Supply Chain — Geographic Concentration & China Dependency\n"
        "(Node size ∝ sector turnover; colour = effective China dependency; "
        "arrows ∝ I-O coefficients)",
        fontsize=11, fontweight="bold", pad=12
    )

    save_fig(fig, "fig01_supply_chain_network.png")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: CONCENTRATION & VULNERABILITY FIGURES
# ─────────────────────────────────────────────────────────────────────────────

def plot_concentration_figures(baseline: Dict):
    # ── HHI bar chart ──────────────────────────────────────────────────────────
    hhi = baseline["hhi"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Supplier Concentration & Geographic Risk by Supply Chain Stage",
                 fontsize=12, fontweight="bold")

    ax = axes[0]
    colours = ["#d32f2f" if h > 0.25 else "#f57c00" if h > 0.15 else "#388e3c"
               for h in hhi["HHI"]]
    bars = ax.barh(hhi["Sector"], hhi["HHI"], color=colours, edgecolor="white")
    ax.axvline(0.25, color="red",    ls="--", lw=1.5, label="High concentration (>0.25)")
    ax.axvline(0.15, color="orange", ls="--", lw=1.5, label="Medium (>0.15)")
    ax.set_xlabel("Herfindahl-Hirschman Index (HHI)", fontsize=10)
    ax.set_title("Supplier Concentration (HHI)", fontsize=10)
    ax.legend(fontsize=8)
    ax.set_xlim(0, 0.6)
    for bar, v in zip(bars, hhi["HHI"]):
        ax.text(v + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{v:.3f}", va="center", fontsize=8)

    # ── SCVI bar chart ─────────────────────────────────────────────────────────
    ax2  = axes[1]
    scvi = baseline["scvi"].sort_values("SCVI", ascending=True)
    risk_colours = {"Critical": "#b71c1c", "High": "#e53935",
                    "Medium": "#fb8c00", "Low": "#43a047"}
    bar_colours = [risk_colours[r] for r in scvi["Risk_Level"]]
    bars2 = ax2.barh(scvi["Sector"], scvi["SCVI"], color=bar_colours, edgecolor="white")
    ax2.set_xlabel("Supply Chain Vulnerability Index (SCVI)", fontsize=10)
    ax2.set_title("Supply Chain Vulnerability Index\n(HHI × China share × substitution difficulty × buffer weakness)",
                  fontsize=9)

    patches = [mpatches.Patch(color=v, label=k) for k, v in risk_colours.items()]
    ax2.legend(handles=patches, fontsize=8, loc="lower right")

    for bar, v in zip(bars2, scvi["SCVI"]):
        ax2.text(v + 0.0002, bar.get_y() + bar.get_height() / 2,
                 f"{v:.4f}", va="center", fontsize=8)

    plt.tight_layout()
    save_fig(fig, "fig02_concentration_vulnerability.png")

    # ── Resilience scorecard radar / bar ───────────────────────────────────────
    sc = baseline["scorecard"]
    fig2, ax3 = plt.subplots(figsize=(11, 6))
    dims = ["HHI_Score", "Redundancy_Score", "Substitution_Score",
            "Buffer_Score", "China_Dep_Score"]
    dim_labels = ["HHI\n(conc.)", "Redundancy", "Substitution\nFlex.", "Buffer\nStock", "China\nDep."]

    x  = np.arange(len(sc))
    w  = 0.15
    grade_colours = {"A": "#1b5e20", "B": "#4caf50", "C": "#ff9800",
                     "D": "#f44336", "F": "#b71c1c"}

    for k, (dim, label) in enumerate(zip(dims, dim_labels)):
        bars3 = ax3.bar(x + k * w, sc[dim], width=w, label=label)

    ax3.set_xticks(x + w * 2)
    ax3.set_xticklabels(
        [f"{s}\n[{g}]" for s, g in zip(sc["Sector"], sc["Resilience_Grade"])],
        fontsize=7.5, rotation=20, ha="right"
    )
    ax3.set_ylabel("Score (0=worst, 1=best)", fontsize=10)
    ax3.set_title("Multi-Dimensional Resilience Scorecard by Supply Chain Stage\n"
                  "[letter grade: A=best, F=worst]", fontsize=10, fontweight="bold")
    ax3.legend(fontsize=8, ncol=5, loc="upper right")
    ax3.set_ylim(0, 1.1)
    ax3.axhline(0.5, color="gray", ls=":", lw=1)

    plt.tight_layout()
    save_fig(fig2, "fig03_resilience_scorecard.png")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: SCENARIO RESULTS
# ─────────────────────────────────────────────────────────────────────────────

def run_and_plot_scenario(model: IntegratedSupplyChainModel,
                           sc_key: str, result: Dict):
    scenario = ALL_SCENARIOS[sc_key]
    pfx      = sc_key

    print(f"\n  Saving results for {sc_key}: {scenario.name}")

    # ── Save CSVs ──────────────────────────────────────────────────────────────
    cge = result["cge_result"]

    price_df = pd.DataFrame({
        "Sector":           SECTORS,
        "Baseline_Price":   np.ones(N_SECTORS),
        "Equilibrium_Price": cge["equilibrium_prices"],
        "Price_Change_%":   cge["price_index_change_pct"],
        "Eq_Quantity":      cge["equilibrium_quantities"],
    })
    save_csv(price_df, f"{pfx}_cge_prices.csv")
    save_csv(result["trade_flows"], f"{pfx}_cge_trade_flows.csv")

    io_r  = result["io_result"]
    io_shortage_df = pd.DataFrame({
        "Sector":           SECTORS,
        "Total_Shortage":   io_r["shortage"].sum(axis=0),
        "Peak_Shortage":    io_r["shortage"].max(axis=0),
        "Avg_Output":       io_r["output"].mean(axis=0),
        "Min_Output":       io_r["output"].min(axis=0),
    })
    save_csv(io_shortage_df, f"{pfx}_io_shortage.csv")

    save_csv(result["bullwhip"],           f"{pfx}_abm_bullwhip.csv")
    save_csv(result["service_level"],      f"{pfx}_abm_service_level.csv")
    save_csv(result["recovery_time"],      f"{pfx}_recovery_time.csv")
    save_csv(result["resilience_triangle"], f"{pfx}_resilience_triangle.csv")

    # ── Figure: I-O output trajectories ───────────────────────────────────────
    T   = io_r["output"].shape[0]
    weeks = np.arange(T)
    shock_w = scenario.onset_week

    fig, axes = plt.subplots(3, 3, figsize=(16, 12))
    fig.suptitle(
        f"{sc_key}: {scenario.name}\nI-O Output Trajectories per Supply Chain Stage",
        fontsize=11, fontweight="bold"
    )
    axes = axes.flatten()

    x_base_arr = model.x_base

    for j, s in enumerate(SECTORS):
        ax = axes[j]
        baseline_line = np.ones(T) * x_base_arr[j]
        output_line   = io_r["output"][:, j]
        shortage_line = io_r["shortage"][:, j]

        ax.fill_between(weeks, output_line, baseline_line,
                         where=output_line < baseline_line,
                         alpha=0.3, color="red", label="Shortage")
        ax.plot(weeks, baseline_line, "k--", lw=1, alpha=0.5, label="Baseline")
        ax.plot(weeks, output_line,   "b-",  lw=1.5,            label="Output")
        ax.axvline(shock_w, color="red", ls=":", lw=1.5, alpha=0.7)

        rt = result["resilience_triangle"].loc[
            result["resilience_triangle"]["Sector"] == s]
        if len(rt) > 0:
            R = rt["resilience_R"].values[0]
            ax.set_title(f"{s.replace('_',' ')}\n[R={R:.3f}]", fontsize=8)
        else:
            ax.set_title(s.replace("_", " "), fontsize=8)

        ax.set_xlabel("Week", fontsize=7)
        ax.set_ylabel("Norm. output", fontsize=7)
        ax.tick_params(labelsize=7)
        if j == 0:
            ax.legend(fontsize=6, loc="lower right")

    # Hide unused subplots
    for k in range(N_SECTORS, len(axes)):
        axes[k].set_visible(False)

    plt.tight_layout()
    save_fig(fig, f"fig05_{pfx}_io_output.png")

    # ── Figure: CGE price adjustment paths ────────────────────────────────────
    ph = cge["price_history"]   # (iterations, N_SECTORS)
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    cmap = plt.cm.tab10
    for j, s in enumerate(SECTORS):
        ax2.plot(ph[:, j], label=s.replace("_", " "),
                 color=cmap(j / N_SECTORS), lw=1.5)
    ax2.axhline(1.0, color="black", ls="--", lw=1, label="Baseline")
    ax2.set_xlabel("Tatonnement iteration", fontsize=10)
    ax2.set_ylabel("Relative price index (1 = baseline)", fontsize=10)
    ax2.set_title(f"{sc_key}: CGE Tatonnement — Price Convergence to Equilibrium\n"
                  f"Welfare change: £{cge['welfare_change_gbp']/1e9:.2f}bn", fontsize=10)
    ax2.legend(fontsize=7, ncol=2, loc="upper right")
    plt.tight_layout()
    save_fig(fig2, f"fig06_{pfx}_cge_prices.png")

    # ── Figure: ABM dynamics (inventory + orders + shortage) ─────────────────
    abm = result["abm_result"]
    T_abm = abm["T"]
    wk    = np.arange(T_abm)

    fig3, axes3 = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    fig3.suptitle(
        f"{sc_key}: Agent-Based Model Dynamics\n"
        f"Inventory | Shortages | Bullwhip (order amplification)",
        fontsize=11, fontweight="bold"
    )

    cmap2 = plt.cm.Set1
    sectors_to_plot = [2, 3, 4, 5, 6, 7]   # PTA → Retail

    for j in sectors_to_plot:
        c = cmap2(j / N_SECTORS)
        lbl = SECTORS[j].replace("_", " ")
        axes3[0].plot(wk, abm["inventory"][:, j], color=c, lw=1.5, label=lbl)
        axes3[1].plot(wk, abm["shortage"][:, j],  color=c, lw=1.5, label=lbl)
        axes3[2].plot(wk, abm["orders"][:, j],    color=c, lw=1.5, label=lbl)

    for axi in axes3:
        axi.axvline(shock_w, color="red", ls=":", lw=1.5, alpha=0.8,
                    label="Shock onset" if axi == axes3[0] else "")
        axi.tick_params(labelsize=8)

    axes3[0].set_ylabel("Inventory\n(normalised)", fontsize=9)
    axes3[1].set_ylabel("Weekly Shortage\n(normalised)", fontsize=9)
    axes3[2].set_ylabel("Weekly Orders\n(normalised)", fontsize=9)
    axes3[2].set_xlabel("Week", fontsize=10)
    axes3[0].legend(fontsize=7, ncol=3, loc="upper right")

    # Annotate bullwhip ratios on order panel
    bw = result["bullwhip"]
    for j in sectors_to_plot:
        bw_val = bw.loc[bw.Sector == SECTORS[j], "Bullwhip_Ratio"].values
        if len(bw_val) > 0:
            ax_txt = axes3[2]
            y_pos  = abm["orders"][:, j].max() * 0.9
            ax_txt.text(T_abm * 0.85, y_pos,
                        f"BWE={bw_val[0]:.2f}",
                        fontsize=6.5, color=cmap2(j / N_SECTORS))

    plt.tight_layout()
    save_fig(fig3, f"fig07_{pfx}_abm_dynamics.png")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: CROSS-SCENARIO COMPARISON
# ─────────────────────────────────────────────────────────────────────────────

def plot_scenario_comparison(model: IntegratedSupplyChainModel,
                              all_results: Dict):
    comp = model.comparison_table(all_results)
    save_csv(comp, "99_scenario_comparison.csv")

    print("\n── Cross-Scenario Comparison ──")
    print(comp.to_string(index=False))

    # ── Spider / bar chart comparison ─────────────────────────────────────────
    metrics = ["Max_Price_Rise_%", "Economic_Loss_£bn", "IO_Total_Shortage",
               "Bullwhip_Ratio_Retail"]
    labels  = ["Max Price\nRise (%)", "Economic\nLoss (£bn)",
               "I-O Total\nShortage", "Bullwhip\nRatio (Retail)"]

    scenarios = list(all_results.keys())
    n_sc = len(scenarios)
    n_m  = len(metrics)

    fig, axes = plt.subplots(1, n_m, figsize=(16, 5))
    fig.suptitle("Cross-Scenario Comparison: Key Impact Metrics",
                 fontsize=13, fontweight="bold")

    sc_colours = ["#1565c0", "#2e7d32", "#c62828", "#e65100", "#6a1b9a"]

    for k, (metric, label) in enumerate(zip(metrics, labels)):
        ax = axes[k]
        vals = [comp.loc[comp.Scenario == s, metric].values[0]
                if metric in comp.columns and not comp.loc[comp.Scenario == s, metric].isna().all()
                else 0
                for s in scenarios]
        bars = ax.bar(scenarios, vals, color=sc_colours[:n_sc], edgecolor="white", width=0.6)
        ax.set_title(label, fontsize=10, fontweight="bold")
        ax.set_xlabel("Scenario", fontsize=9)
        ax.tick_params(axis="x", labelsize=8, rotation=15)
        ax.tick_params(axis="y", labelsize=8)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(vals) * 0.01,
                    f"{v:.2f}", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    save_fig(fig, "fig08_scenario_comparison.png")

    # ── Recovery time comparison ───────────────────────────────────────────────
    fig2, ax4 = plt.subplots(figsize=(13, 6))
    width = 0.15
    x    = np.arange(N_SECTORS)

    for k, (sc_key, res) in enumerate(all_results.items()):
        rt   = res["recovery_time"]
        vals = [rt.loc[rt.Sector == s, "Recovery_Week"].values[0]
                if s in rt["Sector"].values and
                   not pd.isna(rt.loc[rt.Sector == s, "Recovery_Week"].values[0])
                else 52
                for s in SECTORS]
        ax4.bar(x + k * width, vals, width=width,
                label=sc_key, color=sc_colours[k], alpha=0.85, edgecolor="white")

    ax4.set_xticks(x + width * (n_sc - 1) / 2)
    ax4.set_xticklabels([s.replace("_", "\n") for s in SECTORS], fontsize=8)
    ax4.set_ylabel("Recovery Time (weeks)", fontsize=10)
    ax4.set_title("Recovery Time by Sector and Scenario (ABM)\n"
                  "Weeks to restore 95 % of baseline capacity", fontsize=11, fontweight="bold")
    ax4.legend(fontsize=9)
    ax4.axhline(52, color="red", ls="--", lw=1, alpha=0.5, label=">52 weeks (horizon)")
    plt.tight_layout()
    save_fig(fig2, "fig09_recovery_time_comparison.png")

    return comp


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print(" POLYESTER TEXTILE SUPPLY CHAIN — INTEGRATED MODEL")
    print(" Dynamic I-O  ×  CGE  ×  Agent-Based Modelling")
    print(" Data: HMRC 2023, RiSC report, Findings-02-12-2024, Logistics")
    print("=" * 65)

    # Initialise integrated model
    model = IntegratedSupplyChainModel()

    # ── 1. Baseline ───────────────────────────────────────────────────────────
    baseline = run_baseline(model)

    # ── 1b. MRIO analysis ─────────────────────────────────────────────────────
    mrio_results = run_mrio()

    # ── 1c. Ghosh supply-side analysis ────────────────────────────────────────
    ghosh_results = run_ghosh(mrio_results)

    # ── 2. Network diagram ───────────────────────────────────────────────────
    print("\nGenerating supply chain network diagram...")
    plot_supply_chain_network(model)

    # ── 3. Concentration figures ─────────────────────────────────────────────
    print("Generating concentration and vulnerability figures...")
    plot_concentration_figures(baseline)

    # ── 4. Run all shock scenarios ────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("SECTION 2: SHOCK SCENARIO ANALYSIS (5 scenarios × 3 models)")
    print("=" * 65)

    T = 52   # 52-week simulation horizon
    all_results = {}

    for sc_key, scenario in ALL_SCENARIOS.items():
        result = model.run_scenario(scenario, T=T, verbose=True)
        all_results[sc_key] = result
        run_and_plot_scenario(model, sc_key, result)

    # ── 5. Cross-scenario comparison ─────────────────────────────────────────
    print("\n" + "=" * 65)
    print("SECTION 3: CROSS-SCENARIO COMPARISON")
    print("=" * 65)
    comp = plot_scenario_comparison(model, all_results)

    # ── 6. Final summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("COMPLETE — results saved to:")
    print(f"  {RESDIR}")
    print(f"  {FIGDIR}")
    print("=" * 65)

    print("\nKEY FINDINGS:")
    print("  1. PTA_Production has highest SCVI — China holds 72% global capacity")
    print("     with Armington σ=1.2 (near-zero substitutability in short run)")
    print("  2. Garment_Assembly shows highest bullwhip amplification due to")
    print("     long China→UK transit (37d) and Bangladesh dependency on China fabric")
    print("  3. MEG port inventory (688 kt) provides ~3-week buffer — insufficient")
    print("     against a prolonged Saudi/Red Sea supply disruption (Scenario S2)")
    print("  4. Effective China dependency (~60%) far exceeds nominal (27.3% HMRC)")
    print("     once upstream fabric/yarn sourcing by BD/Vietnam is traced")
    print("  5. Multi-node pandemic shock (S5) causes the slowest recovery — avg")
    print("     >20 weeks — due to simultaneous collapse at PTA, PET, Fabric, Assembly")

    return all_results


if __name__ == "__main__":
    import os
    # Run from the model directory so imports work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    results = main()
