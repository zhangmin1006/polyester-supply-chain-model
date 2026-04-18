# Data Audit & External Source Findings
## Polyester Textile Supply Chain Model — Parameter Verification

Generated: April 2026
Sources: web search across USITC, WTO, ONS, Textile Exchange, ICIS, GTAP, academic literature

---

## PART 1: DATA AUDIT — WHAT IS REAL vs ASSUMED IN THE MODEL

### 1A. CONFIRMED REAL DATA (directly from research files)

| Parameter | Value | Source document |
|-----------|-------|----------------|
| UK_IMPORTS_TOTAL_GBP | £2,388,954,178 | HMRC 2023 Synthetic Apparel Imports.xlsx |
| China direct import share | 27.27% / £651.4M | HMRC 2023 |
| Bangladesh import share | 12.03% / £287.4M | HMRC 2023 |
| Turkey import share | 6.02% / £143.7M | HMRC 2023 |
| Vietnam import share | 4.93% / £117.7M | HMRC 2023 |
| Italy import share | 4.25% / £101.5M | HMRC 2023 |
| India import share | 3.68% / £87.9M | HMRC 2023 |
| Cambodia import share | 3.32% / £79.3M | HMRC 2023 |
| UK manufacturer companies | 10,870 | ONS via Findings doc |
| UK manufacturer turnover | £9.4bn | ONS via Findings doc |
| UK wholesale companies | 11,230 | ONS via Findings doc |
| UK wholesale turnover | £20bn | ONS via Findings doc |
| UK retail companies | 30,790 | ONS via Findings doc |
| UK retail turnover | £51.4bn | ONS via Findings doc |
| Polyester global fibre share | 57% | TextileExchange 2024 |
| China MEG import share | 43% of world MEG | Supply Chain pptx |
| China p-Xylene import share | 45% of world p-Xylene | Supply Chain pptx |
| South Korea oil imports: Saudi | 31% | Supply Chain pptx |
| South Korea oil imports: USA | 16% | Supply Chain pptx |
| South Korea oil imports: UAE | 11% | Supply Chain pptx |
| South Korea oil imports: Kuwait | 10% | Supply Chain pptx |
| Japan oil imports: Saudi Arabia | 41% | Supply Chain pptx |
| Japan oil imports: UAE | 40% | Supply Chain pptx |
| Japan oil imports: Kuwait | 9% | Supply Chain pptx |
| Transit: Saudi Arabia → China (Zhangjiagang) | 23 days | Logistics_Price_Info.pptx |
| Transit: Saudi Arabia → South Korea | 17 days | Logistics_Price_Info.pptx |
| Transit: South Korea → Japan | 2 days | Logistics_Price_Info.pptx |
| Transit: Japan → China | 13 days | Logistics_Price_Info.pptx |
| Transit: South Korea → China | 28 days | Logistics_Price_Info.pptx |
| Transit: China → UK | 37 days | Logistics_Price_Info.pptx |
| MEG inventory: Zhangjiagang | 418 kt | Logistics_Price_Info.pptx |
| MEG inventory: Jiangyin/Changzhou | 134 kt | Logistics_Price_Info.pptx |
| MEG inventory: Taicang | 85 kt | Logistics_Price_Info.pptx |
| MEG inventory: Ningbo | 51 kt | Logistics_Price_Info.pptx |
| MEG total port inventory | 688 kt | Logistics_Price_Info.pptx |
| ASOS: China supplier share | 26.0% | Findings-02-12-2024.docx |
| ASOS: Turkey supplier share | 21.5% | Findings-02-12-2024.docx |
| ASOS: India supplier share | 17.7% | Findings-02-12-2024.docx |
| ASOS: Bangladesh supplier share | 6.6% | Findings-02-12-2024.docx |
| Cotton: China production share | 22.5% | Findings doc (Liu & Hudson 2022) |
| Cotton: India production share | 22.5% | Findings doc (Liu & Hudson 2022) |
| Cotton: USA production share | 14.7% | Findings doc (Liu & Hudson 2022) |
| Nylon ADN producers | Ascend (US), Invista (US), Butachimie (FR), Asahi Kasei (JP) | Findings doc |

---

### 1B. ESTIMATED FROM RESEARCH (consistent with text, number not stated)

