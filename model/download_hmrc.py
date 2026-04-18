"""
Download HMRC synthetic apparel import data 2002–2024 via UK Trade Info OData API.

Produces three CSV files in model/data/:
  hmrc_monthly_country.csv   — monthly Value+NetMass by country, 2002–2024
  hmrc_annual_country.csv    — annual aggregates by country
  hmrc_monthly_eu_noneu.csv  — monthly EU vs NON-EU totals (for ABM seasonality)
"""

import requests
import pandas as pd
import time
import os
from pathlib import Path

BASE_URL = "https://api.uktradeinfo.com/OTS"
OUT_DIR = Path(__file__).parent / "data"
OUT_DIR.mkdir(exist_ok=True)

# All 29 HS6 codes from the existing 2023 HMRC xlsx (Sheet1 applied-filters description)
HS6_CODES = [
    "610323", "610333", "610343",               # men's knitted, synthetic
    "610413", "610423", "610433", "610443", "610453",  # women's knitted, synthetic
    "610520",                                    # men's shirts, man-made fibres
    "611130",                                    # babies' knitted, synthetic
    "611212", "611231", "611241",               # track/swimwear, synthetic
    "611521", "611522", "611530", "611596",     # hosiery, synthetic
    "620312", "620323", "620333", "620343",     # men's woven, synthetic
    "620413", "620423", "620433", "620443", "620453", "620463",  # women's woven, synthetic
    "620930",                                    # babies' woven, synthetic
    "621430",                                    # scarves, synthetic
]

# Country IDs confirmed from API
COUNTRY_IDS = {
    "China": 720, "Bangladesh": 666, "Turkey": 52, "India": 664,
    "Vietnam": 690, "Italy": 5, "Cambodia": 696, "Sri_Lanka": 669,
    "Pakistan": 662, "Myanmar": 676, "South_Korea": 728, "Japan": 732,
    "Taiwan": 736, "USA": 902, "Germany": 4, "France": 1,
    "Netherlands": 3, "Spain": 11, "Belgium": 17, "Romania": 66,
    "Morocco": 204, "Indonesia": 700, "Jordan": 628, "Philippines": 708,
    "Thailand": 680, "Hong_Kong": 740,
}
ID_TO_COUNTRY = {v: k for k, v in COUNTRY_IDS.items()}

# FlowTypeId: 1=EU Imports, 3=Non-EU Imports
FLOW_LABELS = {1: "EU", 3: "NON-EU"}

def build_hs6_filter(codes):
    parts = [f"Commodity/Hs6Code eq '{c}'" for c in codes]
    return "(" + " or ".join(parts) + ")"

def download_year(year: int, hs6_filter: str) -> pd.DataFrame:
    """Download one calendar year, aggregated by Month × Country × FlowType."""
    month_start = year * 100 + 1
    month_end   = year * 100 + 12

    apply_clause = (
        f"filter("
        f"MonthId ge {month_start} and MonthId le {month_end} "
        f"and (FlowTypeId eq 1 or FlowTypeId eq 3) "
        f"and {hs6_filter}"
        f")/groupby("
        f"(MonthId,CountryId,FlowTypeId),"
        f"aggregate(Value with sum as TotalValue,NetMass with sum as TotalMass)"
        f")"
    )

    rows = []
    skip = 0
    page_size = 5000
    while True:
        params = {"$apply": apply_clause, "$top": page_size, "$skip": skip}
        r = requests.get(BASE_URL, params=params, timeout=60)
        if r.status_code != 200:
            print(f"  WARNING year={year} skip={skip} → HTTP {r.status_code}")
            break
        data = r.json().get("value", [])
        rows.extend(data)
        if len(data) < page_size:
            break
        skip += page_size
        time.sleep(0.3)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["Year"]  = df["MonthId"] // 100
    df["Month"] = df["MonthId"] % 100
    df["Country"] = df["CountryId"].map(ID_TO_COUNTRY).fillna("Other")
    df["Flow"]    = df["FlowTypeId"].map(FLOW_LABELS)
    return df[["Year", "Month", "MonthId", "CountryId", "Country", "Flow",
               "TotalValue", "TotalMass"]]


def main():
    hs6_filter = build_hs6_filter(HS6_CODES)
    all_frames = []

    for year in range(2002, 2025):
        print(f"Downloading {year}...", end=" ", flush=True)
        df = download_year(year, hs6_filter)
        if not df.empty:
            all_frames.append(df)
            print(f"{len(df)} rows")
        else:
            print("no data")
        time.sleep(0.5)

    if not all_frames:
        print("No data downloaded.")
        return

    monthly = pd.concat(all_frames, ignore_index=True)
    monthly.sort_values(["Year", "Month", "Country"], inplace=True)

    # ── 1. Monthly by country ──────────────────────────────────────────────
    out_monthly = OUT_DIR / "hmrc_monthly_country.csv"
    monthly.to_csv(out_monthly, index=False)
    print(f"\nSaved: {out_monthly}  ({len(monthly)} rows)")

    # ── 2. Annual by country ───────────────────────────────────────────────
    annual = (
        monthly.groupby(["Year", "Country", "CountryId"], as_index=False)
        .agg(Value=("TotalValue", "sum"), NetMass=("TotalMass", "sum"))
    )
    annual["UnitPrice_GBP_per_kg"] = (
        annual["Value"] / annual["NetMass"].replace(0, float("nan"))
    )
    out_annual = OUT_DIR / "hmrc_annual_country.csv"
    annual.to_csv(out_annual, index=False)
    print(f"Saved: {out_annual}  ({len(annual)} rows)")

    # ── 3. Monthly EU vs NON-EU totals ────────────────────────────────────
    eu_noneu = (
        monthly.groupby(["Year", "Month", "MonthId", "Flow"], as_index=False)
        .agg(Value=("TotalValue", "sum"), NetMass=("TotalMass", "sum"))
    )
    eu_noneu.sort_values(["MonthId", "Flow"], inplace=True)
    out_eu = OUT_DIR / "hmrc_monthly_eu_noneu.csv"
    eu_noneu.to_csv(out_eu, index=False)
    print(f"Saved: {out_eu}  ({len(eu_noneu)} rows)")

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n=== Download Summary ===")
    total_val = monthly["TotalValue"].sum()
    print(f"Total records: {len(monthly):,}")
    print(f"Years covered: {monthly['Year'].min()}–{monthly['Year'].max()}")
    print(f"Countries with data: {monthly['Country'].nunique()}")
    print(f"Aggregate value across all years: £{total_val/1e9:.2f}bn")

    # 2023 cross-check vs existing xlsx
    check = annual[(annual["Year"] == 2023)]
    total_2023 = check["Value"].sum()
    china_2023 = check[check["Country"] == "China"]["Value"].sum()
    print(f"\n2023 cross-check:")
    print(f"  Total: £{total_2023/1e6:.1f}m  (xlsx: £2,388.9m)")
    print(f"  China: £{china_2023/1e6:.1f}m  (xlsx: £651.4m)")


if __name__ == "__main__":
    main()
