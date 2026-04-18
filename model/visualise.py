"""
visualise.py
============
Main entry point for the Polyester Textile Supply Chain Model.

Runs the full integrated model (IO × CGE × ABM × MRIO × Ghosh) and generates
every figure. New in this version: HMRC 2002–2024 time-series visualisations
and an improved geographic supply chain diagram.

Usage
-----
  cd model
  python visualise.py

Output
------
  results/figures/
    fig00_supply_chain_geography.png   ← geographic flow diagram (NEW)
    fig01_supply_chain_network.png     ← IO network / China dependency
    fig02_concentration_vulnerability.png
    fig03_resilience_scorecard.png
    fig04_hmrc_import_trends.png       ← HMRC 2002-2024 annual trends (NEW)
    fig05_hmrc_country_breakdown.png   ← per-country value / unit price (NEW)
    fig06_hmrc_seasonal_pattern.png    ← monthly seasonal demand (NEW)
    fig07_hmrc_validation_events.png   ← HMRC benchmarks vs model (NEW)
    fig08_mrio_va_heatmap.png
    fig09_mrio_china_exposure.png
    fig10_mrio_china_shock.png
    fig11_ghosh_linkage_quadrant.png
    fig12_ghosh_scenarios.png
    fig13_ghosh_mrio_shock.png
    fig14_SX_io_output.png             (per scenario S1–S5)
    fig15_SX_cge_prices.png            (per scenario)
    fig16_SX_abm_dynamics.png          (per scenario)
    fig17_scenario_comparison.png
    fig18_recovery_time.png
"""

import sys
import io as _io
import os
import warnings
warnings.filterwarnings("ignore")

# ── Windows console encoding ──────────────────────────────────────────────────
if hasattr(sys.stdout, "buffer"):
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

