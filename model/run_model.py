"""
run_model.py
Command-line program for the Polyester Textile Supply Chain Model.

Usage:
    python run_model.py baseline              # baseline analysis + resilience scorecard
    python run_model.py scenario S1           # run scenario S1 (52 weeks)
    python run_model.py scenario all          # run all 5 scenarios + comparison table
    python run_model.py hmrc                  # HMRC import data summary
    python run_model.py validate              # validation benchmarks vs HMRC
    python run_model.py visualise             # run full visualisation pipeline
"""

import argparse
import sys
import os
from pathlib import Path
import io

# ── Encoding fix (Windows CP1252 → UTF-8) ─────────────────────────────────────
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Ensure model directory is on path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

# ── Formatting helpers ────────────────────────────────────────────────────────

def _hline(char="=", width=72):
    print(char * width)

def _section(title):
    _hline()
    print(f"  {title}")
    _hline()

def _print_df(df: pd.DataFrame, max_rows: int = 40):
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 120)
    pd.set_option("display.float_format", "{:.4f}".format)
    print(df.to_string(index=False, max_rows=max_rows))

# ── Sub-commands ──────────────────────────────────────────────────────────────

def cmd_baseline(args):
    """Print baseline supply chain characterisation."""
    _section("BASELINE ANALYSIS  —  Polyester Textile Supply Chain")

    from integrated_model import IntegratedSupplyChainModel
    print("Loading model...", flush=True)
    model    = IntegratedSupplyChainModel()
    baseline = model.baseline_report()

    # HHI
    print("\n--- Supplier Concentration (HHI) ---")
    _print_df(baseline["hhi"])

    # SCVI
    print("\n--- Supply Chain Vulnerability Index (SCVI) ---")
    scvi = baseline["scvi"]
    if isinstance(scvi, pd.DataFrame):
        _print_df(scvi)
    else:
        print(scvi)

    # Effective China dependency
    print("\n--- Effective China Dependency (upstream-traced) ---")
    eff = baseline["eff_china"]
    if isinstance(eff, pd.DataFrame):
        _print_df(eff)
    else:
        print(eff)

    # Multipliers
    print("\n--- I-O Multipliers ---")
    mult = baseline["multipliers"]
    if isinstance(mult, pd.DataFrame):
        _print_df(mult)
    else:
        print(mult)

    # Resilience scorecard
    print("\n--- Resilience Scorecard ---")
    sc = baseline["scorecard"]
    if isinstance(sc, pd.DataFrame):
        _print_df(sc)
    else:
        print(sc)

    # Geographic risk
    print("\n--- Geographic Risk (CGE) ---")
    gr = baseline["geo_risk"]
    if isinstance(gr, pd.DataFrame):
        _print_df(gr)
    elif isinstance(gr, dict):
        for k, v in gr.items():
            print(f"  {k}: {v}")
    else:
        print(gr)

    _hline()
    print("Baseline analysis complete.")