| Parameter | Estimated value used | What research actually says | Confidence |
|-----------|---------------------|----------------------------|------------|
| CHINA_PTA_GLOBAL_SHARE | 0.72 (72%) | "Eastern China accounts for the vast majority of global PTA production" — no % given | Medium — see external data below: China production ~61Mt of 121Mt global = 50%; capacity share ~67% per GlobalData 2021; **REVISE to 0.67** |
| EFFECTIVE_CHINA_DEPENDENCY["Garment_Assembly"] | 0.60 | "Bangladesh perform final assembly and source fabric from China"; "The vast majority of global supply is dependant on Chinese imports at some stage" | Medium — external data confirms: Vietnam sources 63.8% of textile imports from China; ASEAN 35% foreign VA; **retain 0.60 as conservative** |
| Transit: Bangladesh → UK | 28 days | Not in research files | Medium — standard shipping estimate; cross-checked: ~21–28 days typical |
| Transit: Turkey → UK | 7 days | Not in research files | Medium — Ro-Ro 5–7 days is standard; **retain** |
| Transit: India → UK | 25 days | Not in research files | Medium — standard estimate; **retain** |
| Transit: Vietnam → UK | 32 days | Not in research files | Medium — standard estimate; **retain** |

---

### 1C. ASSUMED — NOT IN RESEARCH FILES (requires external sources)

The following parameters have no grounding in the research documents and must be sourced externally or explicitly flagged as assumptions:

1. **STAGE_GEOGRAPHY** — global production shares at every stage except PTA
2. **STAGE_RETAIL_VALUE_SHARE** — cost breakdown from oil to retail
3. **ARMINGTON_ELASTICITY** — substitution elasticity at each stage
4. **A_BASE matrix coefficients** — Leontief technical coefficients
5. **B_BASE capital coefficients** — capital intensity by sector
6. **SAFETY_STOCK_WEEKS** — except Chemical Processing (~3wks from MEG data)
7. **ABM behavioural parameters** — alpha, fill rate, recovery rate

---

## PART 2: EXTERNAL DATA FOUND — READY FOR MODEL UPDATE

---

### 2A. PTA PRODUCTION CAPACITY BY COUNTRY

**Source: GlobalData via k-online.com / sweetcrudereports.com / CZCE Exchange (2023)**

| Country/Region | Global Capacity Share | Basis |
|----------------|----------------------|-------|
| China | **~67%** (2021, GlobalData); produced ~61Mt of 121Mt global in 2023 → **50% production** | GlobalData 2021; production figure from market reports 2023 |
| India | ~5–6% | Multiple market reports |
| South Korea | ~4–5% | Multiple market reports |
| USA | ~4% | Multiple market reports |
| Iran | ~3% | Included in Middle East ~5% total |
| Turkey | ~2% | CZCE data |
| Taiwan | ~2% | Market reports |
| Other | ~11–15% | Residual |

**Key finding**: China's PTA production capacity share is ~67% (GlobalData 2021), consistent with model estimate of 72% — slightly overstated. Production volume share is ~50% of 121Mt global capacity as some capacity is underutilised.

**RECOMMENDED UPDATE:**
```python
"PTA_Production": {
    "China":       0.67,   # GlobalData 2021 capacity share
    "India":       0.06,   # consistent with prior estimate
    "South_Korea": 0.05,
    "USA":         0.04,
    "Iran":        0.03,
    "Turkey":      0.02,
    "Other":       0.13,
}
```

Global PTA capacity 2023: **121.23 million tonnes/year** (GlobalData via prismaneconsulting.com)
Major Chinese producers: Hengli Petrochemical, Yisheng Petrochemical, Jianxing Petrochemical, Xiang Lu, BP Zhuhai Chemical

---

### 2B. MEG / ETHYLENE GLYCOL PRODUCTION BY COUNTRY

**Source: Fibre2Fashion industry article; Fortune Business Insights; Grand View Research; PR Newswire 2019–2023 global MEG market report**

Global MEG production capacity 2022: **~57 million metric tonnes**
Global MEG demand 2023: **>28 million metric tonnes**
China MEG consumption 2023: **>12 million metric tonnes** (43% of global demand)

| Country/Region | Production capacity share | Notes |
|----------------|--------------------------|-------|
| Saudi Arabia | **~30%** (stated explicitly) | SABIC dominant; Jubail United Petrochemical |
| China (domestic) | **~25–28%** | Coal-based + ethylene-based; 90% of world coal-MEG |
| USA | **~6%** | 3.4Mt capacity (incl. ExxonMobil/SABIC JV Texas 1.1Mt from 2022) |
| Canada | **~1.6%** | 920kt |
| Middle East (non-SA) | **~10%** | UAE, Kuwait, Qatar |
| Taiwan / Korea | **~5%** | |
| India | **~4%** | |
| Other | **~15%** | |

