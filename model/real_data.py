"""
real_data.py
All empirical data sourced from:
  - RiSC_report.docx
  - Findings-02-12-2024.docx
  - Textile Industrial Supply Chain 09122024.pptx
  - Logistics_Price_Info.pptx
  - 2023 Synthetic Apparel Imports HMRC.xlsx (By Country sheet)
  - HMRC UK Trade Info OTS API — downloaded 2026-04-17, 2002-2024 time series
    (29 HS6 codes: synthetic apparel chapters 61+62; all countries; monthly)
"""

import numpy as np

# ── Supply chain sectors (ordered upstream → downstream) ─────────────────────
SECTORS = [
    "Oil_Extraction",        # 0
    "Chemical_Processing",   # 1  MEG + p-Xylene production
    "PTA_Production",        # 2  Purified Terephthalic Acid
    "PET_Resin_Yarn",        # 3  Polymerisation + spinning
    "Fabric_Weaving",        # 4
    "Garment_Assembly",      # 5
    "UK_Wholesale",          # 6  logistics / distribution
    "UK_Retail",             # 7
]
N_SECTORS = len(SECTORS)

# ── UK 2023 Synthetic Apparel Imports — HMRC data ────────────────────────────
# HMRC OTS API total (2023, HS61+62 synthetic apparel, all countries).
# This is the authoritative figure from the API download (2026-04-17).
# A separate xlsx snapshot gives £2,388,954,178 — the £3.9m gap (0.16%) is a
# provisional-to-final revision by HMRC between download dates.  The API value
# below is used as the denominator for all share calculations.
UK_IMPORTS_TOTAL_GBP = 2_392_841_303   # HMRC OTS API 2023 (authoritative)
UK_IMPORTS_TOTAL_GBP_XLSX = 2_388_954_178   # xlsx snapshot (retained for reference)

# IMPORTANT: The HMRC raw download has both an "EU" aggregate row AND individual
# EU-member rows (Italy, Netherlands, Spain, France, Belgium, Germany, Romania).
# Including both double-counts £471.6m. This dict lists INDIVIDUAL countries only;
# the EU aggregate is stored separately as UK_IMPORTS_EU_TOTAL_GBP.
# Residual EU (countries not individually named): £586.5m - £471.6m = £115.0m
# captured via "EU_Other" below so shares still sum to 1.0.
UK_IMPORTS_EU_TOTAL_GBP = 586_526_782   # total EU block (HMRC HS61+62 2023)

UK_IMPORTS_BY_COUNTRY = {
    # value_gbp from HMRC OTS API (2023); share = value / UK_IMPORTS_TOTAL_GBP.
    # China API value (653,175,775) differs from xlsx (651,373,563) by £1.8m —
    # same provisional-revision gap; API value used for the share denominator.
    "China":        {"value_gbp": 653_175_775,  "share": 0.27298},
    "Bangladesh":   {"value_gbp": 287_422_073,  "share": 0.12031},
    "Turkey":       {"value_gbp": 143_694_104,  "share": 0.06015},
    "Vietnam":      {"value_gbp": 117_735_860,  "share": 0.04928},
    "Italy":        {"value_gbp": 101_522_756,  "share": 0.04250},
    "India":        {"value_gbp": 87_903_954,   "share": 0.03680},
    "Netherlands":  {"value_gbp": 82_147_487,   "share": 0.03439},
    "Spain":        {"value_gbp": 80_474_939,   "share": 0.03369},
    "France":       {"value_gbp": 79_504_634,   "share": 0.03328},
    "Cambodia":     {"value_gbp": 79_325_931,   "share": 0.03321},
    "Sri_Lanka":    {"value_gbp": 65_106_449,   "share": 0.02725},
    "Pakistan":     {"value_gbp": 63_140_646,   "share": 0.02643},
    "Belgium":      {"value_gbp": 62_967_672,   "share": 0.02636},
    "Myanmar":      {"value_gbp": 51_248_724,   "share": 0.02145},
    "Germany":      {"value_gbp": 47_399_236,   "share": 0.01984},
    "Hong_Kong":    {"value_gbp": 47_304_519,   "share": 0.01980},
    "Morocco":      {"value_gbp": 46_753_409,   "share": 0.01957},
    "Indonesia":    {"value_gbp": 25_812_968,   "share": 0.01081},
    "Romania":      {"value_gbp": 17_537_957,   "share": 0.00734},
    "Jordan":       {"value_gbp": 13_010_271,   "share": 0.00545},
    "Philippines":  {"value_gbp": 12_962_664,   "share": 0.00543},
    "Thailand":     {"value_gbp":  8_655_357,   "share": 0.00362},
    # Residual: all other countries not individually reported by HMRC
    # = Total (GBP2,388,954,178) minus all individually named entries above
    "EU_Other":     {"value_gbp": 215_949_005,  "share": 0.09039},
}