os.chdir(os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec
import networkx as nx
from pathlib import Path
from typing import Dict

from real_data import (
    SECTORS, N_SECTORS, STAGE_GEOGRAPHY, EFFECTIVE_CHINA_DEPENDENCY,
    UK_IMPORTS_BY_COUNTRY, UK_IMPORTS_TOTAL_GBP,
    HMRC_ANNUAL_TOTALS_GBP, HMRC_ANNUAL_BY_COUNTRY_GBP,
    HMRC_CHINA_UNIT_PRICE_GBP_PER_KG, HMRC_MONTHLY_SEASONAL_FACTORS,
    HMRC_VALIDATION_BENCHMARKS,
)
from io_model import A_BASE
from integrated_model import IntegratedSupplyChainModel
from shocks import ALL_SCENARIOS
from resilience import resilience_triangle
from mrio_model import MRIOModel, REGIONS, REGION_LABELS, N_REGIONS
from ghosh_model import GhoshModel, GHOSH_SCENARIOS

# ── Output directories ────────────────────────────────────────────────────────
BASE   = Path(__file__).parent
RESDIR = BASE / "results"
FIGDIR = RESDIR / "figures"
RESDIR.mkdir(exist_ok=True)
FIGDIR.mkdir(exist_ok=True)

# ── Shared style ──────────────────────────────────────────────────────────────
PALETTE = {
    "china":      "#c62828",
    "sa":         "#1565c0",
    "uk":         "#2e7d32",
    "warn_hi":    "#b71c1c",
    "warn_med":   "#e65100",
    "warn_lo":    "#f9a825",
    "ok":         "#2e7d32",
    "neutral":    "#546e7a",
    "bg":         "#fafafa",
}
SECTOR_COLOURS = [
    "#5c6bc0", "#26a69a", "#ab47bc", "#ef5350",
    "#ff7043", "#8d6e63", "#42a5f5", "#26c6da",
]

def _save(fig: plt.Figure, name: str):
    path = FIGDIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  {path.name}")

def _save_csv(df: pd.DataFrame, name: str):
    df.to_csv(RESDIR / name, index=False)


# =============================================================================
# FIG 00 — GEOGRAPHIC SUPPLY CHAIN DIAGRAM
# =============================================================================

def fig_supply_chain_geography():
    """
    Stylised geographic flow diagram: crude oil → chemicals → fibres → fabric
    → garment → UK wholesale → UK retail, with countries positioned by region.
    Flows coloured by risk level; widths proportional to value flow.
    """
    print("  fig00 — geographic supply chain diagram")

    fig, ax = plt.subplots(figsize=(20, 11))
    fig.patch.set_facecolor("#0d1b2a")
    ax.set_facecolor("#0d1b2a")
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 11)
    ax.axis("off")

    # ── Node definitions: (x, y, label, sublabel, colour, size) ─────────────
    nodes = {
        # stage 0 — Oil
        "oil_sa":   (1.5, 8.5, "Saudi Arabia", "Oil 11.5%",   "#f57c00", 1.1),
        "oil_uae":  (1.5, 7.1, "UAE",           "Oil 4.7%",    "#f57c00", 0.7),
        "oil_iraq": (1.5, 5.8, "Iraq",           "Oil 5.1%",    "#f57c00", 0.7),
        "oil_usa":  (1.5, 4.4, "USA",            "Oil 16.0%",   "#f57c00", 1.2),
        "oil_rus":  (1.5, 3.0, "Russia",         "Oil 11.6%",   "#f57c00", 1.1),

        # stage 1 — Chemicals (MEG + p-Xylene)
        "chem_cn":  (4.5, 8.0, "China",          "Chem 35%",    "#c62828", 1.2),
        "chem_sa":  (4.5, 6.5, "Saudi Arabia",   "Chem 18%",    "#f57c00", 0.9),
        "chem_kr":  (4.5, 5.1, "South Korea",    "Chem 14%",    "#1976d2", 0.8),
        "chem_jp":  (4.5, 3.7, "Japan",          "Chem 10%",    "#1976d2", 0.75),

        # stage 2 — PTA
        "pta_cn":   (7.2, 7.5, "China",          "PTA 67%",     "#c62828", 1.6),
        "pta_in":   (7.2, 5.5, "India",          "PTA 7%",      "#5c8a3c", 0.7),
        "pta_kr":   (7.2, 4.0, "South Korea",    "PTA 6%",      "#1976d2", 0.65),

        # stage 3 — PET Resin/Yarn
        "pet_cn":   (10.0, 7.8, "China",         "PET 60%",     "#c62828", 1.55),
        "pet_in":   (10.0, 6.0, "India",         "PET 13%",     "#5c8a3c", 0.85),
        "pet_kr":   (10.0, 4.5, "S. Korea/TW",  "PET 10%",     "#1976d2", 0.75),

        # stage 4 — Fabric Weaving
        "fab_cn":   (12.8, 8.2, "China",         "Fabric 43%",  "#c62828", 1.5),
        "fab_in":   (12.8, 6.5, "India",         "Fabric 11%",  "#5c8a3c", 0.85),
        "fab_bd":   (12.8, 5.0, "Bangladesh",    "Fabric 5%",   "#5c8a3c", 0.65),
        "fab_tr":   (12.8, 3.5, "Turkey",        "Fabric 5%",   "#7b1fa2", 0.65),

        # stage 5 — Garment Assembly
        "gar_cn":   (15.5, 8.5, "China",         "Garment 27%", "#c62828", 1.2),
        "gar_bd":   (15.5, 7.1, "Bangladesh",    "Garment 12%", "#5c8a3c", 0.9),
        "gar_tr":   (15.5, 5.8, "Turkey",        "Garment 6%",  "#7b1fa2", 0.75),
        "gar_vn":   (15.5, 4.5, "Vietnam",       "Garment 5%",  "#5c8a3c", 0.7),
        "gar_in":   (15.5, 3.2, "India",         "Garment 4%",  "#5c8a3c", 0.65),

        # stage 6 — UK Wholesale
        "who_uk":   (17.8, 7.0, "UK",            "Wholesale\n£20bn",  "#2e7d32", 1.3),

        # stage 7 — UK Retail
        "ret_uk":   (19.5, 6.0, "UK",            "Retail\n£51.4bn",   "#1b5e20", 1.6),
    }

    # ── Stage header bars ────────────────────────────────────────────────────
    stage_info = [
        (1.5, 1.5, "OIL",           "§0"),
        (4.5, 1.5, "CHEMICALS",     "§1"),
        (7.2, 1.5, "PTA",           "§2"),
        (10.0,1.5, "PET/YARN",      "§3"),
        (12.8,1.5, "FABRIC",        "§4"),
        (15.5,1.5, "GARMENT",       "§5"),
        (17.8,1.5, "WHOLESALE",     "§6"),
        (19.5,1.5, "RETAIL",        "§7"),
    ]
    for sx, sy, slabel, snum in stage_info:
        ax.text(sx, sy + 0.4, slabel, ha="center", va="center",
                fontsize=7.5, color="white", fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.25", facecolor="#1e3a5f",
                          edgecolor="#4fc3f7", linewidth=0.8))
        ax.text(sx, sy - 0.05, snum, ha="center", va="center",
                fontsize=6.5, color="#78909c")

    # ── Edges (flows) ────────────────────────────────────────────────────────
    edges = [
        # oil → chemicals
        ("oil_sa",  "chem_sa",  0.8, "#f57c00"),
        ("oil_sa",  "chem_cn",  0.6, "#f57c00"),
        ("oil_usa", "chem_cn",  0.5, "#f57c00"),
        ("oil_rus", "chem_cn",  0.6, "#f57c00"),
        # chemicals → PTA
        ("chem_cn", "pta_cn",   2.5, "#c62828"),
        ("chem_sa", "pta_cn",   0.7, "#f57c00"),
        ("chem_kr", "pta_kr",   0.6, "#1976d2"),
        ("chem_jp", "pta_kr",   0.4, "#1976d2"),
        # PTA → PET
        ("pta_cn",  "pet_cn",   2.5, "#c62828"),
        ("pta_in",  "pet_in",   0.7, "#5c8a3c"),
        ("pta_kr",  "pet_kr",   0.7, "#1976d2"),
        # PET → Fabric
        ("pet_cn",  "fab_cn",   2.2, "#c62828"),
        ("pet_in",  "fab_in",   0.8, "#5c8a3c"),
        ("pet_kr",  "fab_cn",   0.5, "#c62828"),
        # Fabric → Garment (China fabric supplies BD/VN — key indirect link)
        ("fab_cn",  "gar_cn",   1.8, "#c62828"),
        ("fab_cn",  "gar_bd",   1.2, "#c62828"),   # indirect China exposure
        ("fab_cn",  "gar_vn",   0.9, "#c62828"),
        ("fab_bd",  "gar_bd",   0.5, "#5c8a3c"),
        ("fab_in",  "gar_in",   0.6, "#5c8a3c"),
        ("fab_tr",  "gar_tr",   0.7, "#7b1fa2"),
        # Garment → UK Wholesale
        ("gar_cn",  "who_uk",   2.0, "#c62828"),
        ("gar_bd",  "who_uk",   1.2, "#5c8a3c"),
        ("gar_tr",  "who_uk",   0.9, "#7b1fa2"),
        ("gar_vn",  "who_uk",   0.6, "#5c8a3c"),
        ("gar_in",  "who_uk",   0.5, "#5c8a3c"),
        # Wholesale → Retail
        ("who_uk",  "ret_uk",   3.5, "#2e7d32"),
    ]

    for src, dst, w, col in edges:
        x0, y0 = nodes[src][0], nodes[src][1]
        x1, y1 = nodes[dst][0], nodes[dst][1]
        ax.annotate("", xy=(x1 - 0.2, y1), xytext=(x0 + 0.2, y0),
                    arrowprops=dict(
                        arrowstyle="->,head_width=0.2,head_length=0.15",
                        color=col, lw=w * 0.7, alpha=0.55,
                        connectionstyle="arc3,rad=0.08"))

    # ── Nodes ────────────────────────────────────────────────────────────────
    for key, (x, y, label, sublabel, col, size) in nodes.items():
        circle = plt.Circle((x, y), size * 0.38, color=col,
                             ec="white", lw=1.2, zorder=4, alpha=0.92)
        ax.add_patch(circle)
        ax.text(x, y + 0.08, label, ha="center", va="center",
                fontsize=6.2, color="white", fontweight="bold", zorder=5)
        ax.text(x, y - 0.25, sublabel, ha="center", va="center",
                fontsize=5.5, color="#e0e0e0", zorder=5)

    # ── Indirect exposure annotation ─────────────────────────────────────────
    ax.annotate(
        "BD/VN source ~60-70%\nof fabric from China\n→ indirect UK exposure",
        xy=(14.0, 6.3), xytext=(13.2, 9.6),
        fontsize=7, color="#ffcc02", fontweight="bold",
        arrowprops=dict(arrowstyle="->", color="#ffcc02", lw=1.2),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#1e3a5f",
                  edgecolor="#ffcc02", linewidth=1),
    )

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_elements = [
        mpatches.Patch(color="#c62828", label="China-origin / China-dependent"),
        mpatches.Patch(color="#f57c00", label="Middle East origin"),
        mpatches.Patch(color="#5c8a3c", label="South / South-East Asia"),
        mpatches.Patch(color="#1976d2", label="East Asia (S. Korea, Japan, Taiwan)"),
        mpatches.Patch(color="#7b1fa2", label="EMEA (Turkey, Italy, EU)"),
        mpatches.Patch(color="#2e7d32", label="United Kingdom"),
        Line2D([0], [0], color="white", lw=2, label="Arrow width = flow volume"),
    ]
    ax.legend(handles=legend_elements, loc="lower left",
              fontsize=7.5, framealpha=0.25,
              facecolor="#1e3a5f", edgecolor="#4fc3f7",
              labelcolor="white", ncol=2)

    ax.set_title(
        "Polyester Textile Supply Chain — Geographic Flow & China Dependency",
        fontsize=14, fontweight="bold", color="white", pad=14
    )
    ax.text(10, 10.6,
            "Node size ∝ production share   |   Arrow width ∝ material flow value"
            "   |   Red = China exposure risk",
            ha="center", fontsize=8, color="#90caf9")

    _save(fig, "fig00_supply_chain_geography.png")