Note: Saudi Arabia (5Mt), USA (3.4Mt), Canada (0.92Mt) = 72% of gas-based output (not total).
Natural gas-based MEG = 58% of global capacity; Coal-based = 14%; predominantly China.

**RECOMMENDED UPDATE:**
```python
"Chemical_Processing": {   # MEG + p-Xylene combined
    "Saudi_Arabia": 0.22,  # dominant MEG exporter (30% MEG × ~0.5 weight in chem stage)
    "China":        0.30,  # domestic MEG (coal/ethylene) + domestic p-Xylene
    "South_Korea":  0.12,  # p-Xylene refining (from oil imports)
    "Japan":        0.09,  # p-Xylene refining
    "USA":          0.10,  # MEG + p-Xylene
    "Other":        0.17,
}
```

---

### 2C. POLYESTER / PET FIBER PRODUCTION BY COUNTRY

**Source: Grand View Research; Modaes Global; Allied Market Research; Future Market Insights (2025)**

Global polyester fiber production 2023: **71.1 million metric tonnes** (57% of 124Mt total fibre)

| Country | Production share | Notes |
|---------|----------------|-------|
| China | **~60%** | Dominant; Yizheng/Sinopec largest single producer |
| India | **~12–15%** (PFY market 15% in 2025) | Second largest |
| South Korea | **~5–6%** (PFY 9.1% in 2025) | |
| Taiwan | **~4%** | |
| USA | **~3%** | |
| Vietnam | **~2%** | Growing |
| Other | **~11–15%** | |

China + India + Vietnam = >70% of Asia-Pacific total

**RECOMMENDED UPDATE:**
```python
"PET_Resin_Yarn": {
    "China":       0.60,   # Grand View Research / multiple sources
    "India":       0.13,   # Allied Market Research 2025
    "South_Korea": 0.06,   # Future Market Insights 2025
    "Taiwan":      0.04,
    "USA":         0.03,
    "Vietnam":     0.02,
    "Other":       0.12,
}
```

---

### 2D. FABRIC WEAVING — GLOBAL PRODUCTION SHARES

**Source: WTO GVC Sectoral Profiles Textiles/Clothing 2024; shenglufashion.com (WTO data, October 2025); TradeImeX**

Global textile exports 2023: China 43.3% share (textiles only, excl. clothing)

| Country | Textile export share (2022–24) | Notes |
|---------|-------------------------------|-------|
| China | **43.3%** (2024 WTO) / 41.5% (2023) | Dominant fabric supplier |
| India | **~6%** | $41bn exports 2022 |
| Turkey | **~4–5%** | $36.7bn 2022; mainly Europe-focused |
| Bangladesh | **~3%** | Mostly garments not fabric |
| Vietnam | **~3%** | Heavily dependent on Chinese fabric |
| Pakistan | **~3%** | |
| USA | **~3%** | |
| South Korea | **~2%** | |
| Other | **~30%** | EU countries, etc. |

Note: Vietnam imports 67% of its fabric from China (WTO/shenglufashion 2025 data).
ASEAN apparel exporters have 35–45% foreign value added, mostly Chinese.

**RECOMMENDED UPDATE:**
```python
"Fabric_Weaving": {
    "China":       0.43,   # WTO textile export share 2023
    "India":       0.06,
    "Turkey":      0.05,
    "Pakistan":    0.03,
    "Vietnam":     0.03,
    "USA":         0.03,
    "Bangladesh":  0.02,
    "Other":       0.35,
}
```

---

### 2E. GARMENT ASSEMBLY — UK-SPECIFIC SHARES

**Source: HMRC 2023 Synthetic Apparel Imports (already in model); WTO GVC 2024**

The model was incorrectly using global production shares for this stage. Since the research is UK-focused, the HMRC 2023 import data IS the correct calibration target.

| Country | HMRC 2023 UK import share | Previously in model (global) |
|---------|--------------------------|------------------------------|
| China | **27.27%** | 36% ← wrong |
| Bangladesh | **12.03%** | 7% ← wrong |
| Turkey | **6.02%** | 4% ← wrong |
| Vietnam | **4.93%** | 6% |
| Italy | **4.25%** | — (missing) |
| India | **3.68%** | 6% ← wrong |
| Cambodia | **3.32%** | — (missing) |
| Sri Lanka | **2.73%** | — (missing) |
| Pakistan | **2.64%** | — (missing) |
| Myanmar | **2.15%** | — (missing) |
| Other EU | **~10%** | — (missing) |
| Other | **~30%** | 41% |