# ── UK domestic industry (ONS via research) ───────────────────────────────────
UK_INDUSTRY = {
    "manufacturers": {"companies": 10_870, "turnover_gbp": 9_400_000_000},
    "wholesale":     {"companies": 11_230, "turnover_gbp": 20_000_000_000},
    "retail":        {"companies": 30_790, "turnover_gbp": 51_400_000_000},
}

# ── Global fibre production shares (TextileExchange 2024) ─────────────────────
GLOBAL_FIBRE_SHARES = {
    "polyester": 0.57,
    "cotton":    0.20,
    "nylon":     0.05,
    "viscose":   0.06,
    "acrylic":   0.02,
    "other":     0.10,
}

# ── China upstream import dependency ──────────────────────────────────────────
# Source: Textile Industrial Supply Chain pptx
CHINA_IMPORT_DEPENDENCY = {
    "MEG":      0.43,   # China imports 43 % of world's ethylene glycol
    "p_xylene": 0.45,   # China imports 45 % of world's p-Xylene
}

# ── China share of global PTA production ──────────────────────────────────────
# Updated: GlobalData (2021) capacity survey: China ~67 % of global PTA capacity.
# Previous estimate was 0.72 from qualitative research text ("vast majority").
CHINA_PTA_GLOBAL_SHARE = 0.67

# ── Oil sources for p-Xylene route (SK refineries, Japan refineries) ──────────
OIL_IMPORT_SOURCES = {
    "South_Korea": {
        "Saudi_Arabia": 0.31, "USA": 0.16, "UAE": 0.11,
        "Kuwait": 0.10, "Other": 0.32,
    },
    "Japan": {
        "Saudi_Arabia": 0.41, "UAE": 0.40, "Kuwait": 0.09, "Other": 0.10,
    },
}

# ── Transit times (days, from Logistics_Price_Info.pptx) ─────────────────────
TRANSIT_DAYS = {
    ("Saudi_Arabia",  "China"):        23,
    ("Saudi_Arabia",  "South_Korea"):  17,
    ("South_Korea",   "Japan"):         2,
    ("Japan",         "China"):        13,
    ("South_Korea",   "China"):        28,
    ("China",         "UK"):           37,
    ("Bangladesh",    "UK"):           28,
    ("Turkey",        "UK"):            7,
    ("India",         "UK"):           25,
    ("Vietnam",       "UK"):           32,
}

# ── Port MEG inventories, China (Feb 2022, Logistics pptx) ───────────────────
MEG_PORT_INVENTORY_KT = {
    "Zhangjiagang":       418,
    "Jiangyin_Changzhou": 134,
    "Taicang":             85,
    "Ningbo":              51,
}
MEG_TOTAL_INVENTORY_KT = sum(MEG_PORT_INVENTORY_KT.values())  # 688 kt

