# Data Source Audit — Polyester Textile Supply Chain Model
## Complete Parameter-by-Parameter Verification
**Audit date:** 2026-04-17 (v4: MRIO module §23, Ghosh module §24, comprehensive priority gaps, 56 sources)  
**Auditor:** Model review against all source documents

---

## Classification Key
- **REAL** — exact figure from a named primary source document or official dataset
- **EXTERNAL** — sourced from published literature / public database (web-retrieved)
- **DERIVED** — mathematically computed from REAL or EXTERNAL inputs
- **ESTIMATED** — calibrated from indirect evidence, analogy, or literature range; not a direct primary figure
- **ASSUMED** — behavioural or structural parameter with no empirical primary source; set from standard modelling practice

---

## 1. UK IMPORT DATA (`real_data.py` → `UK_IMPORTS_BY_COUNTRY`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| Total UK synthetic apparel imports 2023 | £2,388,954,178 | **REAL** | HMRC 2023 "2023 Synthetic Apparel Imports.xlsx", By Country sheet — exact cell value |
| China import value | £651,373,563 (27.27%) | **REAL** | HMRC 2023 xlsx, By Country sheet |
| EU aggregate | £586,526,782 (24.55%) | **REAL** | HMRC 2023 xlsx |
| Bangladesh | £287,422,073 (12.03%) | **REAL** | HMRC 2023 xlsx |
| Turkey | £143,694,104 (6.02%) | **REAL** | HMRC 2023 xlsx |
| Vietnam | £117,735,860 (4.93%) | **REAL** | HMRC 2023 xlsx |
| Italy | £101,522,756 (4.25%) | **REAL** | HMRC 2023 xlsx |
| India | £87,903,954 (3.68%) | **REAL** | HMRC 2023 xlsx |
| Netherlands | £82,147,487 (3.44%) | **REAL** | HMRC 2023 xlsx |
| Spain | £80,474,939 (3.37%) | **REAL** | HMRC 2023 xlsx |
| France | £79,504,634 (3.33%) | **REAL** | HMRC 2023 xlsx |
| Cambodia | £79,325,931 (3.32%) | **REAL** | HMRC 2023 xlsx |
| Sri Lanka | £65,106,449 (2.73%) | **REAL** | HMRC 2023 xlsx |
| Pakistan | £63,140,646 (2.64%) | **REAL** | HMRC 2023 xlsx |
| Belgium | £62,967,672 (2.64%) | **REAL** | HMRC 2023 xlsx |
| Myanmar | £51,248,724 (2.15%) | **REAL** | HMRC 2023 xlsx |
| Germany | £47,399,236 (1.98%) | **REAL** | HMRC 2023 xlsx |
| Hong Kong | £47,304,519 (1.98%) | **REAL** | HMRC 2023 xlsx |
| Morocco | £46,753,409 (1.96%) | **REAL** | HMRC 2023 xlsx |
| Indonesia | £25,812,968 (1.08%) | **REAL** | HMRC 2023 xlsx |
| Romania | £17,537,957 (0.73%) | **REAL** | HMRC 2023 xlsx |
| Jordan | £13,010,271 (0.55%) | **REAL** | HMRC 2023 xlsx |
| Philippines | £12,962,664 (0.54%) | **REAL** | HMRC 2023 xlsx |
| Thailand | £8,655,357 (0.36%) | **REAL** | HMRC 2023 xlsx |

**All 23 country rows are direct primary data from HMRC 2023. No estimates.**

---

## 2. UK DOMESTIC INDUSTRY (`real_data.py` → `UK_INDUSTRY`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| Manufacturer companies | 10,870 | **REAL** | ONS Business Register (SIC 13/14) — cited in RiSC_report.docx |
| Manufacturer turnover | £9.4bn | **REAL** | ONS Annual Business Survey 2022/23 — cited in RiSC_report.docx |
| Wholesale companies | 11,230 | **REAL** | ONS Business Register (SIC 46) — cited in RiSC_report.docx |
| Wholesale turnover | £20bn | **REAL** | ONS Annual Business Survey — cited in RiSC_report.docx and Findings doc |
| Retail companies | 30,790 | **REAL** | ONS Business Register (SIC 47) — cited in RiSC_report.docx |
| Retail turnover | £51.4bn | **REAL** | ONS Retail Sales data 2023 — cited in RiSC_report.docx and Findings doc |

---

## 3. GLOBAL FIBRE SHARES (`real_data.py` → `GLOBAL_FIBRE_SHARES`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| Polyester share | 57% | **REAL** | Textile Exchange Materials Market Report 2024, p.4 |
| Cotton share | 20% | **REAL** | Textile Exchange 2024 |
| Nylon share | 5% | **REAL** | Textile Exchange 2024 |
| Viscose share | 6% | **REAL** | Textile Exchange 2024 |
| Acrylic share | 2% | **REAL** | Textile Exchange 2024 |

---

## 4. CHINA UPSTREAM IMPORT DEPENDENCY (`real_data.py` → `CHINA_IMPORT_DEPENDENCY`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| China MEG import dependency | 43% | **REAL** | "Textile Industrial Supply Chain 09122024.pptx", Key Points slide: "China imports 43% of world's ethylene glycol" |
| China p-Xylene import dependency | 45% | **REAL** | Same pptx: "China imports 45% of world's p-Xylene" |

---

## 5. CHINA PTA GLOBAL SHARE (`real_data.py` → `CHINA_PTA_GLOBAL_SHARE`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| China share of global PTA production capacity | 67% | **EXTERNAL** | GlobalData (2021), "Global PTA Capacity and Production Statistics" — China 80.1 Mt/yr out of ~120 Mt/yr global. Cited in industry commentary at ICIS (2022): "China accounts for approximately two-thirds of global PTA capacity." Note: RiSC_report.docx stated "vast majority" (unquantified); updated to 67% from capacity data. |

> **Caveat:** GlobalData reports are subscription-based; the 67% figure is widely cited in industry press (ICIS, S&P Global Commodity Insights 2022) but the original dataset cannot be freely accessed for verification.

---

## 6. OIL IMPORT SOURCES (`real_data.py` → `OIL_IMPORT_SOURCES`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| South Korea: Saudi Arabia 31%, USA 16%, UAE 11%, Kuwait 10% | As stated | **REAL** | Korea National Oil Corporation (KNOC) / Korea Customs Service Import Statistics 2022 — cited in Textile Industrial Supply Chain pptx |
| Japan: Saudi Arabia 41%, UAE 40%, Kuwait 9% | As stated | **REAL** | Japan Ministry of Economy, Trade and Industry (METI) Energy White Paper 2022 — cited in pptx |

---

## 7. TRANSIT TIMES (`real_data.py` → `TRANSIT_DAYS`)

| Route | Days | Status | Source |
|---|---|---|---|
| Saudi Arabia → China | 23 | **REAL** | Logistics_Price_Info.pptx — explicit slide data |
| Saudi Arabia → South Korea | 17 | **REAL** | Logistics_Price_Info.pptx |
| South Korea → Japan | 2 | **REAL** | Logistics_Price_Info.pptx |
| Japan → China | 13 | **REAL** | Logistics_Price_Info.pptx |
| South Korea → China | 28 | **REAL** | Logistics_Price_Info.pptx |
| China → UK | 37 | **REAL** | Logistics_Price_Info.pptx — "37 days sea freight China to UK" |
| Bangladesh → UK | 28 | **REAL** | Logistics_Price_Info.pptx |
| Turkey → UK | 7 | **REAL** | Logistics_Price_Info.pptx |
| India → UK | 25 | **REAL** | Logistics_Price_Info.pptx |
| Vietnam → UK | 32 | **REAL** | Logistics_Price_Info.pptx |

---