# =============================================================================
# FIG 01 — IO NETWORK (existing, refactored)
# =============================================================================

def fig_io_network():
    print("  fig01 — I-O network / China dependency")
    fig, ax = plt.subplots(figsize=(16, 7))
    ax.set_facecolor("#f5f5f5")
    fig.patch.set_facecolor("#f5f5f5")

    sizes_gbp  = [0.30, 0.60, 0.90, 1.30, 2.40, 4.20, 20.0, 51.4]
    sizes_norm = np.array(sizes_gbp) / max(sizes_gbp)
    china_dep  = [EFFECTIVE_CHINA_DEPENDENCY.get(s, 0) for s in SECTORS]
    pos        = {i: (i * 2.2, 0) for i in range(N_SECTORS)}
    cmap       = plt.cm.RdYlGn_r

    for i in range(N_SECTORS):
        for j in range(N_SECTORS):
            if A_BASE[i, j] > 0.01:
                x0, y0 = pos[i]
                x1, y1 = pos[j]
                ax.annotate("",
                    xy=(x1 - 0.18, y1), xytext=(x0 + 0.18, y0),
                    arrowprops=dict(
                        arrowstyle="->,head_width=0.25,head_length=0.18",
                        color="#1976d2", lw=A_BASE[i, j] * 9,
                        alpha=0.55, connectionstyle="arc3,rad=0.12"))

    for i, s in enumerate(SECTORS):
        x, y = pos[i]
        r    = 0.38 + sizes_norm[i] * 0.52
        ax.add_patch(plt.Circle((x, y), r, color=cmap(china_dep[i]),
                                ec="white", lw=2.5, zorder=3))
        ax.text(x, y + 0.06, s.replace("_", "\n"),
                ha="center", va="center", fontsize=6.2, fontweight="bold", zorder=4)
        ax.text(x, y - r - 0.18,
                f"China {china_dep[i]*100:.0f}%\n£{sizes_gbp[i]:.1f}bn",
                ha="center", va="top", fontsize=6, color="#444")

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
    sm.set_array([])
    cb = fig.colorbar(sm, ax=ax, orientation="vertical",
                      fraction=0.018, pad=0.01, shrink=0.6)
    cb.set_label("Effective China Dependency", fontsize=9)

    ax.set_xlim(-1.2, (N_SECTORS - 1) * 2.2 + 1.2)
    ax.set_ylim(-2.2, 1.6)
    ax.axis("off")
    ax.set_title(
        "Polyester Textile Supply Chain — Technical Coefficient Network\n"
        "Node size ∝ sector turnover  |  Colour = effective China dependency"
        "  |  Arrow width ∝ I-O coefficient",
        fontsize=11, fontweight="bold", pad=10)

    _save(fig, "fig01_supply_chain_network.png")


# =============================================================================
# FIG 04 — HMRC IMPORT TRENDS 2002–2024
# =============================================================================

def fig_hmrc_import_trends():
    print("  fig04 — HMRC annual import trends 2002-2024")

    years  = sorted(HMRC_ANNUAL_TOTALS_GBP.keys())
    totals = [HMRC_ANNUAL_TOTALS_GBP[y] / 1e9 for y in years]

    fig = plt.figure(figsize=(16, 9))
    fig.patch.set_facecolor(PALETTE["bg"])
    gs  = GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.32)

    # ── Panel A: total annual imports ─────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :])
    ax1.fill_between(years, totals, alpha=0.18, color="#1565c0")
    ax1.plot(years, totals, "o-", color="#1565c0", lw=2, ms=5)
    ax1.set_ylabel("Total UK Imports (£ bn)", fontsize=10)
    ax1.set_title("UK Synthetic Apparel Imports — Total Annual Value 2002–2024\n"
                  "(29 HS6 codes, all countries, HMRC OTS API)", fontsize=10, fontweight="bold")
    ax1.set_xlim(min(years) - 0.5, max(years) + 0.5)
    ax1.grid(axis="y", alpha=0.3, lw=0.7)

    # Annotate key events
    events = {
        2008: ("GFC",        "down"),
        2020: ("COVID-19",   "down"),
        2022: ("Ukraine/\nEnergy", "up"),
        2024: ("Red Sea",    "down"),
    }
    for yr, (label, direction) in events.items():
        if yr in years:
            idx = years.index(yr)
            y_val = totals[idx]
            dy = 0.12 if direction == "up" else -0.18
            ax1.annotate(label, xy=(yr, y_val), xytext=(yr, y_val + dy),
                         ha="center", fontsize=7.5, color=PALETTE["warn_hi"],
                         arrowprops=dict(arrowstyle="->", color=PALETTE["warn_hi"], lw=1),
                         fontweight="bold")

    # ── Panel B: key-country value trends ────────────────────────────────────
    ax2 = fig.add_subplot(gs[1, 0])
    country_colours = {
        "China":      PALETTE["china"],
        "Bangladesh": "#2e7d32",
        "Turkey":     "#7b1fa2",
        "Vietnam":    "#00838f",
        "Italy":      "#f57c00",
    }
    annual_df = pd.read_csv(BASE / "data" / "hmrc_annual_country.csv")

    for country, col in country_colours.items():
        sub = annual_df[annual_df["Country"] == country].sort_values("Year")
        if len(sub):
            ax2.plot(sub["Year"], sub["Value"] / 1e6, "o-", color=col,
                     lw=1.8, ms=4, label=country, alpha=0.9)

    ax2.set_ylabel("Import Value (£ m)", fontsize=9)
    ax2.set_title("Top-5 Country Import Values 2002–2024", fontsize=9, fontweight="bold")
    ax2.legend(fontsize=7.5, ncol=2)
    ax2.grid(alpha=0.25, lw=0.6)
    ax2.set_xlim(min(years) - 0.5, max(years) + 0.5)

    # ── Panel C: China unit price (£/kg) ─────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 1])
    price_years = sorted(HMRC_CHINA_UNIT_PRICE_GBP_PER_KG.keys())
    prices      = [HMRC_CHINA_UNIT_PRICE_GBP_PER_KG[y] for y in price_years]
    ax3.fill_between(price_years, prices, alpha=0.18, color=PALETTE["china"])
    ax3.plot(price_years, prices, "o-", color=PALETTE["china"], lw=2, ms=4)
    ax3.set_ylabel("Unit Price (£ / kg)", fontsize=9)
    ax3.set_title("China Import Unit Price 2002–2024\n"
                  "(proxy for cost-inflation pass-through)", fontsize=9, fontweight="bold")
    ax3.grid(alpha=0.25, lw=0.6)
    ax3.set_xlim(min(price_years) - 0.5, max(price_years) + 0.5)
    # Annotate the 2022 energy spike
    peak_y = max(prices)
    peak_x = price_years[prices.index(peak_y)]
    ax3.annotate(f"Energy spike\n£{peak_y:.2f}/kg",
                 xy=(peak_x, peak_y), xytext=(peak_x - 3.5, peak_y + 0.5),
                 fontsize=7.5, color=PALETTE["warn_hi"], fontweight="bold",
                 arrowprops=dict(arrowstyle="->", color=PALETTE["warn_hi"]))

    fig.suptitle("HMRC UK Synthetic Apparel Import Data — 2002 to 2024\n"
                 "Source: HMRC Overseas Trade Statistics API (downloaded 2026-04-17)",
                 fontsize=12, fontweight="bold", y=1.01)
    _save(fig, "fig04_hmrc_import_trends.png")