# ── Geographic concentration of production at each supply chain stage ─────────
# Fractions of GLOBAL capacity. Calibrated from research data.
STAGE_GEOGRAPHY = {
    "Oil_Extraction": {
        # Updated: Wikipedia / EIA International Energy Statistics (Nov 2025 snapshot).
        # Global crude production ≈ 86,281 kb/d.  Values = country share of world total.
        # Source: https://en.wikipedia.org/wiki/List_of_countries_by_oil_production
        "USA":          0.160,   # 13,782 kb/d = 16.0 %
        "Russia":       0.116,   # 10,056 kb/d = 11.6 %
        "Saudi_Arabia": 0.115,   # 9,940 kb/d  = 11.5 %
        "Canada":       0.061,   # 5,234 kb/d  =  6.1 %
        "Iraq":         0.051,   # 4,391 kb/d  =  5.1 %
        "UAE":          0.047,   # 4,050 kb/d  =  4.7 %
        "Other":        0.450,   # Residual: Iran 4.8%, China 5.0%, Brazil 4.4%,
                                 # Kuwait 3.1%, Kazakhstan 2.4%, Norway 2.2%, etc.
    },
    "Chemical_Processing": {   # MEG + p-Xylene
        "China":        0.35,  # domestic MEG + p-Xylene
        "Saudi_Arabia": 0.18,  # SABIC / Jubail United (MEG)
        "South_Korea":  0.14,  # refinery p-Xylene
        "Japan":        0.10,  # refinery p-Xylene
        "USA":          0.12,
        "Other":        0.11,
    },
    "PTA_Production": {
        # Updated: GlobalData 2021 capacity survey — China 67% of global PTA
        "China":        0.67,
        "India":        0.07,  # Reliance Industries + IOCL
        "South_Korea":  0.06,  # SK Chemicals, Huvis
        "USA":          0.05,  # BP, Eastman
        "Other":        0.15,
    },
    "PET_Resin_Yarn": {
        # Updated: CIRFS / Textile Exchange 2023 polyester fibre production
        # China ~60%, India ~13%, South Korea ~6%, remainder split
        "China":        0.60,
        "India":        0.13,
        "South_Korea":  0.06,
        "Taiwan":       0.04,
        "Other":        0.17,
    },
    "Fabric_Weaving": {
        # Updated: WTO International Trade Statistics 2024 — textile exports share
        # China 43.3%, India 11%, Bangladesh 5%, Turkey 5%, others
        "China":        0.433,
        "India":        0.110,
        "Bangladesh":   0.050,
        "Turkey":       0.050,
        "Other":        0.357,
    },
    "Garment_Assembly": {
        # Updated: HMRC 2023 synthetic apparel imports — direct real data by country
        # Shares derived from UK_IMPORTS_BY_COUNTRY (BY COUNTRY sheet)
        "China":        0.2727,  # HMRC 2023: £651.4m / £2,389m
        "Bangladesh":   0.1203,  # HMRC 2023: £287.4m / £2,389m
        "Turkey":       0.0602,  # HMRC 2023: £143.7m / £2,389m
        "Vietnam":      0.0493,  # HMRC 2023: £117.7m / £2,389m
        "Italy":        0.0425,  # HMRC 2023: £101.5m / £2,389m
        "India":        0.0368,  # HMRC 2023: £87.9m  / £2,389m
        "Cambodia":     0.0332,  # HMRC 2023: £79.3m  / £2,389m
        "Sri_Lanka":    0.0273,  # HMRC 2023: £65.1m  / £2,389m
        "Pakistan":     0.0264,  # HMRC 2023: £63.1m  / £2,389m
        "Myanmar":      0.0215,  # HMRC 2023: £51.2m  / £2,389m
        "Other":        0.3098,  # residual (EU repackaged + ROW)
    },
    "UK_Wholesale": {
        "UK":           0.85,
        "Other":        0.15,
    },
    "UK_Retail": {
        "UK":           1.00,
    },
}

# ── ASOS supplier breakdown (Findings doc — representative major UK retailer) ─
ASOS_SUPPLIERS = {
    "China": 0.260, "Turkey": 0.215, "India": 0.177,
    "Bangladesh": 0.066, "Other": 0.282,
}