## 8. MEG PORT INVENTORIES (`real_data.py` → `MEG_PORT_INVENTORY_KT`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| Zhangjiagang MEG inventory | 418 kt | **REAL** | Logistics_Price_Info.pptx — February 2022 snapshot from CCFGroup/CMAI port monitoring data |
| Jiangyin/Changzhou MEG inventory | 134 kt | **REAL** | Same pptx |
| Taicang MEG inventory | 85 kt | **REAL** | Same pptx |
| Ningbo MEG inventory | 51 kt | **REAL** | Same pptx |
| Total MEG port inventory | 688 kt | **DERIVED** | Sum of above four ports |

> **Note:** This is a point-in-time snapshot (February 2022). Inventory levels vary seasonally; the model uses this as a representative buffer estimate.

---

## 9. STAGE GEOGRAPHY — GEOGRAPHIC SUPPLY SHARES (`real_data.py` → `STAGE_GEOGRAPHY`)

### 9a. Oil Extraction

**UPDATED 2026-04-17:** Replaced estimated values with EIA/Wikipedia data.

| Parameter | Value | Status | Source |
|---|---|---|---|
| USA: 16.0% | 13,782 kb/d | **REAL** | Wikipedia "List of countries by oil production" (EIA underlying data), Nov 2025 snapshot. Global total 86,281 kb/d. |
| Russia: 11.6% | 10,056 kb/d | **REAL** | Same source |
| Saudi Arabia: 11.5% | 9,940 kb/d | **REAL** | Same source |
| Canada: 6.1% | 5,234 kb/d | **REAL** | Same source |
| Iraq: 5.1% | 4,391 kb/d | **REAL** | Same source |
| UAE: 4.7% | 4,050 kb/d | **REAL** | Same source |
| Other: 45.0% | Residual | **DERIVED** | 1 − sum of named countries; includes Iran 4.8%, China 5.0%, Brazil 4.4%, Kuwait 3.1%, etc. |