# =============================================================================
# FIG 05 — HMRC COUNTRY BREAKDOWN (2019–2024)
# =============================================================================

def fig_hmrc_country_breakdown():
    print("  fig05 — HMRC country breakdown 2019-2024")

    countries = ["China", "Bangladesh", "Turkey", "Vietnam",
                 "India", "Cambodia", "Italy", "Sri_Lanka", "Pakistan", "Myanmar"]
    cols = [PALETTE["china"], "#2e7d32", "#7b1fa2", "#00838f",
            "#ef5350", "#f57c00", "#1565c0", "#6d4c41", "#78909c", "#c0ca33"]
    years_sub = [2019, 2020, 2021, 2022, 2023, 2024]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle("UK Synthetic Apparel Imports by Country — 2019 to 2024\n"
                 "Value (£m) and Market Share (%)",
                 fontsize=12, fontweight="bold")

    # ── Panel A: stacked area of value ───────────────────────────────────────
    ax = axes[0]
    values_matrix = np.zeros((len(years_sub), len(countries)))
    for yi, yr in enumerate(years_sub):
        row = HMRC_ANNUAL_BY_COUNTRY_GBP.get(yr, {})
        for ci, c in enumerate(countries):
            values_matrix[yi, ci] = row.get(c, 0) / 1e6

    ax.stackplot(years_sub, values_matrix.T, labels=countries, colors=cols, alpha=0.85)
    ax.set_ylabel("Import Value (£ m)", fontsize=10)
    ax.set_title("Stacked Import Value by Country", fontsize=10, fontweight="bold")
    ax.legend(fontsize=7.5, loc="upper right", ncol=2)
    ax.set_xlim(2019, 2024)
    ax.grid(axis="y", alpha=0.25)

    # ── Panel B: market share lines ───────────────────────────────────────────
    ax2 = axes[1]
    annual_df = pd.read_csv(BASE / "data" / "hmrc_annual_country.csv")
    annual_tot = annual_df.groupby("Year")["Value"].sum()

    for ci, (country, col) in enumerate(zip(countries[:6], cols[:6])):
        sub = annual_df[(annual_df["Country"] == country) &
                        (annual_df["Year"].between(2019, 2024))].sort_values("Year")
        if len(sub):
            shares = sub["Value"].values / annual_tot[sub["Year"].values].values * 100
            ax2.plot(sub["Year"].values, shares, "o-", color=col,
                     lw=1.8, ms=5, label=country)

    ax2.set_ylabel("Market Share (%)", fontsize=10)
    ax2.set_title("Import Market Share (Top 6 Countries)", fontsize=10, fontweight="bold")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.25)
    ax2.set_xlim(2018.7, 2024.3)

    plt.tight_layout()
    _save(fig, "fig05_hmrc_country_breakdown.png")


# =============================================================================
# FIG 06 — HMRC SEASONAL DEMAND PATTERN
# =============================================================================

def fig_hmrc_seasonal():
    print("  fig06 — HMRC seasonal demand pattern")

    months     = list(range(1, 13))
    month_abbr = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
    seasonal   = HMRC_MONTHLY_SEASONAL_FACTORS

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle("UK Synthetic Apparel Import Seasonality\n"
                 "Source: HMRC OTS API 2002–2024 average (NON-EU imports)",
                 fontsize=11, fontweight="bold")

    # ── Panel A: bar chart ────────────────────────────────────────────────────
    ax = axes[0]
    bar_cols = [PALETTE["china"] if s > 1.05
                else PALETTE["warn_lo"] if s > 1.0
                else PALETTE["sa"] if s < 0.93
                else PALETTE["neutral"]
                for s in seasonal]
    bars = ax.bar(month_abbr, seasonal, color=bar_cols, edgecolor="white", width=0.7)
    ax.axhline(1.0, color="black", lw=1.2, ls="--", label="Annual mean")
    ax.set_ylabel("Seasonal Factor (1.0 = annual mean)", fontsize=10)
    ax.set_title("Monthly Demand Seasonality", fontsize=10, fontweight="bold")
    ax.set_ylim(0.75, 1.25)
    ax.legend(fontsize=8)
    for bar, v in zip(bars, seasonal):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.005, f"{v:.3f}",
                ha="center", va="bottom", fontsize=7.5)

    # ── Panel B: monthly NON-EU from CSV (recent years) ───────────────────────
    ax2 = axes[1]
    eu_df = pd.read_csv(BASE / "data" / "hmrc_monthly_eu_noneu.csv")
    noneu = eu_df[eu_df["Flow"] == "NON-EU"].copy()
    for yr, col in [(2021, "#90caf9"), (2022, "#f57c00"),
                    (2023, "#2e7d32"),  (2024, PALETTE["china"])]:
        sub = noneu[noneu["Year"] == yr].sort_values("Month")
        if len(sub) == 12:
            ax2.plot(month_abbr, sub["Value"].values / 1e6,
                     "o-", lw=1.8, ms=4, label=str(yr), color=col)

    ax2.set_ylabel("NON-EU Import Value (£ m)", fontsize=10)
    ax2.set_title("Monthly NON-EU Imports by Year\n(2021–2024)", fontsize=10, fontweight="bold")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.25)

    plt.tight_layout()
    _save(fig, "fig06_hmrc_seasonal_pattern.png")


# =============================================================================
# FIG 07 — HMRC VALIDATION: MODEL vs OBSERVED
# =============================================================================