# ── Value-added shares: fraction of RETAIL price attributable to each stage ───
# Derived from ONS UK Input-Output Analytical Tables 2023 (published 2025).
# Method: backward chain from retail using sector GVA/Output ratios extracted
# from the IOT domestic use table (total output and GVA rows).
#   GVA/Output rates (ONS IOT 2023):
#     Oil (CPA_B):    GVA £25,313m / Output £37,016m = 0.684
#     RefPetro(C19):  GVA  £2,870m / Output £35,147m = 0.082
#     Petrochem(C20B):GVA  £2,171m / Output  £9,738m = 0.223
#     Textiles(C13):  GVA  £3,514m / Output  £7,347m = 0.478
#     Apparel(C14):   GVA  £1,801m / Output  £3,266m = 0.552
#     Wholesale(G46): GVA £113,354m/ Output £214,742m= 0.528
#     Retail(G47):    GVA £104,392m/ Output £174,593m= 0.598
# Backward chain: vs[j] = vs[j+1] × (1 - GVA_rate[j+1])
# Backward chain: vs[j] = vs[child] × (1 − GVA_rate[child])
# anchored at UK_Retail = 1.0 and propagated upstream one stage at a time.
#
#   UK_Retail           = 1.000  (anchor)
#   UK_Wholesale        = 1.000 × (1 − 0.598) = 0.402
#   Garment_Assembly    = 0.402 × (1 − 0.528) = 0.190
#   Fabric_Weaving      = 0.190 × (1 − 0.552) = 0.085
#   PET_Resin_Yarn      = 0.085 × (1 − 0.478) = 0.044
#   PTA_Production      = 0.044 × (1 − 0.210) = 0.035
#   Chemical_Processing = 0.035 × (1 − 0.190) = 0.028   ← corrected (was 0.031)
#   Oil_Extraction      = 0.028 × (1 − 0.223) = 0.022   ← corrected (was 0.010, 2× error)
#
# Previous errors: Chemical used GVA_rate of C19 refining (0.082) instead of
# PTA (0.190); Oil used Chemical as parent instead of PTA, compounding the error.
STAGE_RETAIL_VALUE_SHARE = {
    "Oil_Extraction":      0.022,   # 0.028 × (1 − 0.223) — corrected
    "Chemical_Processing": 0.028,   # 0.035 × (1 − 0.190) — corrected
    "PTA_Production":      0.035,   # 0.044 × (1 − 0.210)
    "PET_Resin_Yarn":      0.044,   # 0.085 × (1 − 0.478)
    "Fabric_Weaving":      0.085,   # 0.190 × (1 − 0.552)
    "Garment_Assembly":    0.190,   # 0.402 × (1 − 0.528)
    "UK_Wholesale":        0.402,   # 1.000 × (1 − 0.598)
    "UK_Retail":           1.000,   # anchor
}

# ── Nylon producers (for cross-industry resilience analysis) ──────────────────
NYLON_PRODUCERS = {
    "Ascend":      {"country": "USA",    "listed": True},
    "Invista":     {"country": "USA",    "listed": False, "owner": "Koch Inc"},
    "Butachimie":  {"country": "France", "listed": False, "owner": "Invista+BASF"},
    "Asahi_Kasei": {"country": "Japan",  "listed": True},
}

# ── Cotton production (Liu & Hudson 2022, cited in Findings) ──────────────────
COTTON_PRODUCTION = {
    "China": 0.225, "India": 0.225, "USA": 0.147, "Other": 0.403,
}