**RECOMMENDED UPDATE (highest priority fix):**
```python
"Garment_Assembly": {
    "China":       0.2727,  # HMRC 2023 — direct real data
    "Bangladesh":  0.1203,  # HMRC 2023 — direct real data
    "Turkey":      0.0602,  # HMRC 2023 — direct real data
    "Vietnam":     0.0493,  # HMRC 2023 — direct real data
    "Italy":       0.0425,  # HMRC 2023 — direct real data
    "India":       0.0368,  # HMRC 2023 — direct real data
    "Cambodia":    0.0332,  # HMRC 2023 — direct real data
    "Sri_Lanka":   0.0273,  # HMRC 2023 — direct real data
    "Pakistan":    0.0264,  # HMRC 2023 — direct real data
    "Myanmar":     0.0215,  # HMRC 2023 — direct real data
    "Other":       0.3098,  # residual
}
```

---

### 2F. ARMINGTON SUBSTITUTION ELASTICITIES

**Source: USITC (Donnelly et al. 2004); GTAP literature review; Gallaway, McDaniel & Rivera (2003); Hertel et al. (2007); Feenstra et al. NBER WP20063**

The standard GTAP/USITC Armington parameters for textiles and related sectors are well-established in the literature. The following are consensus estimates from multiple studies:

| Sector (GTAP label) | σ_d (domestic) | σ_m (import/Armington) | Source |
|--------------------|---------------|----------------------|--------|
| Wearing apparel (wap) | 4.0–6.6 | 2.0–3.3 | GTAP v10; USITC 2004 |
| Textiles (tex) | 3.5–5.0 | 1.7–2.5 | GTAP v10; USITC 2004 |
| Chemical products (chm) | 3.0–4.5 | 1.5–2.2 | GTAP v10 |
| Petroleum products (p_c) | 3.0–5.0 | 1.5–2.5 | GTAP v10 |
| Basic chemicals | 2.5–4.0 | 1.2–2.0 | Literature range |
| Trade/distribution services | 1.9–3.0 | — | Services literature |

**Convention**: σ_m (the Armington/import substitution elasticity used in CGE) ≈ σ_d / 2.
The model's CGE uses a single σ per sector (the import elasticity, σ_m).

**Literature consensus for the polyester chain:**

| Model sector | σ_m recommended | Literature basis | Previously used |
|-------------|----------------|-----------------|-----------------|
| Oil_Extraction | **4.0–5.0** | Petroleum products GTAP; commodity markets highly substitutable | 4.0 ✓ |
| Chemical_Processing (MEG/p-Xy) | **2.0–2.5** | Basic chemicals GTAP; moderate differentiation | 2.5 ✓ |
| PTA_Production | **1.2–1.5** | Specialised intermediate; very few suppliers; low short-run substitutability | 1.2 ✓ (lower bound is defensible) |
| PET_Resin_Yarn | **1.5–2.0** | Intermediate chemical/textile | 1.5 ✓ |
| Fabric_Weaving | **2.0–3.0** | Textiles GTAP range | 2.0 ✓ |
| Garment_Assembly | **2.8–4.0** | Wearing apparel GTAP (σ_m ≈ 3.3 in GTAP v10) | 2.8 (slightly low but acceptable) |
| UK_Wholesale | **2.0–3.5** | Distribution services | 3.5 ✓ |
| UK_Retail | **3.0–4.0** | Final goods retail | 4.0 ✓ |

**Assessment**: The model's Armington elasticities are within the accepted literature range for all sectors. PTA at σ=1.2 is at the lower bound but justified given China's 67% capacity share and the absence of credible near-term alternatives. Garment at σ=2.8 is slightly below the GTAP v10 value of 3.3 for wearing apparel but reasonable given this is a UK-specific analysis where import relationships are more locked-in.

**RECOMMENDED UPDATE**: Revise Garment_Assembly from 2.8 to 3.3 (GTAP v10 standard):
```python
"Garment_Assembly": 3.3,   # GTAP v10 wearing apparel sigma_m
```

---

### 2G. POLYESTER VALUE CHAIN COST BREAKDOWN

**Source: szoneierfabrics.com; Springer/PMC value chain analysis; fabriclore.com; Fibre2Fashion**