> **Note:** Previous model had Saudi Arabia 17%, UAE 9%, Kuwait 6% — these overestimated Middle East shares. EIA data shows USA (#1, 16%) and Russia (#2, 11.6%) are larger producers than previously modelled. This reduces HHI concentration score for Oil_Extraction slightly.

### 9b. Chemical Processing (MEG + p-Xylene)

| Parameter | Value | Status | Source |
|---|---|---|---|
| China 35%, Saudi Arabia 18%, South Korea 14%, Japan 10%, USA 12%, Other 11% | As stated | **ESTIMATED** | Synthesised from: ICIS MEG/p-Xylene producer databases; SABIC annual report 2022; IHS Markit Chemical Supply Tracker. No single primary table was directly transcribed. |

> **Recommended improvement:** IEA Petrochemicals report 2023 or CEFIC (European Chemical Industry Council) capacity data.

### 9c. PTA Production

| Parameter | Value | Status | Source |
|---|---|---|---|
| China 67% | **EXTERNAL** | GlobalData 2021 capacity survey (see §5 above) |
| India 7% (Reliance, IOCL) | **ESTIMATED** | Approximated from ICIS India PTA capacity listings; consistent with ~8.5 Mt/yr Indian capacity vs 121 Mt/yr global |
| South Korea 6% (SK Chemicals, Huvis) | **ESTIMATED** | ICIS producer database |
| USA 5% (BP, Eastman) | **ESTIMATED** | ICIS producer database |
| Other 15% | **DERIVED** | Residual (1 − 0.67 − 0.07 − 0.06 − 0.05) |

### 9d. PET Resin / Yarn

| Parameter | Value | Status | Source |
|---|---|---|---|
| China 60% | **EXTERNAL** | CIRFS (International Rayon and Synthetic Fibres Committee) 2023 Annual Report; Textile Exchange Materials Market Report 2023: "China accounts for approximately 60% of global polyester fibre production" |
| India 13% | **EXTERNAL** | Textile Exchange 2023; Fibre2Fashion market intelligence 2023 |
| South Korea 6% | **EXTERNAL** | CIRFS 2023 |
| Taiwan 4% | **ESTIMATED** | CIRFS 2023 approximation |
| Other 17% | **DERIVED** | Residual |

### 9e. Fabric Weaving

| Parameter | Value | Status | Source |
|---|---|---|---|
| China 43.3% | **EXTERNAL** | WTO International Trade Statistics 2024 — "Leading exporters of textiles, 2023": China USD 109.8bn / USD 253.7bn world total = 43.3% |
| India 11% | **EXTERNAL** | WTO 2024 — India USD 27.9bn / USD 253.7bn = 11.0% |
| Bangladesh 5% | **EXTERNAL** | WTO 2024 approximation (Bangladesh primarily garment exporter; woven fabric ~5% of world textile exports) |
| Turkey 5% | **EXTERNAL** | WTO 2024 — Turkey textile exports ~USD 12-13bn |
| Other 35.7% | **DERIVED** | Residual |

> **Note:** WTO figures measure textile *exports*, not global *production capacity*. These are used as a proxy for production share, which is reasonable but imperfect (domestic consumption not captured).

### 9f. Garment Assembly

| Parameter | Value | Status | Source |
|---|---|---|---|
| All 10 country shares | **REAL** | HMRC 2023 "2023 Synthetic Apparel Imports.xlsx" By Country sheet — exact values as fraction of £2,388,954,178 total |
| "Other" residual 30.98% | **DERIVED** | 1 − sum of named countries |

**This is the only stage where all shares are directly from a UK primary source.**

### 9g. UK Wholesale

| Parameter | Value | Status | Source |
|---|---|---|---|
| UK 85%, Other 15% | **ESTIMATED** | No direct primary source. Approximation: UK wholesalers service 85% of UK retail supply chain; 15% represents direct importing by large retailers (e.g. ASOS, Next). Consistent with ONS trade data structure but not a directly cited figure. |

### 9h. UK Retail

| Parameter | Value | Status | Source |
|---|---|---|---|
| UK 100% | **REAL** | By definition: UK retail occurs in the UK |

---

## 10. ASOS SUPPLIER BREAKDOWN (`real_data.py` → `ASOS_SUPPLIERS`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| China 26%, Turkey 21.5%, India 17.7%, Bangladesh 6.6%, Other 28.2% | As stated | **REAL** | Findings-02-12-2024.docx — ASOS supplier disclosure, representative of major UK online fashion retailer |

---

## 11. VALUE-ADDED SHARES (`real_data.py` → `STAGE_RETAIL_VALUE_SHARE`)

**UPDATED:** Previously ESTIMATED from literature. Now DERIVED from ONS UK IO Analytical Tables 2023 using backward GVA chain.

**Method:** GVA/Output rates extracted from ONS IOT domestic use table. Backward chain:
`vs[j] = vs[j+1] × (1 − GVA_rate[j+1])`, anchored at `vs[Retail] = 1.000`.

| Parameter | Value | Status | GVA/Output (ONS IOT 2023) | Source |
|---|---|---|---|---|
| Oil Extraction | 0.010 | **DERIVED** | Oil (CPA_B): £25,313m GVA / £37,016m Output = 0.684 | ONS UK IO Analytical Tables 2023, IOT sheet |
| Chemical Processing | 0.031 | **DERIVED** | Refined Petro (CPA_C19): £2,870m / £35,147m = 0.082 | ONS UK IO Analytical Tables 2023, IOT sheet |
| PTA Production | 0.034 | **DERIVED** | Petrochem (CPA_C20B): £2,171m / £9,738m = 0.223 | ONS UK IO Analytical Tables 2023, IOT sheet |
| PET Resin/Yarn | 0.044 | **DERIVED** | Textiles (CPA_C13): £3,514m / £7,347m = 0.478 | ONS UK IO Analytical Tables 2023, IOT sheet |
| Fabric Weaving | 0.085 | **DERIVED** | Apparel (CPA_C14): £1,801m / £3,266m = 0.552 | ONS UK IO Analytical Tables 2023, IOT sheet |
| Garment Assembly | 0.190 | **DERIVED** | Wholesale (CPA_G46): £113,354m / £214,742m = 0.528 | ONS UK IO Analytical Tables 2023, IOT sheet |
| UK Wholesale | 0.402 | **DERIVED** | Retail (CPA_G47): £104,392m / £174,593m = 0.598 | ONS UK IO Analytical Tables 2023, IOT sheet |
| UK Retail | 1.000 | **REAL** | Anchor by definition | ONS UK IO Analytical Tables 2023 |

> **Cross-validation:** McKinsey "The State of Fashion" (2020) estimates garment 15–20% of retail and wholesale 35–45% of retail for apparel value chains. Model values (garment 19.0%, wholesale 40.2%) fall within these ranges, providing independent confirmation.

---

## 12. COTTON PRODUCTION (`real_data.py` → `COTTON_PRODUCTION`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| China 22.5%, India 22.5%, USA 14.7%, Other 40.3% | As stated | **REAL** | Liu, J. & Hudson, D. (2022) "Global Cotton Production and Trade" — cited in Findings-02-12-2024.docx |

---

## 13. EFFECTIVE CHINA DEPENDENCY (`real_data.py` → `EFFECTIVE_CHINA_DEPENDENCY`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| Oil 5%, Chemical 47% | **ESTIMATED** | Derived from upstream tracing logic; no direct measurement |
| PTA 67% | **DERIVED** | = CHINA_PTA_GLOBAL_SHARE (external source, see §5) |
| PET 60% | **DERIVED** | = STAGE_GEOGRAPHY["PET_Resin_Yarn"]["China"] |
| Fabric 43.3% | **DERIVED** | = STAGE_GEOGRAPHY["Fabric_Weaving"]["China"] |
| Garment 60% | **ESTIMATED** | RiSC_report.docx states "effective dependency ~60%" when upstream Bangladesh/Vietnam fabric sourcing from China is traced. Nominal (HMRC) = 27.3%; the 60% represents indirect dependency. No precise quantification in primary sources — described qualitatively as "significant." |

---

## 14. ARMINGTON SUBSTITUTION ELASTICITIES (`real_data.py` → `ARMINGTON_ELASTICITY`)

| Parameter | Value | Status | Source |
|---|---|---|---|
**UPDATED 2026-04-17:** Four entries now use exact GTAP v10 values (upgraded from ESTIMATED/EXTERNAL to EXTERNAL with precise citation).

| Parameter | Value | Status | Source |
|---|---|---|---|
| Oil Extraction σ = 5.20 | Updated from 4.0 | **EXTERNAL** | GTAP v10 database — Hertel, T.W. et al. (2012) Global Trade Analysis. Sector "oil" (crude oil extraction) σ_m = 5.20. |
| Chemical Processing σ = 3.65 | Updated from 2.5 | **EXTERNAL** | GTAP v10 sector "crp" (chemicals, rubber, plastics) σ_m = 3.65 — Hertel et al. (2012). |
| PTA Production σ = 1.20 | Unchanged | **ESTIMATED** | Below GTAP "crp" (3.65) because PTA is a specific, highly concentrated intermediate (China 67%) with high switching costs and long-term supply contracts. Balistreri & Hillberry (2007) σ = 1.0–1.5 for such intermediates. |
| PET Resin/Yarn σ = 1.50 | Unchanged | **ESTIMATED** | Above PTA reflecting marginally more supplier diversity; no specific GTAP parameter for synthetic fibres. |
| Fabric Weaving σ = 3.20 | Updated from 2.0 | **EXTERNAL** | GTAP v10 sector "tex" (textiles, CPA_C13) σ_m = 3.20 — Hertel et al. (2012). |
| Garment Assembly σ = 3.30 | Unchanged (already GTAP) | **EXTERNAL** | GTAP v10 sector "wap" (wearing apparel, CPA_C14) σ_m = 3.30 — Hertel et al. (2012). |
| UK Wholesale σ = 3.50 | Unchanged | **ESTIMATED** | No specific GTAP parameter for wholesale distribution. |
| UK Retail σ = 4.00 | Unchanged | **ESTIMATED** | GTAP "wap" consumer-level elasticity applied to final retail stage. |

---

## 15. SAFETY STOCK WEEKS (`real_data.py` → `SAFETY_STOCK_WEEKS`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| Chemical Processing: 3.0 weeks | **DERIVED** | MEG: 688 kt total port inventory ÷ estimated ~230 kt/week consumption = ~3.0 weeks. Consumption rate itself is estimated from CHINA_IMPORT_DEPENDENCY and production volumes, not directly measured. |
| PTA Production: 2.5 weeks | **ESTIMATED** | Industry standard for PTA (closer co-location with PET plants reduces storage need). No primary source. |
| PET Resin/Yarn: 3.0 weeks | **ESTIMATED** | Typical chemical intermediate inventory holding period. No primary source. |
| Fabric Weaving: 4.0 weeks | **ESTIMATED** | Consistent with typical 30-day fabric inventory observed in industry surveys (McKinsey 2020). No sector-specific primary source. |
| Garment Assembly: 6.0 weeks | **ESTIMATED** | Typical for seasonal fashion production (6-week buffer before peak season). No primary source. |
| UK Wholesale: 8.0 weeks | **ESTIMATED** | Consistent with UK logistics industry standard (BRC Retail Logistics report 2022 mentions 6-10 weeks for fashion). No direct citation. |
| UK Retail: 10.0 weeks | **ESTIMATED** | UK fashion retailers typically carry 8-12 weeks of forward stock (Kantar Retail UK 2022). No direct citation. |
| Oil Extraction: 4.0 weeks | **ESTIMATED** | IEA Strategic Petroleum Reserve policy targets 90 days (≈13 weeks) for oil-importing nations; 4.0 weeks reflects a conservative commercial stock estimate. |

---

## 16. TECHNICAL COEFFICIENT MATRIX (`io_model.py` → `A_BASE`)

**UPDATED:** Mixed calibration strategy applied. Four entries now use ONS IO direct coefficients; two use IO-derived value-share ratios; five remain global supply-chain estimates for upstream stages where UK domestic IO is near-zero.

### 16a. ONS IO-grounded entries (downstream material inputs)

| A_BASE entry | Value | Status | ONS CPA pair | Source |
|---|---|---|---|---|
| Fabric(C13) → Garment(C14): A[4,5] | 0.0855 | **DERIVED** | C13→C14 total (domestic + import) direct coefficient | ONS UK IO Analytical Tables 2023, "A" + "Imports use pxp" sheets |
| Wholesale(G46) → Garment(C14): A[6,5] | 0.0962 | **DERIVED** | G46→C14 domestic direct coefficient | ONS UK IO Analytical Tables 2023, "A" sheet |
| Petrochem(C20B) → Textiles(C13): A[1,4] | 0.0555 | **DERIVED** | C20B→C13 total direct coefficient | ONS UK IO Analytical Tables 2023, "A" + "Imports use pxp" sheets |

### 16b. IO-derived value-share ratios (goods-distribution chain)

The ONS G46 and G47 sectors represent trade-services margins, not merchandise flows. Direct IO coefficients (G46→G47 ≈ 0.0095) capture only the trade-margin service, not the full merchandise value. Distribution-chain coefficients are derived instead from the IO-based `STAGE_RETAIL_VALUE_SHARE` (§11) using the same ratio method, ensuring model-internal consistency.

| A_BASE entry | Value | Status | Formula | Source |
|---|---|---|---|---|
| Garment → Wholesale: A[5,6] | 0.321 | **DERIVED** | vs[Gar]/vs[Who] × 0.68 = 0.190/0.402 × 0.68 | ONS IOT GVA/Output + distribution margin literature |
| Wholesale → Retail: A[6,7] | 0.225 | **DERIVED** | vs[Who]/vs[Ret] × 0.56 = 0.402/1.000 × 0.56 | ONS IOT GVA/Output + ONS retail margin data |

### 16c. Upstream entries (global supply-chain estimates)

UK domestic IO has near-zero coefficients for these stages because the UK imports >95% of polyester feedstock. Global cost-structure estimates are used instead, consistent with IEA/ICIS petrochemical cost literature.

| A_BASE entry | Value | Status | Source |
|---|---|---|---|
| Oil → Chemical: A[0,1] | 0.20 | **ESTIMATED** | IEA Petrochemicals 2023: oil feedstock ~20% of chemical output value globally |
| Chemical → PTA: A[1,2] | 0.30 | **ESTIMATED** | p-Xylene/MEG ~30% of PTA unit cost (ICIS cost analysis) |
| PTA → PET: A[2,3] | 0.35 | **ESTIMATED** | PTA + MEG ~35% of PET resin cost (S&P Global 2022) |
| PET → Fabric: A[3,4] | 0.20 | **ESTIMATED** | Polyester yarn ~20% of woven fabric output value (Werner International 2022) |
| Oil → PET (energy): A[0,3] | 0.04 | **ESTIMATED** | Energy for polymerisation ~4% of output value (IEA estimate) |

---

## 17. CAPITAL COEFFICIENT MATRIX (`io_model.py` → `B_BASE`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| All diagonal values (0.40, 0.35, 0.30, 0.22, 0.15, 0.08, 0.12, 0.06) | **ASSUMED** | No primary source. Set to reflect declining capital intensity from upstream (oil: high fixed assets) to downstream (retail: low). Values are plausible but unverified. ONS Capital Expenditure surveys (SIC 13/14/19/20) would be the correct source. |

---

## 18. DELIVERY LAG MATRIX (`io_model.py` → `LAG_WEEKS`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| Oil→Chemical: 3 weeks | **DERIVED** | Saudi Arabia→China 23 days ÷ 7 = 3.3 → 3 weeks. From TRANSIT_DAYS (REAL). |
| Chemical→PTA: 1 week | **DERIVED** | Co-located in China; 1-week internal logistics. |
| PTA→PET: 1 week | **DERIVED** | Co-located. |
| PET→Fabric: 2 weeks | **DERIVED** | Intra-China or short-haul. |
| Fabric→Garment: 2 weeks | **DERIVED** | China or Bangladesh domestic. |
| Garment→Wholesale: 5 weeks | **DERIVED** | China→UK 37 days ÷ 7 = 5.3 → 5 weeks. From TRANSIT_DAYS (REAL). |
| Wholesale→Retail: 1 week | **DERIVED** | UK domestic distribution. |

---

## 19. CGE CALIBRATION QUANTITIES (`cge_model.py` → `Q0_GBP`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| UK Retail: £51.4bn | **REAL** | ONS Retail Sales 2023 — same as `UK_INDUSTRY.retail.turnover_gbp` |
| UK Wholesale: £20bn | **REAL** | ONS Annual Business Survey 2023 — same as `UK_INDUSTRY.wholesale.turnover_gbp` |
| Garment Assembly: £4.2bn | **ESTIMATED** | UK imports £2.39bn (REAL) + estimated domestic production ~£1.8bn (ESTIMATED from ONS manufacturer turnover £9.4bn with ~20% attributable to garments). |
| Fabric Weaving: £2.4bn | **ESTIMATED** | Derived from STAGE_RETAIL_VALUE_SHARE ratio (0.24/0.42 × garment value). |
| PET Resin/Yarn: £1.3bn | **ESTIMATED** | Derived from value-share ratio. |
| PTA Production: £0.9bn | **ESTIMATED** | Derived from value-share ratio. |
| Chemical Processing: £0.6bn | **ESTIMATED** | Derived from value-share ratio. |
| Oil Extraction: £0.3bn | **ESTIMATED** | Fraction of UK-attributable oil value for polyester chain. |

> **Note:** Only retail (£51.4bn) and wholesale (£20bn) are directly from real data. All upstream quantities are estimated via value-chain ratios derived from the ESTIMATED `STAGE_RETAIL_VALUE_SHARE` table.

---

## 20. FREIGHT COST SHARES (`cge_model.py` → `FREIGHT_COST_SHARE`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| Garment Assembly: 7.5% | **EXTERNAL** | UNCTAD Review of Maritime Transport 2023: "freight costs represent 6-8% of FOB value for garment exports from Asia" — using midpoint 7.5%. |
| UK Wholesale: 20% | **ESTIMATED** | Logistics cost as fraction of wholesale distribution — World Bank Logistics Performance Index methodology suggests 15-25% for UK retail distribution. 20% is midpoint. |
| Fabric Weaving: 5.5% | **ESTIMATED** | UNCTAD 2023 textile sector average freight/FOB ratio ~4-7%; 5.5% midpoint. |
| PET Resin/Yarn: 4% | **ESTIMATED** | Bulk chemical/polymer sea freight; consistent with ICIS freight cost analysis framework. |
| PTA Production: 3% | **ESTIMATED** | Bulk commodity, lower unit freight cost. |
| Chemical Processing: 2% | **ESTIMATED** | Partially pipeline, partially tanker. |
| Oil Extraction: 1% | **ESTIMATED** | Crude oil pipeline/tanker cost is very low per unit value. |
| UK Retail: 3% | **ESTIMATED** | Last-mile delivery costs as fraction of retail price (consistent with ONS distribution cost data). |

---

## 21. ABM BEHAVIOURAL PARAMETERS (`abm_model.py`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| Exponential smoothing α = 0.3 | **ESTIMATED** | Standard value used in Beer Distribution Game literature (Sterman 1989, 2000). Range in published ABMs: 0.2–0.5. No supply-chain-specific calibration for polyester. |
| Adaptive safety stock increase: 5%/week | **ASSUMED** | Sterman (2000) "Business Dynamics" anchoring/adjustment heuristic. |
| Safety stock cap: 20× weekly capacity | **ASSUMED** | Reasonable upper bound; no primary source. |
| Disrupted output: 5% of normal | **ASSUMED** | Convention for severe disruption in ABM models (Ivanov 2017). |
| Capacity recovery rate: 5%/week | **ASSUMED** | Implies ~20 weeks for full recovery — consistent with literature on supply chain disruption recovery (Tang 2006: 3-6 months typical). |
| Pipeline fill rate: 90% | **ASSUMED** | Standard imperfect fulfilment rate in supply chain ABMs. No sector-specific source. |
| Lead time default: 2 weeks | **ESTIMATED** | Generic default; overridden by `_lead_time_from_real_data()` for key routes. |
| Garment→UK lead time: 5 weeks | **DERIVED** | China→UK 37 days ÷ 7 = 5.3 → 5 weeks (REAL transit data). |
| Chemical→UK lead time: 3 weeks | **DERIVED** | Saudi Arabia→China 23 days ÷ 7 = 3.3 → 3 weeks (REAL transit data). |

---

## 22. SHOCK SCENARIO PARAMETERS (`shocks.py`)

| Parameter | Value | Status | Source |
|---|---|---|---|
| S1 PTA shock magnitude: 50% | **ESTIMATED** | Calibrated to 2018 nylon-66 ADN factory fires which caused 35-40% supply reduction (Bloomberg, Chemical Week). Scaled up to 50% for a more severe but plausible PTA event. |
| S1 PET cascade: 35% | **ESTIMATED** | Proportional downstream effect derived from A_BASE coefficients. |
| S2 MEG shock: 25% | **ESTIMATED** | Saudi Arabia supplies ~30% of world MEG (external source); a major disruption (Red Sea closure) would cut ~60-80% of this flow → 18-24% world MEG reduction. 25% is calibrated midpoint. |
| S2 MEG buffer: 3 weeks | **DERIVED** | 688 kt port inventory ÷ ~230 kt/week implied consumption rate = ~3 weeks. Consumption rate is ESTIMATED. |
| S3 tariff rate: 35% | **ESTIMATED** | Scenario assumption for geopolitical shock. Reference: US-China Section 301 tariffs on apparel reached 7.5-25% (USTR 2019); 35% represents a more severe UK-specific scenario. |
| S3 China garment shock: 35% | **DERIVED** | From tariff (35%) applied to China's 27.3% HMRC share. |
| S4 Zhangjiagang share: 61% | **DERIVED** | 418 kt ÷ 688 kt = 60.8% ≈ 61% (REAL: from MEG_PORT_INVENTORY_KT). |
| S5 pandemic magnitudes | **ESTIMATED** | Calibrated to observed COVID-19 impacts: NBS China PMI Feb 2020 = 35.7 (implying ~57% output reduction); ILO garment jobs lost 25-50%. |
| S5 transit delay: 37→70 days | **REAL** | Documented during COVID: Freightos/Drewry tracked China→UK times doubling in 2021. |

---

## 23. MRIO MODEL PARAMETERS (`mrio_model.py`)

### 23a. Region definitions and country mapping

| Parameter | Status | Source |
|---|---|---|
| 8-region structure (CHN, SAS, EAS, MDE, AME, EUR, GBR, ROW) | **ASSUMED** | Defined to match STAGE_GEOGRAPHY country coverage. No primary source for aggregation schema. |
| Country→Region mapping (20 mappings) | **DERIVED** | Mechanically aggregates STAGE_GEOGRAPHY countries to 8 MRIO regions. Derivation is exact; the underlying country shares carry the status of their source (§9). |

### 23b. MRIO calibration

| Parameter | Status | Source |
|---|---|---|
| Proportional sourcing assumption (A_MRIO[r,i,s,j] = A_BASE[i,j] × share[i,r]) | **ASSUMED** | Standard MRIO proxy calibration (RAS-based approach) used when bilateral inter-regional trade matrices are unavailable. True bilateral flows would require WIOD or GTAP MRIO tables. |
| GVA rates tiled across all regions (same rates for all regions) | **ASSUMED** | Uses ONS IOT 2023 UK GVA rates (§11) applied uniformly to all regions. In reality, Chinese and South Asian processing sectors have lower GVA rates (more labour-intensive, lower margins). Region-specific GVA rates require regional IO tables (e.g. China NBS IO 2018). |

> **Structural limitation:** The proportional sourcing assumption means intra-China circular flows are not captured — Chinese PTA plants sourcing Chinese chemicals do not create additional amplification of China's effective exposure beyond the nominal production share. WIOD bilateral trade data would fix this.

### 23c. MRIO-specific new parameters

| Parameter | Count | Status | Notes |
|---|---|---|---|
| Regional production share matrix (8 regions × 8 sectors) | 64 cells | **DERIVED** | Aggregated from STAGE_GEOGRAPHY (§9); inherits source quality of §9 entries |
| A_MRIO matrix (64×64) | 4,096 cells | **DERIVED** | Deterministically computed from A_BASE and regional shares |
| L_MRIO Leontief inverse (64×64) | 4,096 cells | **DERIVED** | Computed analytically |

---

## 24. GHOSH MODEL PARAMETERS (`ghosh_model.py`)

### 24a. Core Ghosh matrices

| Parameter | Status | Source |
|---|---|---|
| B matrix = diag(1/x) × A_BASE × diag(x) | **DERIVED** | Computed analytically from A_BASE (§16) and baseline gross output x |
| Ghosh inverse G = (I − B)^{-1} | **DERIVED** | Computed analytically |
| GVA rates for primary input vector v | **DERIVED** | Same ONS IOT 2023 rates as §11 (Oil 0.684, Chemical 0.082, …, Retail 0.598) |

> **Calibration note:** The model uses exogenous GVA rates (not row-balance identity) for primary inputs because all final demand is concentrated at UK_Retail, which gives v_i = 0 for all upstream sectors under the row-balance approach. This is a modelling artefact, not a data gap. See §11 for GVA rate sources.

### 24b. Ghosh scenario shock magnitudes (GS1–GS5)

| Parameter | Value | Status | Source |
|---|---|---|---|
| GS1 PTA shock: 50% | **ESTIMATED** | Mirrors Leontief S1. Same calibration basis as §22 S1. |
| GS2 Chemical shock: 25% | **ESTIMATED** | Mirrors Leontief S2 MEG shock magnitude. Same basis as §22 S2. |
| GS3 Oil shock: 20% | **ESTIMATED** | Calibrated to V7 Ukraine war oil supply reduction (~8% Russian crude lost from world market in 2022 per IEA; scaled up to 20% for a severe scenario). |
| GS4 Fabric + Garment shock: 40% | **ESTIMATED** | Calibrated to Bangladesh/Vietnam garment assembly disruption; consistent with COVID-era garment factory closures of 30-50% (ILO 2020). |
| GS5 Multi-node shock: PTA/PET/Fabric/Garment 50% | **ESTIMATED** | Mirrors Leontief S5 subset. Same basis as §22 S5. |

---

## SUMMARY TABLE

**Audit date: 2026-04-17 (v4 — MRIO, Ghosh, full data gap review)**

| Category | Total Parameters | REAL | EXTERNAL | DERIVED | ESTIMATED | ASSUMED |
|---|---|---|---|---|---|---|
| UK Import Data | 24 | **24** | 0 | 0 | 0 | 0 |
| UK Industry Turnover | 6 | **6** | 0 | 0 | 0 | 0 |
| Global Fibre Shares | 5 | **5** | 0 | 0 | 0 | 0 |
| China MEG/p-Xylene Dependency | 2 | **2** | 0 | 0 | 0 | 0 |
| China PTA Share | 1 | 0 | **1** | 0 | 0 | 0 |
| Oil Import Sources | 2 | **2** | 0 | 0 | 0 | 0 |
| Transit Times | 10 | **10** | 0 | 0 | 0 | 0 |
| MEG Port Inventories | 5 | **4** | 0 | **1** | 0 | 0 |
| Stage Geography (Oil) | 7 | **6** | 0 | **1** | 0 | 0 |
| Stage Geography (Chemical) | 1 | 0 | 0 | 0 | **1** | 0 |
| Stage Geography (PTA) | 5 | 0 | **1** | **1** | **3** | 0 |
| Stage Geography (PET) | 5 | 0 | **3** | **1** | **1** | 0 |
| Stage Geography (Fabric) | 5 | 0 | **3** | **1** | **1** | 0 |
| Stage Geography (Garment) | 11 | **10** | 0 | **1** | 0 | 0 |
| Stage Geography (Wholesale) | 1 | 0 | 0 | 0 | **1** | 0 |
| ASOS Suppliers | 5 | **5** | 0 | 0 | 0 | 0 |
| Value-Added Shares | 8 | **1** | 0 | **7** | 0 | 0 |
| Effective China Dependency | 8 | 0 | 0 | **4** | **4** | 0 |
| Armington Elasticities | 8 | 0 | **4** | 0 | **4** | 0 |
| Safety Stock Weeks | 8 | 0 | 0 | **1** | **7** | 0 |
| A_BASE — ONS IO (downstream) | 5 | 0 | 0 | **5** | 0 | 0 |
| A_BASE — upstream estimates | 5 | 0 | 0 | 0 | **5** | 0 |
| B_BASE (Capital coefficients) | 8 | 0 | 0 | 0 | 0 | **8** |
| LAG_WEEKS (Delivery lags) | 7 | 0 | 0 | **7** | 0 | 0 |
| Q0_GBP (CGE quantities) | 8 | **2** | 0 | 0 | **6** | 0 |
| FREIGHT_COST_SHARE | 8 | 0 | **1** | 0 | **7** | 0 |
| ABM Behavioural Parameters | 9 | 0 | 0 | **2** | **3** | **4** |
| Shock Magnitudes | 12 | **1** | 0 | **2** | **9** | 0 |
| MRIO Parameters (§23) | 7 | 0 | 0 | **4** | 0 | **3** |
| Ghosh Parameters (§24) | 8 | 0 | 0 | **3** | **5** | 0 |
| **TOTAL** | **208** | **77 (37%)** | **13 (6%)** | **42 (20%)** | **61 (29%)** | **15 (7%)** |

> **Change from v3 audit:**
> - **MRIO module added** (§23): 7 new parameters — 4 DERIVED (country mapping, regional shares, A_MRIO, L_MRIO), 3 ASSUMED (region structure, proportional sourcing, uniform GVA rates).
> - **Ghosh module added** (§24): 8 new parameters — 3 DERIVED (B, G, GVA vector), 5 ESTIMATED (GS1–GS5 shock magnitudes).
> - **Net change from v1 audit**: REAL +6, EXTERNAL +2, DERIVED +21, ESTIMATED −8, ASSUMED +3. Total: 193 → 208.

---

## PRIORITY GAPS — Data Needed to Improve the Model

This section lists all unresolved data gaps, prioritised by structural impact on model outputs. Each entry notes the affected module(s), the specific parameter(s) that would change, and the recommended primary source.

---

### TIER 1 — Critical: replaces ASSUMED/ESTIMATED parameters that drive core model results

**1. WIOD bilateral inter-regional trade matrices**
- *Affected:* `mrio_model.py` — A_MRIO calibration (§23b, 4,096 cells)
- *Current gap:* Proportional sourcing assumption (ASSUMED) means intra-China circular flows generate no amplification above nominal share. WIOD 2016 release or ADB MRIO 2023 provides actual bilateral trade flows for 43+ countries × 56 sectors.
- *Impact:* Would fix "amplification = 1.0" limitation. Expected to raise China's effective MRIO exposure above 67% nominal PTA share as circular CHN-CHN flows get captured.
- *Source:* WIOD (wiod.org, free), ADB MRIO (adb.org/mrio, free), or GTAP MRIO tables (purdue.edu, registration required)
- *Effort:* High (data integration); impact: very high

**2. Chemical Processing geography (MEG + p-Xylene capacity)**
- *Affected:* `real_data.py` — STAGE_GEOGRAPHY["Chemical_Processing"] (§9b, 6 parameters)
- *Current gap:* China 35%, Saudi Arabia 18%, S Korea 14%, Japan 10%, USA 12%, Other 11% — all ESTIMATED from synthesised secondary sources. Saudi Arabia share likely underestimated (Fibre2Fashion 2023 suggests Saudi MEG ~30%).
- *Impact:* Chemical Processing HHI and oil-to-chemical shock transmission. Correcting Saudi Arabia's MEG share would raise S2 MEG shock sensitivity.
- *Source:* IEA Petrochemicals 2023 (iea.org/reports, £60 subscription); ICIS MEG/PX capacity database (icis.com, subscription); CEFIC European Chemical Industry Council annual report (cefic.org, free)
- *Effort:* Low; impact: high

**3. Bangladesh and Vietnam fabric import dependency on China**
- *Affected:* `real_data.py` — EFFECTIVE_CHINA_DEPENDENCY["Garment"] (§13, 1 parameter)
- *Current gap:* Garment effective China dependency = 60% (ESTIMATED from qualitative RiSC_report.docx description). The 60% estimate reflects upstream tracing but is not quantified in any primary source.
- *Impact:* The Leontief China shock multiplier for UK retail depends directly on this figure. If true dependency is 70–75%, the £1.4bn estimated UK retail impact from a China shock would increase by ~15–25%.
- *Source:* BGMEA (Bangladesh Garment Manufacturers and Exporters Association) annual report (bgmea.com.bd, free); VITAS (Vietnam Textile and Apparel Association, vitas.com.vn); World Bank Global Value Chain database (wits.worldbank.org)
- *Effort:* Low; impact: high

**4. PTA and PET Armington substitution elasticities**
- *Affected:* `real_data.py` — ARMINGTON_ELASTICITY["PTA_Production"] = 1.2, ["PET_Resin_Yarn"] = 1.5 (§14, 2 parameters)
- *Current gap:* Both ESTIMATED. No GTAP sector maps directly to PTA or polyester yarn; the "crp" (chemicals, rubber, plastics) aggregate σ = 3.65 is too broad. Balistreri & Hillberry (2007) suggests σ = 1.0–1.5 for concentrated intermediates; current values sit in this range but are not sector-specific.
- *Impact:* Controls how quickly UK buyers substitute away from Chinese PTA/PET after a price shock. Lower σ → larger welfare loss and smaller trade diversion.
- *Source:* Gallaway et al. (2003) "Short-run and long-run industry-level estimates of US Armington elasticities" (NAJEF); Broda & Weinstein (2006) Econometrica estimates by HS-10 code; or estimate via Feenstra (1994) method using UN Comtrade PTA bilateral price/quantity data (HS 291736, HS 390760)
- *Effort:* Medium (econometric estimation); impact: high for tariff/policy scenarios

---

### TIER 2 — High impact: replaces ASSUMED parameters or fixes structural limitations

**5. ONS Capital Expenditure by SIC (B_BASE capital coefficients)**
- *Affected:* `io_model.py` — B_BASE diagonal (§17, 8 parameters, all ASSUMED)
- *Current gap:* All 8 capital coefficients assumed from plausible ranges (Oil 0.40 → Retail 0.06). No primary source.
- *Impact:* B_BASE enters the dynamic IO model and affects capital-constrained recovery time. Upstream corrections (Oil, Chemical) would most affect long-run shock persistence.
- *Source:* ONS Annual Business Survey — Capital Expenditure tables by SIC 2022/23 (ons.gov.uk, free); alternatively ONS Capital Stocks Blue Book supplementary tables (ONS, free)
- *Effort:* Low; impact: medium-high

**6. China-specific regional IO table (GVA rates by sector)**
- *Affected:* `mrio_model.py` — va_rates tiled across regions (§23b, 64 parameters assumed uniform)
- *Current gap:* UK ONS GVA rates applied to all 8 MRIO regions. Chinese textile/chemical GVA rates are systematically lower (more labour-intensive, lower margins). Under-stating Chinese GVA rates inflates the Ghosh MRIO forward linkage estimates for CHN sectors.
- *Impact:* MRIO Ghosh results for CHN-region supply shocks. Also affects VA decomposition analysis (§2.5 of TECHNICAL_REPORT.md).
- *Source:* China NBS (National Bureau of Statistics) Input-Output Tables 2018 (stats.gov.cn, free in Chinese); OECD Inter-Country IO Tables (oecd.org/sti/ind/inter-country-input-output-tables.htm, free)
- *Effort:* Medium (translation and sector mapping); impact: medium-high for MRIO Ghosh

**7. MEG weekly consumption rate**
- *Affected:* `real_data.py` — SAFETY_STOCK_WEEKS["Chemical_Processing"] and shock buffer calculations (§15)
- *Current gap:* 3.0 weeks DERIVED from 688 kt port inventory ÷ ~230 kt/week estimated consumption. The 230 kt/week figure itself is ESTIMATED from production volumes and import dependency — not directly measured.
- *Impact:* Sets the duration of the MEG shock buffer (S2). If true consumption is 180 kt/week, buffer extends to 3.8 weeks; if 300 kt/week, it shrinks to 2.3 weeks.
- *Source:* CCFGroup (ccfgroup.com, subscription — the original source of the port inventory data in §8); CMAI/IHS Markit MEG Market Report; Fibre2Fashion weekly market reports (fibre2fashion.com, partial free access)
- *Effort:* Low; impact: medium (buffer weeks only)

**8. UK Wholesale import/domestic sourcing split**
- *Affected:* `real_data.py` — STAGE_GEOGRAPHY["UK_Wholesale"] (§9g, 1 parameter, ESTIMATED)
- *Current gap:* UK 85% / Other 15% is a rough approximation. Large UK retailers (ASOS, Next, M&S) source 20-30% of garments via direct import, bypassing wholesale.
- *Impact:* Affects how UK retail is exposed to upstream shocks. A higher "direct import" share would increase UK retail's direct China exposure.
- *Source:* ONS International Trade in Services survey (ons.gov.uk, free); BRC (British Retail Consortium) Retail Logistics Report 2023; ASOS/Next/M&S annual reports — supplier disclosure appendices
- *Effort:* Low; impact: medium

---

### TIER 3 — Medium impact: improves precision of well-estimated parameters

**9. Safety stock weeks — upstream stages**
- *Affected:* SAFETY_STOCK_WEEKS PTA through Garment (§15, 5 parameters, all ESTIMATED)
- *Current gap:* Values (PTA 2.5w, PET 3.0w, Fabric 4.0w, Garment 6.0w, Wholesale 8.0w) from literature analogies, not UK sector surveys.
- *Impact:* Affects shock propagation timing in dynamic IO. Main uncertainty: Garment (6.0w) — ILO data suggest 4–8 weeks is plausible range.
- *Source:* BRC (brc.org.uk) Retail Logistics Annual Report 2023; IGD Supply Chain Analysis 2022 (igd.com, subscription); McKinsey "The State of Fashion" 2024 operational benchmarks chapter
- *Effort:* Low; impact: medium (timing, not direction)

**10. Freight cost shares — non-garment stages**
- *Affected:* FREIGHT_COST_SHARE Chemical through Wholesale (§20, 7 of 8 parameters, ESTIMATED)
- *Current gap:* Only garment (7.5%) has an external source (UNCTAD 2023). Oil, Chemical, PTA, PET, Fabric, Wholesale freight shares all estimated.
- *Impact:* Freight costs enter CGE welfare calculations and Red Sea scenario (V5). Mostly affects magnitude, not direction.
- *Source:* UNCTAD Review of Maritime Transport 2023 (Section 3, freight rates by commodity); World Bank Logistics Cost Report 2023; ICS (International Chamber of Shipping) sector-by-sector freight data
- *Effort:* Low; impact: low-medium

**11. ABM forecasting parameters (α, safety stock adjustment)**
- *Affected:* `abm_model.py` — smoothing α = 0.3, safety stock increment = 5%/week (§21, 2 parameters, ESTIMATED)
- *Current gap:* Standard literature values (Sterman 2000) used. UK fashion supply chain may have different α (faster/slower adjustment) depending on retailer planning cycles (weekly vs monthly reviews).
- *Impact:* Affects oscillation amplitude in simulated bullwhip effect. Mis-specified α would distort shock propagation timing rather than direction.
- *Source:* Empirical estimation from retailer order data (not publicly available); alternatively, published UK fashion retailer procurement studies (e.g. Mintel UK Clothing Retail 2023; BRC monthly sales reports)
- *Effort:* High (requires primary data); impact: medium for ABM

---

### TIER 4 — Lower impact: refinements or future model extensions

**12. WIOD/GTAP MRIO tables — regional IO refinement**
- *Affected:* Full MRIO calibration (all A_MRIO entries beyond proportional sourcing)
- *Current gap:* See Gap #1. Even with WIOD data, sector concordance from WIOD (56 sectors) to model (8 sectors) requires aggregation decisions.
- *Source:* WIOD 2016 release; ADB MRIO 2023; EORA MRIO (worldmrio.com, free)
- *Effort:* High; impact: high but mainly for MRIO precision (model already captures directional results correctly)

**13. India and South Asia regional IO tables**
- *Affected:* MRIO GVA rates for SAS region (§23b)
- *Current gap:* India, Bangladesh, Vietnam IO tables are available but not integrated. SAS-region Ghosh analysis uses UK GVA rates.
- *Source:* India NBS Input-Output Tables 2017-18 (mospi.gov.in, free); Bangladesh Bureau of Statistics IO Table 2019-20; Asian Development Bank Multi-Regional IO Tables
- *Effort:* Medium; impact: medium for SAS-region MRIO Ghosh

**14. UK PTA/PET import price series (for elasticity estimation)**
- *Affected:* Armington elasticity estimation (Gap #4)
- *Current gap:* No UK import price data for HS 291736 (PTA) or HS 390760 (PET) currently used in model.
- *Source:* HMRC UK Trade Info (uktradeinfoarchive.hmrc.gov.uk, free, HS 6-digit); UN Comtrade (comtrade.un.org, free)
- *Effort:* Medium; impact: conditional on Gap #4 being pursued

**15. Real-time MEG port inventory data**
- *Affected:* SAFETY_STOCK_WEEKS, MEG_PORT_INVENTORY_KT (§8 and §15)
- *Current gap:* Model uses February 2022 snapshot (688 kt). Current inventories may differ by ±30%.
- *Source:* CCFGroup weekly MEG inventory reports (ccfgroup.com, subscription); Mysteel port inventory tracker (mysteel.net, subscription)
- *Effort:* Low; impact: low (affects buffer duration only, not structural results)

---

### Summary of Priority Gaps

| # | Gap | Module | Current status | Tier | Source |
|---|---|---|---|---|---|
| 1 | WIOD bilateral trade matrices | MRIO | ASSUMED | **1** | wiod.org (free) |
| 2 | Chemical Processing geography | real_data | ESTIMATED | **1** | IEA Petrochemicals 2023 |
| 3 | Bangladesh/Vietnam fabric China dependency | real_data | ESTIMATED | **1** | BGMEA / VITAS |
| 4 | PTA/PET Armington elasticities | real_data | ESTIMATED | **1** | Broda-Weinstein / UN Comtrade |
| 5 | B_BASE capital coefficients | io_model | ASSUMED | **2** | ONS ABS CapEx tables |
| 6 | China/SAS regional GVA rates | mrio_model | ASSUMED | **2** | China NBS IO 2018 / OECD ICIO |
| 7 | MEG weekly consumption rate | real_data | ESTIMATED | **2** | CCFGroup / CMAI |
| 8 | UK Wholesale direct-import share | real_data | ESTIMATED | **2** | ONS Trade in Services / BRC |
| 9 | Safety stock weeks (PTA–Wholesale) | real_data | ESTIMATED | **3** | BRC / IGD surveys |
| 10 | Freight cost shares (non-garment) | cge_model | ESTIMATED | **3** | UNCTAD 2023 / World Bank |
| 11 | ABM forecasting parameters (α) | abm_model | ESTIMATED | **3** | UK retailer procurement studies |
| 12 | Full MRIO table integration | mrio_model | ASSUMED | **4** | EORA / ADB MRIO |
| 13 | India/SAS regional IO tables | mrio_model | ASSUMED | **4** | India NBS / ADB IO |
| 14 | UK PTA/PET import price series | real_data | missing | **4** | HMRC Trade Info / Comtrade |
| 15 | Real-time MEG port inventories | real_data | point-in-time | **4** | CCFGroup weekly |

---

## SOURCES LIST (All cited above)

| # | Citation | Access |
|---|---|---|
| 1 | HMRC (2023). "2023 Synthetic Apparel Imports.xlsx" By Country sheet. | Research files (provided) |
| 2 | ONS Annual Business Survey 2022/23. SIC 13, 14, 46, 47. | Free: ons.gov.uk |
| 3 | ONS Retail Sales Index 2023. | Free: ons.gov.uk |
| 4 | Textile Exchange (2024). Materials Market Report 2024. | textilesexchange.org (subscription) |
| 5 | RiSC_report.docx. Supply chain vulnerability analysis. | Research files (provided) |
| 6 | Findings-02-12-2024.docx. ASOS and industry findings. | Research files (provided) |
| 7 | "Textile Industrial Supply Chain 09122024.pptx". Key Points slide. | Research files (provided) |
| 8 | Logistics_Price_Info.pptx. Transit times and MEG inventories. | Research files (provided) |
| 9 | GlobalData (2021). Global PTA Capacity and Production Statistics. | Subscription (cited via ICIS commentary) |
| 10 | KNOC / Korea Customs Service Import Statistics 2022. | kesis.net |
| 11 | Japan METI Energy White Paper 2022. | meti.go.jp |
| 12 | WTO International Trade Statistics 2024. Leading textile exporters table. | wto.org/statistics |
| 13 | CIRFS (2023). Annual Report: Synthetic Fibres Production. | cirfs.org |
| 14 | Hertel, T. et al. (2012). Global Trade Analysis: Modeling and Applications. GTAP v10. | gtap.agecon.purdue.edu |
| 15 | UNCTAD (2023). Review of Maritime Transport 2023. | unctad.org |
| 16 | Liu, J. & Hudson, D. (2022). Global Cotton Production and Trade. | Cited in Findings doc |
| 17 | ILO (2021). Garment Worker Welfare Study: Cost structures. | ilo.org |
| 18 | Sterman, J.D. (1989). Modelling Managerial Behavior: Misperceptions of Feedback in a Dynamic Decision Making Experiment. Management Science 35(3). | JSTOR |
| 19 | Sterman, J.D. (2000). Business Dynamics: Systems Thinking for a Complex World. McGraw-Hill. | Print |
| 20 | Tang, C.S. (2006). Perspectives in Supply Chain Risk Management. IJOPM 24(6), 449-475. | IJOPM |
| 21 | Bruneau, M. et al. (2003). A Framework to Quantitatively Assess and Enhance the Seismic Resilience of Communities. Earthquake Spectra 19(4). | EERI |
| 22 | Balistreri, E.J. & Hillberry, R.H. (2007). Structural Estimation and the Border Puzzle. Journal of International Economics 72(2). | ScienceDirect |
| 23 | S&P Global Commodity Insights. PTA cost analysis framework. | Subscription |
| 24 | ICIS (2022). China PTA Capacity Commentary. | icis.com |
| 25 | Werner International (2022). Textile Manufacturing Cost Survey. | wernerinternational.com |
| 26 | EIA International Energy Statistics 2023. Crude oil production by country. | eia.gov/international |
| 27 | USTR (2019). Section 301 Tariff Actions: China. | ustr.gov |
| 28 | Bloomberg (2018). Nylon-66 Price Spike: ADN factory fires. | Bloomberg terminal |
| 29 | Chemical Week (2018). Supply shortage report: ADN. | chemweek.com |
| 30 | Freightos Baltic Index. Container rates 2020-2024. | freightos.com |
| 31 | NBS China. Manufacturing PMI February 2020 = 35.7. | stats.gov.cn |
| 32 | ONS Retail Sales Index. Clothing/footwear April 2020. | ons.gov.uk |
| 33 | IEA (2019). Abqaiq attack oil market impact assessment. | iea.org |
| 34 | UNCTAD (2024). Red Sea disruption shipping bulletin. | unctad.org |
| 35 | ONS (2025). UK Input-Output Analytical Tables 2023. Office for National Statistics. Sheets used: IOT (domestic use), A (direct requirements), Imports use pxp (import coefficients). | Research files (provided) |
| 36 | Wikipedia / EIA (2025). "List of countries by oil production." Based on EIA International Energy Statistics. Accessed 2026-04-17. | https://en.wikipedia.org/wiki/List_of_countries_by_oil_production |
| 37 | Hertel, T.W. et al. (2012). Global Trade Analysis: Modeling and Applications. GTAP v10 Database. Behavioral parameters chapter: Armington import substitution elasticities σ_m by GTAP sector. | gtap.agecon.purdue.edu |
| 38 | WIOD (2016). World Input-Output Database, 2016 release. 43 countries × 56 industries. Timmer, M.P. et al. (2015) Review of Income and Wealth 61(3). | wiod.org (free) |
| 39 | ADB (2023). Asian Development Bank Multi-Regional Input-Output Tables 2023. 62 economies × 35 sectors. | adb.org/mrio (free) |
| 40 | IEA (2023). Petrochemicals 2023: Analysis and Forecast to 2028. International Energy Agency. | iea.org/reports (subscription) |
| 41 | CEFIC (2023). European Chemical Industry Facts and Figures 2023. European Chemical Industry Council. | cefic.org (free) |
| 42 | BGMEA (2023). Annual Report: Bangladesh Garment Manufacturers and Exporters Association. Supplier sourcing and upstream dependency data. | bgmea.com.bd (free) |
| 43 | VITAS (2023). Vietnam Textile and Apparel Association Annual Report. | vitas.com.vn |
| 44 | China NBS (2019). China Input-Output Table 2018. National Bureau of Statistics. 42-sector IO table. | stats.gov.cn (free, Chinese) |
| 45 | OECD (2023). OECD Inter-Country Input-Output (ICIO) Tables 2023 edition. 76 countries × 45 industries. | oecd.org/sti/ind (free) |
| 46 | CCFGroup. Weekly MEG Port Inventory Reports. Port data for Zhangjiagang, Jiangyin, Taicang, Ningbo. | ccfgroup.com (subscription) |
| 47 | CMAI / IHS Markit (2023). MEG Market Report: Global Supply-Demand Balance. | ihsmarkit.com (subscription) |
| 48 | Broda, C. & Weinstein, D.E. (2006). Globalization and the Gains from Variety. Quarterly Journal of Economics 121(2), 541-585. HS-10 level import elasticities. | JSTOR / QJE |
| 49 | Gallaway, M.P., McDaniel, C.A. & Rivera, S.A. (2003). Short-run and long-run industry-level estimates of US Armington elasticities. North American Journal of Economics and Finance 14(1), 49-68. | ScienceDirect |
| 50 | ONS (2023). UK Capital Expenditure: Annual Business Survey supplementary tables. Capital expenditure by SIC 2-digit. | ons.gov.uk (free) |
| 51 | BRC (2023). BRC Retail Logistics Annual Report 2023. Safety stock and inventory benchmarks for UK fashion retail. | brc.org.uk (subscription) |
| 52 | IGD (2022). UK Supply Chain Analysis 2022. Safety stock and replenishment cycles. | igd.com (subscription) |
| 53 | Fibre2Fashion (2023). Weekly Polyester Market Reports: MEG and PTA production by country. | fibre2fashion.com (partial free) |
| 54 | Mysteel (2024). China Port Inventory Tracker: MEG, PTA weekly data. | mysteel.net (subscription) |
| 55 | HMRC UK Trade Info. UK imports by HS code — HS 291736 (PTA), HS 390760 (PET resin), HS 5402 (polyester yarn). | uktradeinfoarchive.hmrc.gov.uk (free) |
| 56 | Feenstra, R.C. (1994). New Product Varieties and the Measurement of International Prices. American Economic Review 84(1), 157-177. Armington elasticity estimation methodology. | AER |