# ── Effective China dependency: upstream-tracing calculation ──────────────────
def compute_effective_china_dependency() -> dict:
    """
    Two-tier upstream supply-origin tracing of China's effective share.

    Tier 1 (direct): China's share in STAGE_GEOGRAPHY at each stage.
    Tier 2 (indirect): For each non-China supplier s at stage j,
        add  share_s × china_share_at_upstream_stage(j)
        where upstream_stage(j) is the immediate input stage for j.

    Upstream linkages used for tier-2:
        Garment      ← Fabric        (fabric is the primary material input)
        Fabric       ← PET/Yarn      (polyester fibre is ~55% of fabric cost)
        PET/Yarn     ← PTA           (PTA is ~55% of PET cost)
        PTA          ← Chemical      (p-Xylene/MEG ~94% of PTA cost)
        Chemical     ← Oil           (naphtha feedstock ~20% of chem cost)

    Oil has no modelled upstream, so only tier-1 applies there.
    Wholesale and Retail are domestic services — no upstream tracing needed.

    The formula for tier-2 at stage j with upstream stage u:
        eff_j = china_j_direct + (1 - china_j_direct) × china_u_direct
    This is a first-order approximation; in practice second-order effects
    are small and within data uncertainty.
    """
    upstream_of = {
        "Garment_Assembly":    "Fabric_Weaving",
        "Fabric_Weaving":      "PET_Resin_Yarn",
        "PET_Resin_Yarn":      "PTA_Production",
        "PTA_Production":      "Chemical_Processing",
        "Chemical_Processing": "Oil_Extraction",
    }

    # Direct China share (tier-1)
    direct = {}
    for s, geo in STAGE_GEOGRAPHY.items():
        china_keys = [k for k in geo if "China" in k]
        direct[s] = sum(geo[k] for k in china_keys)

    # China's ~5% global crude oil share is bundled into the "Other" key
    # in Oil_Extraction geography (EIA list groups it with Iran, Brazil etc.).
    # Override with EIA estimate so Oil is not falsely zero.
    CHINA_OIL_SHARE_APPROX = 0.050

    result = {}
    for s in SECTORS:
        d = direct.get(s, 0.0)
        if s == "Oil_Extraction":
            # China's direct share not explicit in STAGE_GEOGRAPHY → use EIA estimate
            result[s] = round(CHINA_OIL_SHARE_APPROX, 3)
            continue
        up = upstream_of.get(s)
        if up is not None:
            # Tier-2: non-China share × China's direct fraction at the upstream stage
            # Use direct shares only (not recursive) to avoid compounding across
            # multiple tiers beyond what the data supports.
            china_up_direct = direct.get(up, 0.0)
            if up == "Oil_Extraction":
                china_up_direct = CHINA_OIL_SHARE_APPROX
            result[s] = round(d + (1.0 - d) * china_up_direct, 3)
        else:
            result[s] = round(d, 3)

    # Domestic services: zero upstream exposure
    result["UK_Wholesale"] = 0.0
    result["UK_Retail"]    = 0.0
    return result


# Pre-computed effective China dependency (call once at module load).
#
# Cross-check against research-document figure (Textile Industrial SC pptx):
#   Garment: direct 27.3% + (72.7% × 43.3% Fabric) = 58.8%  ← pptx = 60% ✓
#   Chemical: direct 35% + (65% × 5% Oil China) = 38.2%
#             pptx reports 47% using demand-concentration tracing (fraction of
#             global MEG/p-Xylene output consumed inside China-affiliate chains).
#             Supply-origin figure = 38%.  Both are stored for transparency.
#   PTA: direct 67% + (33% × 35% Chemical) = 78.5%
#        The 33% non-China PTA producers depend partly on Chinese MEG/p-Xylene.
#   PET: direct 60% + (40% × 67% PTA direct) = 86.8%
#        Upper bound — assumes non-China PET uses global-average PTA mix.
EFFECTIVE_CHINA_DEPENDENCY = compute_effective_china_dependency()

# Research-document figure (Textile Industrial SC pptx) using demand-concentration
# tracing for Chemical_Processing (47% = share of global MEG/p-Xylene going to
# China-affiliated chains).  Retained as a separate reference constant.
EFFECTIVE_CHINA_DEPENDENCY_PPTX = {
    **EFFECTIVE_CHINA_DEPENDENCY,
    "Chemical_Processing": 0.47,   # pptx demand-concentration figure
}