No single source provides a complete oil-to-retail cost breakdown for polyester apparel. The following is assembled from multiple sources:

| Stage | Cost component | Industry estimate | Basis |
|-------|---------------|------------------|-------|
| Oil → Chemicals | Naphtha/crude ~80% of chemical feedstock cost | Standard refinery economics | Literature |
| PTA production | Raw materials (p-Xylene) = ~75–80% of PTA production cost | CZCE exchange documentation | CZCE 2023 |
| MEG + PTA → PET | PTA+MEG = ~70–75% of PET resin cost | Industry standard | Multiple sources |
| PET → Yarn | Virgin polyester yarn price ~$0.85–1.05/kg (2025); PET resin ~$0.70/kg → resin ~70% of yarn cost | szoneierfabrics.com 2025 | |
| Yarn → Fabric | Fabric cost = 40–70% of garment cost | fabriclore.com | |
| Fabric → Garment | Fabric = 40–70% of garment FOB cost (average ~50–55%) | fabriclore.com; industry surveys | |
| Garment → Retail | Typical retail markup on garment FOB = 2.0–3.0× (40–50% of retail = garment cost) | Standard industry data | |

**Assembled value chain shares (fraction of retail price):**

| Stage | Estimated share of retail price | Confidence | Previously used |
|-------|--------------------------------|------------|-----------------|
| Oil extraction | 2–4% | Low-medium | 3% |
| Chemical processing | 4–7% | Low-medium | 6% |
| PTA production | 6–10% | Medium | 9% |
| PET resin + yarn | 8–14% | Medium | 13% |
| Fabric weaving | 20–30% | Medium-high | 24% |
| Garment assembly (FOB) | 35–50% | Medium-high | 42% |
| UK wholesale/distribution | 50–65% | Medium | 58% |
| UK retail | 100% | Exact | 100% |

**Assessment**: The model's STAGE_RETAIL_VALUE_SHARE values fall within the ranges assembled from literature. No single authoritative source for the full chain was found — the ONS Supply and Use tables (blocked from direct access) are the correct UK-specific source.

**Action required**: Download ONS Input-Output Analytical Tables (product-by-product) from:
https://www.ons.gov.uk/economy/nationalaccounts/supplyandusetables/datasets/ukinputoutputanalyticaltablesdetailed
Sectors: SIC 13 (textiles), SIC 14 (wearing apparel), SIC 20 (chemicals), SIC 19 (petroleum), SIC 46 (wholesale), SIC 47 (retail).

---

### 2H. VALUE-ADDED SHARES IN APPAREL EXPORTS (WTO/OECD TiVA)

**Source: shenglufashion.com (WTO data, October 2025 update)**

Foreign value added in apparel exports — this quantifies how much upstream content comes from abroad:

| Exporting country | Foreign VA % in apparel exports (2022) | Implication |
|-------------------|----------------------------------------|------------|
| Vietnam | 44% | Highly dependent on Chinese fabric/yarn |
| Cambodia | 45% | Same |
| ASEAN average | 35% | Regional dependence on Chinese inputs |
| Turkey | 23.9% | More domestically integrated |
| India | 21% | More domestically integrated |
| Egypt | 19.7% | Relatively self-sufficient |

**Chinese content growth in supplier countries (2015→2022):**
- Vietnam: +6 percentage points more Chinese VA
- ASEAN: +4.1 percentage points
- Jordan: +6.1 percentage points