def fig_hmrc_validation():
    print("  fig07 — HMRC validation benchmarks vs model")

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle("HMRC Observed Benchmarks — Validation Event Magnitudes\n"
                 "Source: HMRC OTS API (REAL values, downloaded 2026-04-17)",
                 fontsize=11, fontweight="bold")

    # ── Panel A: annual total change by year (2019-2024) ─────────────────────
    ax = axes[0]
    ref_years  = [2019, 2020, 2021, 2022, 2023, 2024]
    totals_sub = [HMRC_ANNUAL_TOTALS_GBP[y] / 1e6 for y in ref_years]
    colours    = [PALETTE["ok"] if y in (2019, 2021) else
                  PALETTE["warn_hi"] if y == 2020 else
                  PALETTE["warn_med"] if y in (2022, 2024) else
                  PALETTE["neutral"]
                  for y in ref_years]
    bars = ax.bar(ref_years, totals_sub, color=colours, edgecolor="white", width=0.6)
    ax.set_ylabel("Total Imports (£ m)", fontsize=10)
    ax.set_title("UK Synthetic Apparel: Annual Import Value 2019–2024\n"
                 "(validation anchor years highlighted)", fontsize=9, fontweight="bold")
    ax.set_ylim(0, max(totals_sub) * 1.18)
    ax.grid(axis="y", alpha=0.25)
    for bar, v, yr in zip(bars, totals_sub, ref_years):
        if yr > 2019:
            prev = HMRC_ANNUAL_TOTALS_GBP.get(yr - 1, 1) / 1e6
            pct  = (v - prev) / prev * 100
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 15,
                    f"{pct:+.0f}%",
                    ha="center", va="bottom", fontsize=8, fontweight="bold",
                    color=PALETTE["warn_hi"] if pct < 0 else PALETTE["ok"])
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() / 2,
                f"£{v:.0f}m", ha="center", va="center",
                fontsize=7.5, color="white", fontweight="bold")

    # ── Panel B: V5 Red Sea monthly drawdown ─────────────────────────────────
    ax2 = axes[1]
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    pcts_val = [
        HMRC_VALIDATION_BENCHMARKS["V5_RedSea_jan_value_pct"],
        HMRC_VALIDATION_BENCHMARKS["V5_RedSea_feb_value_pct"],
        HMRC_VALIDATION_BENCHMARKS["V5_RedSea_mar_value_pct"],
        -1.4, -12.1, -10.5, -1.6,   # Apr–Jul from our analysis
    ]
    eu_df  = pd.read_csv(BASE / "data" / "hmrc_monthly_eu_noneu.csv")
    noneu  = eu_df[eu_df["Flow"] == "NON-EU"]
    pcts_vol = []
    for m in range(1, 8):
        v23 = noneu[(noneu["Year"] == 2023) & (noneu["Month"] == m)]["NetMass"].sum()
        v24 = noneu[(noneu["Year"] == 2024) & (noneu["Month"] == m)]["NetMass"].sum()
        pcts_vol.append((v24 - v23) / v23 * 100 if v23 > 0 else 0)

    x    = np.arange(len(month_labels))
    w    = 0.35
    bars1 = ax2.bar(x - w/2, pcts_val, w, label="Value %",  color="#1565c0", alpha=0.85)
    bars2 = ax2.bar(x + w/2, pcts_vol, w, label="Volume %", color="#c62828", alpha=0.85)
    ax2.axhline(0, color="black", lw=0.8)
    ax2.set_xticks(x)
    ax2.set_xticklabels(month_labels)
    ax2.set_ylabel("Change vs same month 2023 (%)", fontsize=10)
    ax2.set_title("V5 Red Sea: NON-EU Imports Jan–Jul 2024 vs 2023\n"
                  "(value and volume, % YoY change per month)",
                  fontsize=9, fontweight="bold")
    ax2.legend(fontsize=8)
    ax2.grid(axis="y", alpha=0.25)
    for bar in list(bars1) + list(bars2):
        v = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 v - 0.8 if v < 0 else v + 0.3,
                 f"{v:.0f}%", ha="center",
                 va="top" if v < 0 else "bottom",
                 fontsize=6.5)

    plt.tight_layout()
    _save(fig, "fig07_hmrc_validation_events.png")


# =============================================================================
# FIG 02–03 — CONCENTRATION & RESILIENCE (from existing baseline)
# =============================================================================