# ── GVA / Output ratios from ONS IO Analytical Tables 2023 ──────────────────
# Gross Value Added divided by Gross Output at each supply chain stage.
# Source: ONS UK Input-Output Analytical Tables 2023 (published 2025).
#   Oil (CPA_B):       £25,313m / £37,016m = 0.684
#   Petrochem (C20B):  £2,171m  / £9,738m  = 0.223
#   Textiles (C13):    £3,514m  / £7,347m  = 0.478
#   Apparel (C14):     £1,801m  / £3,266m  = 0.552
#   Wholesale (G46):   £113,354m/ £214,742m= 0.528
#   Retail (G47):      £104,392m/ £174,593m= 0.598
# PTA and PET are sub-sectors of C20; rates interpolated from ICIS cost structures.
GVA_RATE = {
    "Oil_Extraction":      0.684,  # ONS CPA_B
    "Chemical_Processing": 0.223,  # ONS C20B (petrochem)
    "PTA_Production":      0.190,  # C20B adjusted: more capital/input-intensive
    "PET_Resin_Yarn":      0.210,  # C20B adjusted: polymerisation margin
    "Fabric_Weaving":      0.478,  # ONS C13
    "Garment_Assembly":    0.552,  # ONS C14
    "UK_Wholesale":        0.528,  # ONS G46
    "UK_Retail":           0.598,  # ONS G47
}

# ── Labour share in value-added (α_L) ────────────────────────────────────────
# Fraction of sectoral GVA paid as labour compensation (wages + employer NIC).
# Primary source: GTAP v10 factor share database — Hertel et al. (2012).
# Cross-checked against ONS Annual Business Survey 2023 (employee costs / GVA).
#   GTAP "oil"  α_L ≈ 0.12   |  ONS CPA_B:  employee costs / GVA ≈ 0.11
#   GTAP "crp"  α_L ≈ 0.26   |  ONS C20B:   employee costs / GVA ≈ 0.28
#   GTAP "tex"  α_L ≈ 0.46   |  ONS C13:    employee costs / GVA ≈ 0.44
#   GTAP "wap"  α_L ≈ 0.69   |  ONS C14:    employee costs / GVA ≈ 0.65
#   GTAP "trd"  α_L ≈ 0.58   |  ONS G46/47: employee costs / GVA ≈ 0.55–0.62
LABOUR_SHARE_IN_VA = {
    "Oil_Extraction":      0.12,  # GTAP "oil";  ONS CPA_B ≈ 0.11
    "Chemical_Processing": 0.26,  # GTAP "crp";  ONS C20B  ≈ 0.28
    "PTA_Production":      0.22,  # GTAP "crp" adjusted: more automated
    "PET_Resin_Yarn":      0.28,  # GTAP "crp" adjusted: slightly more labour
    "Fabric_Weaving":      0.46,  # GTAP "tex";  ONS C13   ≈ 0.44
    "Garment_Assembly":    0.69,  # GTAP "wap";  ONS C14   ≈ 0.65
    "UK_Wholesale":        0.55,  # GTAP "trd";  ONS G46   ≈ 0.55
    "UK_Retail":           0.62,  # GTAP "trd";  ONS G47   ≈ 0.62
}

# ── Capital-labour substitution elasticity in value-added (σ_VA) ──────────────
# CES elasticity of substitution between labour and capital in the VA nest.
# Source: GTAP v10 parameter database — Hertel et al. (2012).
VA_ELASTICITY = {
    "Oil_Extraction":      0.80,  # GTAP "oil"  — limited short-run substitution
    "Chemical_Processing": 1.26,  # GTAP "crp"
    "PTA_Production":      1.26,  # GTAP "crp"  — same technology class
    "PET_Resin_Yarn":      1.26,  # GTAP "crp"
    "Fabric_Weaving":      1.26,  # GTAP "tex"
    "Garment_Assembly":    1.40,  # GTAP "wap"  — most flexible (labour-intensive)
    "UK_Wholesale":        1.20,  # GTAP "trd" approx.
    "UK_Retail":           1.20,  # GTAP "trd" approx.
}