def cmd_scenario(args):
    """Run one or all shock scenarios."""
    from integrated_model import IntegratedSupplyChainModel
    from shocks import ALL_SCENARIOS

    _section(f"SCENARIO ANALYSIS  —  {args.scenario.upper()}")

    print("Loading model...", flush=True)
    model = IntegratedSupplyChainModel()
    T     = args.weeks

    if args.scenario.upper() == "ALL":
        scenarios_to_run = ALL_SCENARIOS
    else:
        key = args.scenario.upper()
        if key not in ALL_SCENARIOS:
            print(f"ERROR: unknown scenario '{key}'. Choose from: {list(ALL_SCENARIOS.keys())} or 'all'")
            sys.exit(1)
        scenarios_to_run = {key: ALL_SCENARIOS[key]}

    all_results = {}
    for key, scenario in scenarios_to_run.items():
        print(f"\nRunning {key}: {scenario.name}...")
        result = model.run_scenario(scenario, T=T, verbose=args.verbose)
        all_results[key] = result

        if args.verbose or len(scenarios_to_run) == 1:
            cge  = result["cge_result"]
            io_r = result["io_result"]
            bw   = result["bullwhip"]
            sl   = result["service_level"]
            rt   = result["recovery_time"]

            p_chg = cge["price_index_change_pct"]
            from real_data import SECTORS
            max_p_s = SECTORS[int(p_chg.argmax())]

            print(f"\n  [CGE]  Max price rise:  {p_chg.max():.1f}% at {max_p_s}")
            print(f"  [CGE]  Welfare change:   GBP {cge['welfare_change_gbp']/1e9:.3f}bn")
            print(f"  [IO ]  Total shortage:   {io_r['shortage'].sum():.4f}")
            print(f"  [ABM]  Economic loss:    GBP {result['total_shortage_gbp']/1e9:.3f}bn")
            print()

            print("  Bullwhip Ratios:")
            _print_df(bw)
            print("\n  Service Levels:")
            _print_df(sl)
            print("\n  Recovery Times:")
            _print_df(rt)

    if len(all_results) > 1:
        print("\n\n--- CROSS-SCENARIO COMPARISON ---")
        table = model.comparison_table(all_results)
        _print_df(table)

        if args.save:
            out = Path(__file__).parent / "results" / "scenario_comparison.csv"
            out.parent.mkdir(exist_ok=True)
            table.to_csv(out, index=False)
            print(f"\nSaved comparison table: {out}")

    _hline()


def cmd_hmrc(args):
    """Print HMRC import data summary."""
    _section("HMRC OTS — UK Synthetic Apparel Import Summary  (2002-2024)")

    DATA_DIR = Path(__file__).parent / "data"

    annual  = pd.read_csv(DATA_DIR / "hmrc_annual_country.csv")
    eu_nn   = pd.read_csv(DATA_DIR / "hmrc_monthly_eu_noneu.csv")

    # Totals
    totals = annual.groupby("Year")["Value"].sum()
    print("\n--- Annual Totals (GBP) ---")
    print(f"{'Year':>6}  {'Value (GBP)':>16}  {'YoY %':>8}")
    prev = None
    for yr, val in totals.items():
        if prev is not None:
            yoy = f"{(val-prev)/prev*100:+.1f}%"
        else:
            yoy = "—"
        print(f"{yr:>6}  {val:>16,.0f}  {yoy:>8}")
        prev = val

    # Country breakdown — latest 3 years
    latest = int(annual["Year"].max())
    print(f"\n--- Country Breakdown — {latest} ---")
    yd = annual[annual["Year"] == latest].sort_values("Value", ascending=False)
    tot = yd["Value"].sum()
    print(f"{'Country':>20}  {'Value GBP':>14}  {'Share':>7}  {'Unit Price':>12}")
    for _, row in yd.head(15).iterrows():
        up = f'{row["UnitPrice_GBP_per_kg"]:.2f} GBP/kg' if pd.notna(row.get("UnitPrice_GBP_per_kg")) else "—"
        print(f'{row["Country"]:>20}  {row["Value"]:>14,.0f}  {row["Value"]/tot*100:>6.1f}%  {up:>12}')

    # Seasonal summary
    from real_data import HMRC_MONTHLY_SEASONAL_FACTORS
    MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    print("\n--- Monthly Seasonal Factors (NON-EU 2002-2024 average) ---")
    for m, f in zip(MONTHS, HMRC_MONTHLY_SEASONAL_FACTORS):
        bar = "#" * int(f * 20)
        tag = " <- PEAK" if f == max(HMRC_MONTHLY_SEASONAL_FACTORS) else (
              " <- TROUGH" if f == min(HMRC_MONTHLY_SEASONAL_FACTORS) else "")
        print(f"  {m:>3}  {f:.3f}  {bar}{tag}")

    # EU vs NON-EU recent
    print(f"\n--- EU vs NON-EU ({latest-1}→{latest}) ---")
    for flow in ["EU", "NON-EU"]:
        v_now  = eu_nn[(eu_nn["Year"] == latest)   & (eu_nn["Flow"] == flow)]["Value"].sum()
        v_prev = eu_nn[(eu_nn["Year"] == latest-1) & (eu_nn["Flow"] == flow)]["Value"].sum()
        yoy    = (v_now - v_prev) / v_prev * 100 if v_prev > 0 else float("nan")
        print(f"  {flow:>8}:  GBP {v_now/1e6:>8.1f}m  ({yoy:+.1f}% YoY)")

    _hline()