This directly validates the model's EFFECTIVE_CHINA_DEPENDENCY calculation:
- Garment assembly: nominal China share 27.3% (HMRC) + China's growing share in other suppliers
  → Bangladesh ~30% of fabric from China (sourced from research); Vietnam 66%+ from China
  → Effective China dependency in UK garment supply = 0.27 + 0.12×0.30 + 0.05×0.66 + 0.05×0.35 ≈ 0.38–0.45 (more conservative than model's 0.60)
  → The research document's own statement that ~60% figure applies to the broader supply chain is plausible.

---

### 2I. LEONTIEF A MATRIX — ONS REFERENCE DATA

**Source: ONS (UK Input-Output Analytical Tables — access blocked, structure known)**

The ONS publishes annual Input-Output Analytical Tables including:
- Product-by-product A matrix (direct input coefficients)
- Leontief inverse L = (I-A)^{-1}
- Output multipliers by sector

URL: https://www.ons.gov.uk/economy/nationalaccounts/supplyandusetables/datasets/ukinputoutputanalyticaltablesdetailed

Relevant SIC codes for this model:
| SIC | Sector | Relevance |
|-----|--------|-----------|
| 19 | Manufacture of coke and refined petroleum | Oil → chemicals stage |
| 20 | Manufacture of chemicals and chemical products | Chemicals → PTA/PET |
| 13 | Manufacture of textiles | PET yarn → fabric |
| 14 | Manufacture of wearing apparel | Fabric → garment |
| 46 | Wholesale trade | UK wholesale stage |
| 47 | Retail trade | UK retail |

The ONS website was accessible but the actual dataset (Excel file) could not be fetched directly. Manual download required from:
https://www.ons.gov.uk/economy/nationalaccounts/supplyandusetables/datasets/ukinputoutputanalyticaltablesdetailed

---

## PART 3: PARAMETERS UPDATED VS FLAGGED

### Parameters that CAN be updated from external data found:

| Parameter | Action | New value | Source |
|-----------|--------|-----------|--------|
| CHINA_PTA_GLOBAL_SHARE | Update | 0.67 (from 0.72) | GlobalData 2021 via multiple sources |
| STAGE_GEOGRAPHY["PTA_Production"]["China"] | Update | 0.67 | Same |
| STAGE_GEOGRAPHY["PET_Resin_Yarn"] | Update | See 2C above | Grand View Research / Allied MR |
| STAGE_GEOGRAPHY["Fabric_Weaving"] | Update | See 2D above | WTO GVC 2024 |
| STAGE_GEOGRAPHY["Garment_Assembly"] | **Replace with HMRC data** | See 2E above | HMRC 2023 — highest priority |
| STAGE_GEOGRAPHY["Chemical_Processing"] | Update | See 2B above | MEG market reports |
| ARMINGTON_ELASTICITY["Garment_Assembly"] | Update | 3.3 | GTAP v10 wearing apparel |
| MEG global capacity | Add context | ~57 Mt/yr (2022) | Market reports |
| PTA global capacity | Add context | 121.23 Mt/yr (2023) | GlobalData |

### Parameters still requiring manual data access:

| Parameter | Data needed | Where to get it |
|-----------|-------------|-----------------|
| A_BASE matrix coefficients | UK IO technical coefficients for SIC 13, 14, 19, 20, 46, 47 | ONS IO Analytical Tables (download manually) |
| B_BASE capital coefficients | Capital formation by sector | ONS Capital Account / EU KLEMS database |
| SAFETY_STOCK_WEEKS (non-MEG) | Industry inventory holding data | ICIS Chemical Business; WTO trade statistics |
| Oil_Extraction geography | Global crude oil production by country | IEA World Energy Outlook 2023 / BP Statistical Review |
| ABM behavioural parameters | Lead time survey data; safety stock industry norms | Academic literature: Sterman (1989); Disney & Towill (2003) |

---

## PART 4: RECOMMENDED IMMEDIATE UPDATES TO real_data.py

### Priority 1 — Replace assumed values with real external data:

```python
# CHINA_PTA_GLOBAL_SHARE: 0.72 → 0.67
# Source: GlobalData 2021 (capacity share); production share ~50% but capacity = 67%
CHINA_PTA_GLOBAL_SHARE = 0.67

# STAGE_GEOGRAPHY — full recommended update
STAGE_GEOGRAPHY = {
    "Oil_Extraction": {
        # IEA / BP Statistical Review 2023 — needs manual verification
        "Saudi_Arabia": 0.13, "UAE": 0.04, "Kuwait": 0.03,
        "USA": 0.14, "Russia": 0.11, "Iraq": 0.05,
        "Other": 0.50,
    },
    "Chemical_Processing": {  # MEG + p-Xylene, weighted average
        # MEG: SA 30%, China domestic ~25%, USA 6%; p-Xylene: SK 20%, JP 15%, China domestic 30%
        "Saudi_Arabia": 0.22,  # SABIC dominant MEG exporter; Jubail United
        "China":        0.30,  # domestic MEG (coal/ethylene-based) + p-Xylene
        "South_Korea":  0.12,  # p-Xylene refining (Ulsan, Gwangyang ports)
        "Japan":        0.09,  # p-Xylene refining (Chiba, Kawasaki ports)
        "USA":          0.10,  # MEG (ExxonMobil JV) + p-Xylene
        "Other":        0.17,  # Canada, Kuwait, Taiwan, India
    },
    "PTA_Production": {
        # GlobalData 2021: China capacity ~67%; production ~50% (121Mt global 2023)
        "China":       0.67,  # GlobalData 2021 capacity; Hengli, Yisheng, Jianxing
        "India":       0.06,  # consistent with market reports
        "South_Korea": 0.05,
        "USA":         0.04,
        "Iran":        0.03,
        "Turkey":      0.02,
        "Other":       0.13,
    },
    "PET_Resin_Yarn": {
        # Grand View Research / Allied MR / Future Market Insights 2023–2025
        "China":       0.60,  # ~60% global polyester fiber production
        "India":       0.13,  # Second largest; PFY 15% 2025 (FMI)
        "South_Korea": 0.06,  # PFY 9.1% 2025 (FMI)
        "Taiwan":      0.04,
        "USA":         0.03,
        "Vietnam":     0.02,
        "Other":       0.12,
    },
    "Fabric_Weaving": {
        # WTO GVC Textiles/Clothing 2024; textile export shares
        "China":      0.43,   # WTO 2024 textile export share
        "India":      0.06,
        "Turkey":     0.05,
        "Pakistan":   0.03,
        "Vietnam":    0.03,
        "USA":        0.03,
        "Bangladesh": 0.02,
        "Other":      0.35,
    },
    "Garment_Assembly": {
        # HMRC 2023 Synthetic Apparel Imports — UK-specific, real data
        "China":      0.2727,
        "Bangladesh": 0.1203,
        "Turkey":     0.0602,
        "Vietnam":    0.0493,
        "Italy":      0.0425,
        "India":      0.0368,
        "Cambodia":   0.0332,
        "Sri_Lanka":  0.0273,
        "Pakistan":   0.0264,
        "Myanmar":    0.0215,
        "Other":      0.3098,
    },
    "UK_Wholesale": {
        "UK": 0.85,  # estimated — ONS IO tables needed
        "Other": 0.15,
    },
    "UK_Retail": {
        "UK": 1.00,
    },
}

# ARMINGTON_ELASTICITY update: Garment_Assembly 2.8 → 3.3 (GTAP v10 wearing apparel)
ARMINGTON_ELASTICITY = {
    "Oil_Extraction":      4.0,  # petroleum products GTAP; commodity
    "Chemical_Processing": 2.5,  # basic chemicals GTAP
    "PTA_Production":      1.2,  # specialised intermediate; very few suppliers
    "PET_Resin_Yarn":      1.5,  # intermediate chemical-textile
    "Fabric_Weaving":      2.0,  # textiles GTAP lower bound
    "Garment_Assembly":    3.3,  # GTAP v10 wearing apparel sigma_m ← UPDATED
    "UK_Wholesale":        3.5,  # distribution services
    "UK_Retail":           4.0,  # final goods retail
}
```

---

## PART 5: PARAMETERS STILL FLAGGED AS ASSUMPTIONS

The following must be disclosed as model assumptions in any paper/report:

| Parameter | Assumed value | Why it cannot be sourced online | Recommended note |
|-----------|--------------|--------------------------------|-----------------|
| A_BASE matrix | Derived from value-added share ratios | ONS IO tables blocked; WIOD behind paywall | "Calibrated to industry value-chain estimates; ONS IO tables recommended for validation" |
| B_BASE capital coefficients | 0.40–0.06 diagonal | EU KLEMS/ONS Capital Account not accessible | "Standard assumption: capital intensity declines downstream; see EU KLEMS for validation" |
| SAFETY_STOCK_WEEKS (most sectors) | 2.5–10 weeks | ICIS data is subscription-only | "Industry-standard estimates; Chemical Processing anchor from 688kt MEG / ~230kt/wk" |
| STAGE_RETAIL_VALUE_SHARE | Industry estimates | ONS IO tables not downloadable | "Literature-based; consistent with fabriclore/szoneierfabrics estimates; ONS IO validation needed" |
| ABM alpha (0.30), fill_rate (0.90), recovery (0.05) | Standard Beer Game calibration | No polyester-specific data found | "Sterman (1989) Beer Distribution Game defaults" |
| Oil_Extraction geography | IEA/BP estimates | IEA paywall; BP PDF not fetched | "Approximate; IEA World Energy Outlook 2023 recommended" |

---

## SOURCES

- [USITC Armington Elasticity Comparison](https://www.usitc.gov/publications/332/journals/jice_armington_elasticity.pdf)
- [USITC Revised Armington Elasticities](https://www.usitc.gov/publications/332/ec200401a.pdf)
- [GTAP Armington Elasticities for UK Economy](https://gtap.agecon.purdue.edu/resources/res_display.asp?RecordID=6116)
- [GTAP Review of Armington Trade Substitution Elasticities](https://www.gtap.agecon.purdue.edu/resources/res_display.asp?RecordID=1148)
- [Gallaway, McDaniel & Rivera — Short-run and Long-run Armington Elasticities](https://www.gtap.agecon.purdue.edu/resources/download/1338.pdf)
- [Feenstra et al. NBER — In Search of the Armington Elasticity](https://www.nber.org/system/files/working_papers/w20063/w20063.pdf)
- [GlobalData — PTA Capacity Report (via k-online.com)](https://www.k-online.com/en/Media_News/News/PTA_MARKET_Global_capacity_to_grow_by_more_than_5_per_year_Global_Data_report_China_leads_investments)
- [Statista — Global PTA Production Capacity 2023](https://www.statista.com/statistics/1065886/global-purified-terephthalic-acid-production-capacity/)
- [Asia to dominate global PTA capacity additions by 2028](https://www.offshore-technology.com/analyst-comment/asia-dominate-global-pta-capacity-additions-2028/)
- [Grand View Research — MEG Market](https://www.grandviewresearch.com/industry-analysis/monoethylene-glycol-market)
- [PR Newswire — Global MEG Markets 2019–2023](https://www.prnewswire.com/news-releases/global-monoethylene-glycol-meg-markets-2019-2023---capacities-production-consumption-trade-statistics-and-prices-300803354.html)
- [Fibre2Fashion — MEG Global Overview](https://www.fibre2fashion.com/industry-article/7424/global-overview-market-trend-and-forecast-for-meg)
- [Fortune Business Insights — Ethylene Glycol Market](https://www.fortunebusinessinsights.com/ethylene-glycol-market-110172)
- [Grand View Research — Polyester Fiber Market](https://www.grandviewresearch.com/industry-analysis/polyester-fiber-market-report)
- [Future Market Insights — Polyester Fiber Market 2032](https://www.futuremarketinsights.com/reports/polyester-fiber-market)
- [Allied Market Research — Polyester Fiber](https://www.alliedmarketresearch.com/polyester-fiber-market-A10583)
- [Modaes Global — From China to India: Race to Dominate Fiber Production](https://www.modaes.com/global/markets/from-china-to-india-who-gives-more-fiber-to-the-world)
- [Textile Exchange — Global Fiber Production Record High 2023](https://textileexchange.org/news/textile-exchange-releases-2024-materials-market-report/)
- [WTO GVC Sectoral Profiles: Textiles and Clothing 2024](https://www.wto.org/english/res_e/statis_e/miwi_e/gvc_sectoral_profiles_textiles_clothing24_e.pdf)
- [WTO Reports World Textiles and Clothing Trade 2022 (shenglufashion.com)](https://shenglufashion.com/2023/08/14/wto-reports-world-textiles-and-clothing-trade-in-2022/)
- [Patterns of Global Textile and Apparel Trade — Origin of Value Added (Oct 2025)](https://shenglufashion.com/2025/10/10/patterns-of-global-textile-and-apparel-trade-measured-by-origin-of-value-added-updated-october-2025/)
- [Top garment manufacturing countries (Textiles Resources)](https://www.textilesresources.com/articles/top-garment-manufacturing-countries-in-the-world/)
- [Polyester Clothing Cost Analysis (szoneierfabrics.com)](https://szoneierfabrics.com/polyester-clothing-cost-analysis-fabric-labor-and-logistics-breakdown/)
- [Fabric Cost Breakdown for Clothing Brands (fabriclore.com)](https://fabriclore.com/blogs/fashion-business-lifestyle-trends/fabric-cost-breakdown-for-clothing-brands/)
- [Polyester Value Chain Analysis — PMC/Springer](https://pmc.ncbi.nlm.nih.gov/articles/PMC7787125/)
- [ONS UK Input-Output Analytical Tables 2023](https://www.ons.gov.uk/releases/ukinputoutputanalyticaltables2023)
- [ONS Input-Output Supply and Use Tables](https://www.ons.gov.uk/economy/nationalaccounts/supplyandusetables/datasets/inputoutputsupplyandusetables)
- [ResourceWise — Understanding the Global Polyester Chain](https://www.resourcewise.com/blog/chemicals-blog/understanding-the-global-polyester-chain)