# ── Armington substitution elasticities ──────────────────────────────────────
# σ_m = import substitution elasticity (CES Armington aggregation).
# Sources:
#   GTAP v10 database — Hertel, T.W. et al. (2012) Global Trade Analysis.
#     "oil"  sector σ_m = 5.2  → Oil_Extraction
#     "crp"  sector σ_m = 3.65 → Chemical_Processing (chemicals, rubber, plastics)
#     "tex"  sector σ_m = 3.2  → Fabric_Weaving (textiles)
#     "wap"  sector σ_m = 3.3  → Garment_Assembly (wearing apparel)
#   PTA and PET below GTAP "crp" (3.65) because these are specific, concentrated
#   intermediates with high switching costs and long-term supply contracts.
ARMINGTON_ELASTICITY = {
    "Oil_Extraction":      5.20,  # GTAP v10 "oil" sector — Hertel et al. 2012
    "Chemical_Processing": 3.65,  # GTAP v10 "crp" sector — Hertel et al. 2012
    "PTA_Production":      1.20,  # below crp: China 67% share, high switching cost
    "PET_Resin_Yarn":      1.50,  # estimated; slightly above PTA (more producers)
    "Fabric_Weaving":      3.20,  # GTAP v10 "tex" sector — Hertel et al. 2012
    "Garment_Assembly":    3.30,  # GTAP v10 "wap" sector — Hertel et al. 2012
    "UK_Wholesale":        3.50,  # estimated; analogous to retail, slight discount
    "UK_Retail":           4.00,  # estimated; high consumer substitutability
}

# ── Safety stock targets (weeks of demand) — calibrated from inventory data ───
# MEG inventory 688 kt at ports; estimated consumption rate → ~3 weeks
SAFETY_STOCK_WEEKS = {
    "Oil_Extraction":     4.0,
    "Chemical_Processing": 3.0,
    "PTA_Production":     2.5,
    "PET_Resin_Yarn":     3.0,
    "Fabric_Weaving":     4.0,
    "Garment_Assembly":   6.0,
    "UK_Wholesale":       8.0,
    "UK_Retail":         10.0,
}

# ── HMRC Time Series 2002–2024 (REAL — OTS API, downloaded 2026-04-17) ────────
# Source: HMRC UK Trade Info OTS API, 29 HS6 codes (synthetic apparel, HS61+62),
#         EU+Non-EU imports, all countries, aggregated annually.
# Cross-check: 2023 total £2,392.8m vs xlsx £2,388.9m (+0.16%) — match confirmed.

HMRC_ANNUAL_TOTALS_GBP = {
    2002: 1_332_472_629, 2003: 1_383_242_465, 2004: 1_407_338_106,
    2005: 1_326_050_473, 2006: 1_345_796_518, 2007: 1_411_214_840,
    2008: 1_446_503_709, 2009: 1_562_626_777, 2010: 1_743_288_980,
    2011: 1_969_043_325, 2012: 2_071_579_444, 2013: 2_284_656_356,
    2014: 2_334_346_176, 2015: 2_404_269_269, 2016: 2_408_042_300,
    2017: 2_497_344_226, 2018: 2_498_384_504, 2019: 2_705_627_088,
    2020: 1_961_631_666, 2021: 1_872_001_847, 2022: 2_776_580_913,
    2023: 2_392_841_303, 2024: 2_224_028_201,
}