def cmd_validate(args):
    """Print validation results vs HMRC benchmarks."""
    _section("MODEL VALIDATION  —  HMRC Benchmark Comparison")

    from real_data import HMRC_VALIDATION_BENCHMARKS as VB

    # Print HMRC benchmarks
    print("\n--- HMRC Observed Values ---")
    labels = {
        "V1_COVID_china_value_pct":  "V1 COVID (2020) — China value change",
        "V1_COVID_china_volume_pct": "V1 COVID (2020) — China volume change",
        "V1_COVID_total_value_pct":  "V1 COVID (2020) — Total UK change",
        "V5_RedSea_jan_value_pct":   "V5 Red Sea — Jan 2024 NON-EU",
        "V5_RedSea_feb_value_pct":   "V5 Red Sea — Feb 2024 NON-EU",
        "V5_RedSea_mar_value_pct":   "V5 Red Sea — Mar 2024 NON-EU",
        "V5_RedSea_H1_value_pct":    "V5 Red Sea — H1 2024 NON-EU",
        "V5_RedSea_annual_value_pct":"V5 Red Sea — Full year 2024",
        "V6_Shanghai_Q2_china_value_pct": "V6 Shanghai Q2 2022 — China value",
        "V6_Shanghai_Q2_china_vol_pct":   "V6 Shanghai Q2 2022 — China volume",
        "V7_Ukraine_annual_value_pct":    "V7 Ukraine (2022) — Annual value",
    }
    for key, label in labels.items():
        val = VB.get(key, "—")
        print(f"  {label:<55}  {val:>+8.1f}%" if isinstance(val, (int, float)) else
              f"  {label:<55}  {val}")

    # Run validation module
    print("\n--- Running Validation Module ---")
    try:
        import validation
        validation.run_all_validations()
    except Exception as e:
        print(f"  (Validation module: {e})")
        print("  Showing HMRC benchmarks only.")

    _hline()


def cmd_visualise(args):
    """Run the full visualisation pipeline."""
    _section("VISUALISATION PIPELINE")
    import visualise
    visualise.main()


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        prog="run_model.py",
        description="Polyester Textile Supply Chain Model — CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_model.py baseline
  python run_model.py scenario S1 --weeks 26
  python run_model.py scenario all --save
  python run_model.py hmrc
  python run_model.py validate
  python run_model.py visualise
        """,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # baseline
    sub.add_parser("baseline", help="Baseline supply chain characterisation")

    # scenario
    p_sc = sub.add_parser("scenario", help="Run shock scenario(s)")
    p_sc.add_argument("scenario", metavar="SCENARIO",
                      help="Scenario key: S1 S2 S3 S4 S5 or 'all'")
    p_sc.add_argument("--weeks",   type=int, default=52,
                      help="Simulation weeks (default: 52)")
    p_sc.add_argument("--verbose", action="store_true",
                      help="Print full per-scenario tables")
    p_sc.add_argument("--save",    action="store_true",
                      help="Save comparison CSV to results/")

    # hmrc
    sub.add_parser("hmrc", help="HMRC import data summary")

    # validate
    p_val = sub.add_parser("validate", help="Model validation vs HMRC benchmarks")
    p_val.add_argument("--verbose", action="store_true")

    # visualise
    sub.add_parser("visualise", help="Run full visualisation pipeline")

    return parser


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "baseline":  cmd_baseline,
        "scenario":  cmd_scenario,
        "hmrc":      cmd_hmrc,
        "validate":  cmd_validate,
        "visualise": cmd_visualise,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