def fig_concentration(baseline: Dict):
    print("  fig02 — concentration & vulnerability")
    hhi  = baseline["hhi"]
    scvi = baseline["scvi"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle("Supplier Concentration & Vulnerability by Supply Chain Stage",
                 fontsize=12, fontweight="bold")

    ax = axes[0]
    cols = [PALETTE["warn_hi"] if h > 0.25 else
            PALETTE["warn_med"] if h > 0.15 else PALETTE["ok"]
            for h in hhi["HHI"]]
    bars = ax.barh(hhi["Sector"], hhi["HHI"], color=cols, edgecolor="white")
    ax.axvline(0.25, color="#b71c1c", ls="--", lw=1.5, label="High (>0.25)")
    ax.axvline(0.15, color="#e65100", ls="--", lw=1.5, label="Medium (>0.15)")
    ax.set_xlabel("Herfindahl-Hirschman Index", fontsize=10)
    ax.set_title("Supplier Concentration (HHI)", fontsize=10, fontweight="bold")
    ax.legend(fontsize=8)
    for bar, v in zip(bars, hhi["HHI"]):
        ax.text(v + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{v:.3f}", va="center", fontsize=8)

    ax2   = axes[1]
    scvi_s = scvi.sort_values("SCVI", ascending=True)
    risk_c = {"Critical": "#b71c1c", "High": "#e53935",
               "Medium": "#fb8c00", "Low": "#43a047"}
    bar_c  = [risk_c[r] for r in scvi_s["Risk_Level"]]
    bars2  = ax2.barh(scvi_s["Sector"], scvi_s["SCVI"], color=bar_c, edgecolor="white")
    ax2.set_xlabel("Supply Chain Vulnerability Index (SCVI)", fontsize=10)
    ax2.set_title("Supply Chain Vulnerability Index", fontsize=10, fontweight="bold")
    ax2.legend(handles=[mpatches.Patch(color=v, label=k)
                         for k, v in risk_c.items()], fontsize=8)
    for bar, v in zip(bars2, scvi_s["SCVI"]):
        ax2.text(v + 0.0002, bar.get_y() + bar.get_height() / 2,
                 f"{v:.4f}", va="center", fontsize=8)
    plt.tight_layout()
    _save(fig, "fig02_concentration_vulnerability.png")


def fig_resilience_scorecard(baseline: Dict):
    print("  fig03 — resilience scorecard")
    sc   = baseline["scorecard"]
    dims = ["HHI_Score", "Redundancy_Score", "Substitution_Score",
            "Buffer_Score", "China_Dep_Score"]
    dlbl = ["HHI\n(conc.)", "Redundancy", "Substitution\nFlex.",
            "Buffer\nStock", "China\nDep."]

    fig, ax = plt.subplots(figsize=(13, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    x = np.arange(len(sc))
    w = 0.15

    for k, (dim, label) in enumerate(zip(dims, dlbl)):
        ax.bar(x + k * w, sc[dim], width=w, label=label,
               color=SECTOR_COLOURS[k], alpha=0.85, edgecolor="white")

    ax.set_xticks(x + w * 2)
    ax.set_xticklabels(
        [f"{s}\n[{g}]" for s, g in zip(sc["Sector"], sc["Resilience_Grade"])],
        fontsize=7.5, rotation=20, ha="right")
    ax.set_ylabel("Score (0 = worst, 1 = best)", fontsize=10)
    ax.set_title("Multi-Dimensional Resilience Scorecard by Supply Chain Stage\n"
                 "[letter grade: A=best, F=worst]", fontsize=10, fontweight="bold")
    ax.legend(fontsize=8, ncol=5, loc="upper right")
    ax.axhline(0.5, color="gray", ls=":", lw=1)
    ax.set_ylim(0, 1.15)
    plt.tight_layout()
    _save(fig, "fig03_resilience_scorecard.png")


# =============================================================================
# FIG 08–10 — MRIO (refactored from main.py)
# =============================================================================

def fig_mrio(mrio: MRIOModel, report: Dict):
    print("  fig08-10 — MRIO analysis")

    # ── fig08: VA heatmap ─────────────────────────────────────────────────────
    detail   = report["va_detail"]
    total_va = detail["Value_Added_GBP"].sum()
    matrix   = np.zeros((N_SECTORS, N_REGIONS))
    for r_idx, region in enumerate(REGIONS):
        for s_idx, sector in enumerate(SECTORS):
            val = detail.loc[(detail["Region"] == region) &
                             (detail["Sector"] == sector), "Value_Added_GBP"].values
            if len(val):
                matrix[s_idx, r_idx] = val[0] / total_va * 100

    fig, ax = plt.subplots(figsize=(14, 7))
    fig.patch.set_facecolor(PALETTE["bg"])
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(N_REGIONS))
    ax.set_xticklabels([REGION_LABELS[r] for r in REGIONS],
                       rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(N_SECTORS))
    ax.set_yticklabels([s.replace("_", " ") for s in SECTORS], fontsize=9)
    for ri in range(N_REGIONS):
        for si in range(N_SECTORS):
            v = matrix[si, ri]
            if v >= 0.01:
                ax.text(ri, si, f"{v:.1f}%", ha="center", va="center",
                        fontsize=7.5, color="black" if v < 15 else "white")
    plt.colorbar(im, ax=ax, label="% of total supply-chain value-added")
    ax.set_title("MRIO Value-Added Origin: Who Creates the Value in UK Textile Demand?\n"
                 "(% of total supply-chain VA, by stage and region)",
                 fontsize=11, fontweight="bold")
    plt.tight_layout()
    _save(fig, "fig08_mrio_va_heatmap.png")

    # ── fig09: China exposure ─────────────────────────────────────────────────
    df  = report["china_exposure"]
    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor(PALETTE["bg"])
    x   = np.arange(N_SECTORS); w = 0.35
    ax.bar(x - w/2, df["Nominal_China_%"],  w, label="Nominal",
           color="#1565c0", alpha=0.85)
    ax.bar(x + w/2, df["MRIO_China_%"],     w, label="MRIO effective",
           color=PALETTE["china"], alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace("_", "\n") for s in SECTORS], fontsize=8)
    ax.set_ylabel("China share (%)", fontsize=10)
    ax.set_title("Nominal vs MRIO-Effective China Exposure by Stage",
                 fontsize=10, fontweight="bold")
    ax.legend(fontsize=9)
    ax.set_ylim(0, 100)
    plt.tight_layout()
    _save(fig, "fig09_mrio_china_exposure.png")

    # ── fig10: shock ──────────────────────────────────────────────────────────
    by_region = report["china_shock_region"]
    by_sector = report["china_shock_sector"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle("MRIO: 50% China Supply Shock — Output Impact",
                 fontsize=11, fontweight="bold")
    for ax_p, data, title, col_key in [
        (axes[0], by_region, "By Region",  "Region_Label"),
        (axes[1], by_sector, "By Sector",  "Sector"),
    ]:
        cols_b = [PALETTE["warn_hi"] if v < -20 else
                  "#e53935" if v < -10 else
                  PALETTE["warn_med"] if v < -5 else PALETTE["ok"]
                  for v in data["Pct_Change"]]
        lbl = [s.replace("_", " ") for s in data[col_key]]
        bars = ax_p.barh(lbl, data["Pct_Change"], color=cols_b, edgecolor="white")
        ax_p.axvline(0, color="black", lw=0.8)
        ax_p.set_xlabel("Output change (%)", fontsize=10)
        ax_p.set_title(title, fontsize=10, fontweight="bold")
        for bar, v in zip(bars, data["Pct_Change"]):
            ax_p.text(v - 0.3 if v < 0 else v + 0.3,
                      bar.get_y() + bar.get_height() / 2,
                      f"{v:.1f}%", va="center",
                      ha="right" if v < 0 else "left", fontsize=8)
    plt.tight_layout()
    _save(fig, "fig10_mrio_china_shock.png")


# =============================================================================
# FIG 11–13 — GHOSH (refactored from main.py)
# =============================================================================

def fig_ghosh(ghosh: GhoshModel, lv_df: pd.DataFrame,
              comp_df: pd.DataFrame, shock_region: pd.DataFrame):
    print("  fig11-13 — Ghosh analysis")

    # ── fig11: linkage quadrant ───────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(9, 7))
    fig.patch.set_facecolor(PALETTE["bg"])
    quadrant_styles = {
        (True,  True):  (PALETTE["warn_hi"],  "Key sector (BL>1 & FL>1)"),
        (False, True):  ("#e65100",            "Supply-push (FL>1 only)"),
        (True,  False): ("#1565c0",            "Demand-pull (BL>1 only)"),
        (False, False): (PALETTE["neutral"],   "Independent"),
    }
    plotted = set()
    for _, row in lv_df.iterrows():
        key   = (bool(row["Demand_Critical"]), bool(row["Supply_Critical"]))
        col, lbl = quadrant_styles[key]
        ax.scatter(row["BL_Norm"], row["FL_Norm"], color=col, s=170, zorder=3,
                   label=lbl if key not in plotted else "")
        ax.annotate(row["Sector"].replace("_", "\n"),
                    (row["BL_Norm"], row["FL_Norm"]),
                    textcoords="offset points", xytext=(6, 4),
                    fontsize=7.5, color=col)
        plotted.add(key)
    ax.axhline(1.0, color="gray", ls="--", lw=1)
    ax.axvline(1.0, color="gray", ls="--", lw=1)
    ax.set_xlabel("Leontief Backward Linkage (normalised)", fontsize=10)
    ax.set_ylabel("Ghosh Forward Linkage (normalised)", fontsize=10)
    ax.set_title("Leontief vs Ghosh Linkage Analysis — Sector Classification",
                 fontsize=10, fontweight="bold")
    ax.legend(fontsize=8)
    for txt, (tx, ty) in [("Q1: Key", (0.55, 0.97)), ("Q2: Supply-Push", (0.03, 0.97)),
                           ("Q4: Demand-Pull", (0.55, 0.03)), ("Q3: Indep.", (0.03, 0.03))]:
        ax.text(tx, ty, txt, transform=ax.transAxes, fontsize=7,
                color=PALETTE["neutral"], ha="left",
                va="top" if "Q1" in txt or "Q2" in txt else "bottom", style="italic")
    plt.tight_layout()
    _save(fig, "fig11_ghosh_linkage_quadrant.png")

    # ── fig12: scenarios ──────────────────────────────────────────────────────
    sc_ids = list(GHOSH_SCENARIOS.keys())
    heat   = np.zeros((len(sc_ids), N_SECTORS))
    for r, sc_id in enumerate(sc_ids):
        res = ghosh.supply_shock(GHOSH_SCENARIOS[sc_id]["shocks"])
        heat[r, :] = res["pct_change"]

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle("Ghosh Supply-Side Analysis: Forward Propagation of Primary Input Shocks",
                 fontsize=11, fontweight="bold")

    losses = comp_df["Total_Output_Loss_GBPbn"].values
    bar_c  = [PALETTE["warn_hi"] if v > 2 else "#e53935" if v > 0.5
              else PALETTE["warn_med"] if v > 0.01 else PALETTE["ok"]
              for v in losses]
    bars = axes[0].bar(range(len(comp_df)), losses, color=bar_c, edgecolor="white")
    axes[0].set_xticks(range(len(comp_df)))
    axes[0].set_xticklabels([r["Scenario"] for _, r in comp_df.iterrows()])
    axes[0].set_ylabel("Total output loss (£ bn)")
    axes[0].set_title("Total Supply Chain Output Loss")
    for bar, v in zip(bars, losses):
        axes[0].text(bar.get_x() + bar.get_width() / 2,
                     bar.get_height() + 0.02, f"£{v:.3f}bn",
                     ha="center", va="bottom", fontsize=8)

    im = axes[1].imshow(heat, cmap="RdYlGn", aspect="auto",
                        vmin=heat.min(), vmax=0)
    axes[1].set_xticks(range(N_SECTORS))
    axes[1].set_xticklabels([s.replace("_", "\n") for s in SECTORS],
                            fontsize=7.5, rotation=15, ha="right")
    axes[1].set_yticks(range(len(sc_ids)))
    axes[1].set_yticklabels(sc_ids)
    axes[1].set_title("Sector Output Change (%) per Scenario")
    for r in range(len(sc_ids)):
        for c in range(N_SECTORS):
            v = heat[r, c]
            if abs(v) > 0.01:
                axes[1].text(c, r, f"{v:.1f}%", ha="center", va="center",
                             fontsize=7, color="black" if abs(v) < 15 else "white")
    plt.colorbar(im, ax=axes[1], label="Output change (%)")
    plt.tight_layout()
    _save(fig, "fig12_ghosh_scenarios.png")

    # ── fig13: MRIO Ghosh shock ────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(PALETTE["bg"])
    cols_b = [PALETTE["warn_hi"] if v < -20 else "#e53935" if v < -5
              else PALETTE["warn_med"] if v < -1 else PALETTE["ok"]
              for v in shock_region["Pct_Change"]]
    bars = ax.barh(shock_region["Region_Label"], shock_region["Pct_Change"],
                   color=cols_b, edgecolor="white")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_xlabel("Output change (%)", fontsize=10)
    ax.set_title("MRIO Ghosh: China 50% Primary Input Shock — Forward Cascade by Region",
                 fontsize=10, fontweight="bold")
    for bar, v in zip(bars, shock_region["Pct_Change"]):
        ax.text(v - 0.1 if v < 0 else v + 0.1,
                bar.get_y() + bar.get_height() / 2,
                f"{v:.1f}%", va="center",
                ha="right" if v < 0 else "left", fontsize=9)
    plt.tight_layout()
    _save(fig, "fig13_ghosh_mrio_shock.png")


# =============================================================================
# FIG 14–16 — PER-SCENARIO (IO output + CGE prices + ABM dynamics)
# =============================================================================

def fig_scenario(sc_key: str, scenario, result: Dict):
    pfx  = sc_key
    io_r = result["io_result"]
    cge  = result["cge_result"]
    abm  = result["abm_result"]
    T    = io_r["output"].shape[0]
    wk   = np.arange(T)
    sw   = scenario.onset_week
    cmap = plt.cm.Set2

    # ── IO output trajectories ────────────────────────────────────────────────
    fig, axes = plt.subplots(3, 3, figsize=(16, 11))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle(f"{sc_key}: {scenario.name}\nI-O Output Trajectories",
                 fontsize=11, fontweight="bold")
    axes = axes.flatten()
    for j, s in enumerate(SECTORS):
        ax = axes[j]
        bl = np.ones(T) * result.get("x_base", io_r["output"].mean(axis=0))[j]
        ax.fill_between(wk, io_r["output"][:, j], bl,
                        where=io_r["output"][:, j] < bl, alpha=0.3, color="red")
        ax.plot(wk, np.ones(T) * io_r["output"][0, j], "k--", lw=1, alpha=0.4)
        ax.plot(wk, io_r["output"][:, j], color=SECTOR_COLOURS[j], lw=1.8)
        ax.axvline(sw, color="red", ls=":", lw=1.5, alpha=0.7)
        rt = result["resilience_triangle"]
        rt_row = rt.loc[rt["Sector"] == s]
        R = rt_row["resilience_R"].values[0] if len(rt_row) else float("nan")
        ax.set_title(f"{s.replace('_',' ')}\n[R={R:.3f}]", fontsize=8)
        ax.tick_params(labelsize=7)
    for k in range(N_SECTORS, len(axes)):
        axes[k].set_visible(False)
    plt.tight_layout()
    _save(fig, f"fig14_{pfx}_io_output.png")

    # ── CGE price paths ───────────────────────────────────────────────────────
    ph  = cge["price_history"]
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    fig2.patch.set_facecolor(PALETTE["bg"])
    for j, s in enumerate(SECTORS):
        ax2.plot(ph[:, j], label=s.replace("_", " "),
                 color=SECTOR_COLOURS[j], lw=1.5)
    ax2.axhline(1.0, color="black", ls="--", lw=1)
    ax2.set_xlabel("Tatonnement iteration", fontsize=10)
    ax2.set_ylabel("Relative price (1 = baseline)", fontsize=10)
    ax2.set_title(f"{sc_key}: CGE Price Convergence  |  "
                  f"Welfare: £{cge['welfare_change_gbp']/1e9:.2f}bn",
                  fontsize=10, fontweight="bold")
    ax2.legend(fontsize=7, ncol=2)
    plt.tight_layout()
    _save(fig2, f"fig15_{pfx}_cge_prices.png")

    # ── ABM dynamics ──────────────────────────────────────────────────────────
    T_abm = abm["T"]
    w_abm = np.arange(T_abm)
    fig3, axes3 = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    fig3.patch.set_facecolor(PALETTE["bg"])
    fig3.suptitle(f"{sc_key}: Agent-Based Model — Inventory / Shortage / Orders",
                  fontsize=11, fontweight="bold")
    for j in [2, 3, 4, 5, 6, 7]:
        col = SECTOR_COLOURS[j]
        lbl = SECTORS[j].replace("_", " ")
        axes3[0].plot(w_abm, abm["inventory"][:, j], color=col, lw=1.5, label=lbl)
        axes3[1].plot(w_abm, abm["shortage"][:, j],  color=col, lw=1.5)
        axes3[2].plot(w_abm, abm["orders"][:, j],    color=col, lw=1.5)
    for ax_i in axes3:
        ax_i.axvline(sw, color="red", ls=":", lw=1.5, alpha=0.8)
        ax_i.tick_params(labelsize=8)
    axes3[0].set_ylabel("Inventory (norm.)")
    axes3[1].set_ylabel("Shortage (norm.)")
    axes3[2].set_ylabel("Orders (norm.)")
    axes3[2].set_xlabel("Week")
    axes3[0].legend(fontsize=7, ncol=3, loc="upper right")
    plt.tight_layout()
    _save(fig3, f"fig16_{pfx}_abm_dynamics.png")


# =============================================================================
# FIG 17–18 — SCENARIO COMPARISON & RECOVERY TIME
# =============================================================================

def fig_scenario_comparison(comp: pd.DataFrame, all_results: Dict):
    print("  fig17-18 — scenario comparison & recovery time")

    scenarios  = list(all_results.keys())
    sc_colours = ["#1565c0", "#2e7d32", "#c62828", "#e65100", "#6a1b9a"]
    metrics    = ["Max_Price_Rise_%", "Economic_Loss_£bn",
                  "IO_Total_Shortage", "Bullwhip_Ratio_Retail"]
    mlabels    = ["Max Price\nRise (%)", "Economic\nLoss (£bn)",
                  "I-O Total\nShortage", "Bullwhip\nRatio (Retail)"]

    fig, axes = plt.subplots(1, 4, figsize=(18, 5))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle("Cross-Scenario Comparison — Key Impact Metrics",
                 fontsize=12, fontweight="bold")
    for k, (metric, label) in enumerate(zip(metrics, mlabels)):
        ax = axes[k]
        vals = []
        for s in scenarios:
            row = comp.loc[comp.Scenario == s, metric]
            vals.append(float(row.iloc[0]) if len(row) and not pd.isna(row.iloc[0]) else 0)
        bars = ax.bar(scenarios, vals, color=sc_colours[:len(scenarios)],
                      edgecolor="white", width=0.6)
        ax.set_title(label, fontsize=10, fontweight="bold")
        ax.tick_params(axis="x", labelsize=8, rotation=15)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(vals) * 0.01 if max(vals) > 0 else 0.01,
                    f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    _save(fig, "fig17_scenario_comparison.png")

    # ── Recovery time by sector ───────────────────────────────────────────────
    fig2, ax4 = plt.subplots(figsize=(14, 6))
    fig2.patch.set_facecolor(PALETTE["bg"])
    width = 0.15
    x     = np.arange(N_SECTORS)
    for k, (sc_key, res) in enumerate(all_results.items()):
        rt  = res["recovery_time"]
        vals = [float(rt.loc[rt.Sector == s, "Recovery_Week"].iloc[0])
                if s in rt["Sector"].values and
                   not pd.isna(rt.loc[rt.Sector == s, "Recovery_Week"].iloc[0])
                else 52.0
                for s in SECTORS]
        ax4.bar(x + k * width, vals, width=width, label=sc_key,
                color=sc_colours[k], alpha=0.85, edgecolor="white")
    ax4.set_xticks(x + width * (len(scenarios) - 1) / 2)
    ax4.set_xticklabels([s.replace("_", "\n") for s in SECTORS], fontsize=8)
    ax4.set_ylabel("Recovery Time (weeks)", fontsize=10)
    ax4.set_title("Recovery Time by Sector and Scenario (ABM)\n"
                  "Weeks to restore 95% of baseline capacity",
                  fontsize=11, fontweight="bold")
    ax4.legend(fontsize=9)
    ax4.axhline(52, color="red", ls="--", lw=1, alpha=0.5)
    plt.tight_layout()
    _save(fig2, "fig18_recovery_time.png")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 65)
    print(" POLYESTER TEXTILE SUPPLY CHAIN — INTEGRATED MODEL")
    print(" I-O  ×  CGE  ×  ABM  ×  MRIO  ×  Ghosh")
    print(" HMRC 2002-2024  |  ONS IO 2023  |  GTAP v10")
    print("=" * 65)

    # ── Phase 1: New HMRC visualisations (no model run needed) ───────────────
    print("\n[Phase 1] HMRC time-series visualisations")
    fig_supply_chain_geography()
    fig_io_network()
    fig_hmrc_import_trends()
    fig_hmrc_country_breakdown()
    fig_hmrc_seasonal()
    fig_hmrc_validation()

    # ── Phase 2: Run integrated model — baseline ──────────────────────────────
    print("\n[Phase 2] Baseline model analysis")
    model    = IntegratedSupplyChainModel()
    baseline = model.baseline_report()

    _save_csv(baseline["calibration"], "00_calibration.csv")
    _save_csv(baseline["linkages"],    "01_linkages.csv")
    _save_csv(baseline["hhi"],         "03_hhi.csv")
    _save_csv(baseline["scvi"],        "04_scvi.csv")
    _save_csv(baseline["eff_china"],   "05_effective_china.csv")
    _save_csv(baseline["scorecard"],   "07_resilience_scorecard.csv")

    fig_concentration(baseline)
    fig_resilience_scorecard(baseline)

    # ── Phase 3: MRIO ────────────────────────────────────────────────────────
    print("\n[Phase 3] MRIO analysis (8 regions × 8 sectors)")
    mrio   = MRIOModel()
    report = mrio.full_report()
    _save_csv(report["va_summary"],         "09_mrio_va_by_region.csv")
    _save_csv(report["china_exposure"],     "14_mrio_china_exposure.csv")
    _save_csv(report["china_shock_region"], "15_mrio_china_shock_by_region.csv")
    fig_mrio(mrio, report)

    # ── Phase 4: Ghosh ───────────────────────────────────────────────────────
    print("\n[Phase 4] Ghosh supply-side analysis")
    ghosh       = GhoshModel()
    lv_df       = ghosh.leontief_vs_ghosh_linkages()
    comp_df     = ghosh.scenarios_comparison()
    mg          = ghosh.mrio_ghosh(mrio)
    _, shock_region = mg.china_supply_shock(0.50)
    _save_csv(lv_df,       "19_ghosh_vs_leontief_linkages.csv")
    _save_csv(comp_df,     "20_ghosh_scenarios_comparison.csv")
    _save_csv(shock_region,"22_ghosh_mrio_china_shock.csv")
    fig_ghosh(ghosh, lv_df, comp_df, shock_region)

    # ── Phase 5: Shock scenarios ──────────────────────────────────────────────
    print("\n[Phase 5] Shock scenario analysis (5 scenarios × 3 models)")
    all_results = {}
    for sc_key, scenario in ALL_SCENARIOS.items():
        print(f"  Running {sc_key}: {scenario.name}")
        result = model.run_scenario(scenario, T=52, verbose=False)
        all_results[sc_key] = result
        result["x_base"] = model.x_base
        fig_scenario(sc_key, scenario, result)

    # ── Phase 6: Cross-scenario comparison ────────────────────────────────────
    print("\n[Phase 6] Cross-scenario comparison")
    comp = model.comparison_table(all_results)
    _save_csv(comp, "99_scenario_comparison.csv")
    fig_scenario_comparison(comp, all_results)

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    n_figs = len(list(FIGDIR.glob("*.png")))
    print(f"COMPLETE  —  {n_figs} figures saved to:  {FIGDIR}")
    print(f"            CSV results in:            {RESDIR}")
    print("=" * 65)
    print("\nKEY FINDINGS:")
    print("  1. PTA is the most vulnerable stage: China 67% share, sigma=1.2")
    print("  2. Effective China dependency ~60% vs 27.3% HMRC nominal (indirect fabric)")
    print("  3. HMRC 2002-2024: China share peaked 2015, stable ~27% since 2017")
    print("  4. Red Sea 2024: NON-EU imports fell 21-26% in Jan-Mar vs prior year")
    print("  5. 2022 energy spike: +48% import value, +14% volume (price-driven)")
    print("  6. Oct is peak demand month (1.145x mean); Dec is trough (0.871x)")


if __name__ == "__main__":
    main()