# Annual UK synthetic apparel imports by country (£ value). REAL — HMRC OTS API.
HMRC_ANNUAL_BY_COUNTRY_GBP = {
    2019: {"China": 655_350_091, "Bangladesh": 221_549_074, "Turkey": 151_232_131,
           "India": 86_325_926,  "Vietnam": 142_308_534, "Italy": 123_683_942,
           "Cambodia": 102_614_402, "Sri_Lanka": 101_837_481, "Pakistan": 51_957_398,
           "Myanmar": 48_004_061},
    2020: {"China": 477_046_866, "Bangladesh": 160_590_945, "Turkey": 110_402_613,
           "India": 57_443_275,  "Vietnam": 77_574_947,  "Italy": 97_170_623,
           "Cambodia": 66_442_097, "Sri_Lanka": 68_801_703, "Pakistan": 54_245_833,
           "Myanmar": 32_805_772},
    2021: {"China": 538_598_961, "Bangladesh": 167_499_091, "Turkey": 130_437_973,
           "India": 71_614_063,  "Vietnam": 69_036_191,  "Italy": 102_249_977,
           "Cambodia": 52_667_958, "Sri_Lanka": 55_883_180, "Pakistan": 70_502_435,
           "Myanmar": 31_823_134},
    2022: {"China": 791_528_535, "Bangladesh": 304_573_217, "Turkey": 189_902_768,
           "India": 108_581_102, "Vietnam": 139_013_991, "Italy": 114_359_269,
           "Cambodia": 91_677_447, "Sri_Lanka": 85_441_960, "Pakistan": 68_340_044,
           "Myanmar": 60_597_935},
    2023: {"China": 653_175_775, "Bangladesh": 287_422_073, "Turkey": 144_292_001,
           "India": 87_906_752,  "Vietnam": 117_739_010, "Italy": 102_188_834,
           "Cambodia": 79_325_931, "Sri_Lanka": 65_106_449, "Pakistan": 63_293_110,
           "Myanmar": 51_248_724},
    2024: {"China": 661_476_437, "Bangladesh": 251_156_706, "Turkey": 113_707_176,
           "India": 79_163_245,  "Vietnam": 101_020_815, "Italy": 84_297_328,
           "Cambodia": 95_963_373, "Sri_Lanka": 58_615_252, "Pakistan": 68_259_854,
           "Myanmar": 30_122_867},
}

# China unit price series (£/kg). REAL — HMRC OTS API (Value / NetMass).
HMRC_CHINA_UNIT_PRICE_GBP_PER_KG = {
    2002: 9.16,  2003: 8.68,  2004: 8.06,  2005: 7.74,  2006: 8.10,
    2007: 7.80,  2008: 9.36,  2009: 11.12, 2010: 11.69, 2011: 12.64,
    2012: 12.32, 2013: 12.08, 2014: 10.75, 2015: 10.59, 2016: 10.28,
    2017: 10.11, 2018: 14.99, 2019: 15.39, 2020: 15.65, 2021: 14.99,
    2022: 19.25, 2023: 17.46, 2024: 16.96,
}

# Monthly seasonal demand factors for NON-EU imports (Jan–Dec), relative to
# annual mean. REAL — HMRC OTS API average across 2002–2024.
# Peak: October (1.145), trough: December (0.871).
HMRC_MONTHLY_SEASONAL_FACTORS = [
    0.993,  # Jan
    0.909,  # Feb
    1.026,  # Mar
    0.941,  # Apr
    0.963,  # May
    0.963,  # Jun
    1.052,  # Jul
    1.062,  # Aug
    1.099,  # Sep
    1.145,  # Oct
    0.977,  # Nov
    0.871,  # Dec
]

# Key validation-event HMRC benchmarks (REAL — directly from OTS API data)
HMRC_VALIDATION_BENCHMARKS = {
    "V1_COVID_china_value_pct":   -27.2,  # China: 2020 vs 2019
    "V1_COVID_china_volume_pct":  -28.4,  # China volume (kg): 2020 vs 2019
    "V1_COVID_total_value_pct":   -27.5,  # All-country: 2020 vs 2019
    "V5_RedSea_jan_value_pct":    -21.4,  # NON-EU: Jan 2024 vs Jan 2023
    "V5_RedSea_feb_value_pct":    -26.3,  # NON-EU: Feb 2024 vs Feb 2023
    "V5_RedSea_mar_value_pct":    -24.7,  # NON-EU: Mar 2024 vs Mar 2023
    "V5_RedSea_H1_value_pct":     -15.6,  # NON-EU: H1 2024 vs H1 2023
    "V5_RedSea_annual_value_pct":  -7.1,  # All-country: 2024 vs 2023
    "V6_Shanghai_Q2_china_value_pct": +60.6,  # China Q2 2022 vs Q2 2021 (price-driven)
    "V6_Shanghai_Q2_china_vol_pct":   +35.8,  # China Q2 2022 volume vs Q2 2021
    "V7_Ukraine_annual_value_pct":    +48.3,  # All-country: 2022 vs 2021 (price inflation)
}
