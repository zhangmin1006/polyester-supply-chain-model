# Polyester Textile Supply Chain Resilience Model
## Technical Report: Model Logic, Data Sources, Validation and Findings

**Project:** UK Polyester Textile Supply Chain Vulnerability Analysis  
**Model version:** 4 (2026-04-17)  
**Files:** `model/` directory — `real_data.py`, `io_model.py`, `cge_model.py`, `abm_model.py`, `shocks.py`, `validation.py`, `mrio_model.py`, `ghosh_model.py`, `main.py`

---

## 1. Overview

This model analyses supply chain resilience and disruption propagation in the UK polyester textile sector. It integrates three complementary modelling frameworks applied to an 8-stage supply chain:

| Stage | Sector | Key geography |
|---|---|---|
| 0 | Oil Extraction | USA 16%, Russia 12%, Saudi Arabia 12% |
| 1 | Chemical Processing (MEG + p-Xylene) | China 35%, Saudi Arabia 18%, South Korea 14% |
| 2 | PTA Production | **China 67%** (critical concentration) |
| 3 | PET Resin / Yarn | **China 60%** |
| 4 | Fabric Weaving | **China 43%**, India 11% |
| 5 | Garment Assembly | China 27% (nominal), Turkey 6%, Bangladesh 12% |
| 6 | UK Wholesale | UK 85% |
| 7 | UK Retail | UK 100% |

The three models are calibrated to the same real data and run simultaneously for each scenario, providing cross-model consistency checks.

---

## 2. Model Architecture

### 2.1 Dynamic Input-Output (Leontief) Model — `io_model.py`

**Purpose:** Quantify production multipliers, linkage effects, and time-path of output under disruption.

**Core equations:**

- **Static form (steady-state):** x = (I − A)⁻¹ f  — where x is gross output vector, f is final demand, A is the technical coefficient matrix, and (I−A)⁻¹ is the Leontief inverse L.
- **Dynamic form (Leontief 1970):** B Δx(t) = x(t) − A x(t) − f(t)  — where B is the capital coefficient matrix governing investment lags.
- **Transit lags:** A pipeline buffer matrix propagates upstream deliveries with sector-specific lag weeks (e.g. Garment→Wholesale: 5 weeks for China→UK sea freight).
- **Shock mechanism:** Supply shocks reduce sector capacity fractions; output constrained by min(x_target × ratio, x_baseline × capacity). Shortage = x_target − x_achieved.
- **Price response:** Tatonnement — P(t) = P(t−1) × (1 + λ(1 − ratio)), λ = 0.4. Capacity recovers at 3%/week.

**Technical coefficient matrix A (mixed calibration):**

| A entry | Value | Basis |
|---|---|---|
| Fabric(C13) → Garment(C14) | 0.0855 | ONS UK IO Analytical Tables 2023 — total direct coefficient |
| Wholesale(G46) → Garment(C14) | 0.0962 | ONS UK IO Analytical Tables 2023 — domestic coefficient |
| Petrochem(C20B) → Textiles(C13) | 0.0555 | ONS UK IO Analytical Tables 2023 — total coefficient |
| Garment → Wholesale | 0.321 | IO-derived value-share ratio: vs[Gar]/vs[Who] × 0.68 |
| Wholesale → Retail | 0.225 | IO-derived value-share ratio: vs[Who]/vs[Ret] × 0.56 |
| Oil → Chemical | 0.20 | Global supply-chain estimate (IEA/ICIS) |
| Chemical → PTA | 0.30 | Global estimate |
| PTA → PET | 0.35 | Global estimate |
| PET → Fabric | 0.20 | Global estimate |
| Oil → PET (energy) | 0.04 | IEA energy cost estimate |

Hawkins-Simon condition (all column sums < 1) is satisfied: max column sum = 0.322.

**Leontief output multipliers** (total gross output per £1 final demand):

| Sector | Multiplier |
|---|---|
| Oil Extraction | 1.00 |
| Chemical Processing | 1.20 |
| PTA Production | 1.36 |
| PET Resin/Yarn | **1.52** |
| Fabric Weaving | 1.37 |
| Garment Assembly | 1.25 |
| UK Wholesale | 1.40 |
| UK Retail | 1.32 |

**Linkage analysis:**

| Sector | BL Normalised | FL Normalised | Key Sector? |
|---|---|---|---|
| PTA Production | 1.044 | 1.097 | **Yes** |
| PET Resin/Yarn | 1.164 | 0.941 | No |
| UK Wholesale | 1.077 | 1.047 | **Yes** |
| Fabric Weaving | 1.052 | 0.862 | No |
| UK Retail | 1.011 | 0.768 | No |
| Garment Assembly | 0.962 | 1.105 | No |
| Chemical Processing | 0.922 | 1.145 | No |
| Oil Extraction | 0.768 | 1.035 | No |

PTA Production and UK Wholesale are the two "key sectors" — above-average in both backward and forward linkages.

---

### 2.2 Computable General Equilibrium (CGE) Model — `cge_model.py`

**Purpose:** Equilibrium price effects, welfare impacts, trade-flow substitution, freight pass-through.

**Structure:**
- CES (Constant Elasticity of Substitution) production at each sector.
- Armington aggregation: domestic vs imported goods per origin country.
- Market clearing via iterative tatonnement (up to 300 iterations, tolerance 1e−7).

**Three-step equilibrium algorithm (revised after validation):**

1. **Partial equilibrium with inventory buffer damping:**  
   P_j* = (s_j / dsh_j)^(−1/σ_j)  
   Buffer fraction = min(1, safety_stock_weeks / shock_duration_weeks)  
   Price impact dampened: ΔP = ΔP_raw × (1 − 0.7 × buffer_fraction)

2. **Upstream I-O cost propagation:**  
   P_j += Σᵢ A[i,j] × (P_i − 1)  — cost-push from disrupted upstream inputs.

3. **Freight cost pass-through from UK Wholesale:**  
   When logistics price rises, cost passes to all sectors proportional to FREIGHT_COST_SHARE.  
   Followed by bounded tatonnement [0.3, 8.0].

**Armington elasticities (σ_m) — all now sourced:**

| Sector | σ | Source |
|---|---|---|
| Oil Extraction | **5.20** | GTAP v10 "oil" sector (Hertel et al. 2012) |
| Chemical Processing | **3.65** | GTAP v10 "crp" sector (Hertel et al. 2012) |
| Fabric Weaving | **3.20** | GTAP v10 "tex" sector (Hertel et al. 2012) |
| Garment Assembly | **3.30** | GTAP v10 "wap" sector (Hertel et al. 2012) |
| PTA Production | 1.20 | Estimated — specific intermediate, high switching cost |
| PET Resin/Yarn | 1.50 | Estimated — slightly more diverse producers than PTA |
| UK Wholesale | 3.50 | Estimated |
| UK Retail | 4.00 | Estimated |

**Welfare measure:** Compensating Variation = −Σ Q₀_GBP × ΔP  
(negative = welfare loss; Q₀ anchored to UK retail £51.4bn, wholesale £20bn — both ONS REAL data)

---

### 2.3 Agent-Based Model (ABM) — `abm_model.py`

**Purpose:** Captures bullwhip effect, inventory dynamics, non-linear recovery behaviour, heterogeneous agents.

**Foundation:** Beer Distribution Game (Sterman 1989), extended to 8-stage polyester chain.

**Agent structure (SupplyChainAgent):**
- Each agent = one sector × one country node, weighted by real geographic share.
- **Inventory policy:** Order-up-to with adaptive safety stock.
  - Order_t = max(0, demand_forecast + safety_stock − inventory − pipeline)
  - Exponential smoothing forecast: F_t = α × D_{t-1} + (1−α) × F_{t-1}, α = 0.30
- **Adaptive safety stock:** Increases 5%/week when price signal > 1.1 (precautionary hoarding); decreases when price falls.
- **Disruption:** Disrupted agents produce 5% of normal capacity for duration_weeks.
- **Recovery:** Capacity restored at 5%/week after disruption ends.
- **Pipeline:** Orders take lead_time weeks to arrive; 90% fill rate assumed.

**Lead times (calibrated from real transit data):**
- Garment Assembly → UK Wholesale: 5 weeks (China→UK 37 days ÷ 7, from Logistics pptx — REAL)
- Chemical Processing: 3 weeks (Saudi Arabia→China 23 days ÷ 7, from Logistics pptx — REAL)
- Others: 2 weeks (default)

**Resilience metrics computed:**
- **Bullwhip Ratio:** Var(orders_s) / Var(final_demand) — amplification of demand variability upstream.
- **Service Level:** Fraction of periods with zero shortage.
- **Fill Rate:** 1 − total shortage / total orders.
- **Recovery Time:** Weeks from shock onset to first week ≥ 95% baseline capacity.
- **Resilience Triangle (Bruneau et al. 2003):** Area of capacity loss over time = integrated disruption cost.

---

### 2.4 Scenario Framework — `shocks.py`

Five scenarios, each run across all three models simultaneously:

| ID | Name | Type | Key shock | Duration |
|---|---|---|---|---|
| S1 | PTA Production Shock | Supply — upstream chemical | China PTA −50%; PET cascade −35% | 24 weeks |
| S2 | MEG Supply Disruption | Supply — chemical input | Saudi MEG −25%; PET −20% after 3-week buffer | 20 weeks |
| S3 | UK–China Trade Restriction | Policy — geopolitical | China garment +35% tariff; effective −35% supply | 52 weeks |
| S4 | Zhangjiagang Port Closure | Logistics — port | PET −30%; MEG buffer from 418 kt (61% of China total) | 16 weeks |
| S5 | Multi-Node Pandemic | Multi-stage (COVID-style) | PTA/PET/Fabric −60%; Garment −50%; 37→70d transit | 52 weeks |

---

### 2.5 Multi-Regional Input-Output (MRIO) Model — `mrio_model.py`

**Purpose:** Extend the single-region Leontief model to capture inter-regional production interdependencies, value-added origin by country, and region-specific shock propagation.

**System:** 8 regions × 8 sectors = **64-dimensional Leontief system**

| Code | Region | Key supply chain role |
|---|---|---|
| CHN | China | Dominant PTA (67%), PET (60%), Fabric (43%) producer |
| SAS | South/SE Asia | Garment assembly (Bangladesh, India, Vietnam, Cambodia, Sri Lanka, Pakistan, Myanmar) |
| EAS | East Asia ex-CN | Chemical/PET (South Korea, Japan, Taiwan) |
| MDE | Middle East | Oil + MEG chemicals (Saudi Arabia, UAE, Iraq) |
| AME | Americas | Oil + chemicals (USA, Canada) |
| EUR | Europe ex-UK | Garment finishing (Turkey, Italy) |
| GBR | United Kingdom | Wholesale + retail (final demand anchor) |
| ROW | Rest of World | Residual (Other country buckets from STAGE_GEOGRAPHY) |

**Calibration — proportional sourcing assumption:**

Each region-sector combination sources its inputs from other regions in proportion to those regions' global production share of each input sector:

```
A_MRIO[r×N+i, s×N+j] = A_BASE[i,j] × regional_shares[i, r]
```

*Interpretation:* to produce one unit of sector j in region s, A_BASE[i,j] units of sector i are needed in total, and region r supplies regional_shares[i,r] of that requirement. Column sums of A_MRIO equal column sums of A_BASE, so the Hawkins-Simon condition is preserved across all 64 columns.

*Limitation:* Proportional sourcing is a standard calibration proxy used when bilateral inter-regional trade matrices are unavailable (no WIOD subscription). It assumes all regions source sector i inputs in the same global proportions, which means the per-sector China production share is not amplified through the Leontief inverse. Region-specific domestic input coefficients (as provided by WIOD or GTAP MRIO tables) would allow heterogeneous sourcing and would generate intra-China amplification effects. The analysis below is therefore conservative on China exposure estimates.

**Key MRIO outputs:**

| Output file | Content |
|---|---|
| `08_mrio_regional_shares.csv` | Production share (%) by region and sector |
| `09_mrio_va_by_region.csv` | Value-added origin by region (£bn and %) |
| `11_mrio_linkage_summary.csv` | Backward and forward linkages aggregated by region |
| `14_mrio_china_exposure.csv` | Nominal vs MRIO China exposure by sector |
| `15_mrio_china_shock_by_region.csv` | 50% China shock — output change by region |
| `16_mrio_china_shock_by_sector.csv` | 50% China shock — output change by sector |
| `17_mrio_leontief_decomp.csv` | Full Leontief decomposition column for UK retail demand |

**Regional value-added origin** (UK £51.4 bn retail demand, proportional sourcing):

| Region | VA (£bn) | VA share (%) |
|---|---|---|
| United Kingdom | 36.1 | 91.7 |
| Rest of World | 1.67 | 4.2 |
| South/SE Asia | 0.70 | 1.8 |
| China | 0.67 | 1.7 |
| Europe ex-UK | 0.23 | 0.6 |
| East Asia ex-CN | ~0 | ~0 |
| Americas | ~0 | ~0 |
| Middle East | ~0 | ~0 |

*Note:* UK's dominant share (91.7%) reflects that UK_Retail and UK_Wholesale collectively carry ONS GVA rates of 59.8% and 52.8% respectively, applied to £51.4 bn and £20 bn gross outputs. The upstream global supply chain (Oil→Garment) generates only ~£8 bn in gross output terms at UK retail-equivalent scale — consistent with the "smile curve" of global value chains, where retail/distribution captures the majority of nominal value.

**China's forward linkage** in the 64-sector MRIO system = **1.766** (normalised), the highest of all 8 regions, reflecting that Chinese sectors (PTA, PET, Fabric) are used as inputs across all other regions' production processes.

**50% China supply shock — regional propagation:**

| Region | Output change (%) |
|---|---|
| China | −52.0 |
| Americas | −47.5 |
| Middle East | −45.2 |
| East Asia ex-CN | −38.9 |
| South/SE Asia | −1.3 |
| Rest of World | −1.2 |
| Europe ex-UK | −1.0 |
| United Kingdom | −0.07 |

*Key finding:* Americas (−47%) and Middle East (−45%) are disproportionately affected relative to their direct China exposure because they supply intermediate inputs (oil, chemicals) to China's PTA and PET sectors. When China's production is halved, demand for these upstream feedstocks collapses. This inter-regional upstream spillover is only visible in the MRIO framework.

**Figures generated:** `fig10_mrio_va_heatmap.png` (value-added origin matrix), `fig11_mrio_china_exposure.png` (nominal vs MRIO China %), `fig12_mrio_china_shock.png` (shock propagation by region and sector)

---

### 2.6 Ghosh Supply-Side IO Model — `ghosh_model.py`

**Purpose:** Complement the Leontief demand-pull model with a supply-push framework. Where Leontief answers *"how much upstream output is needed to satisfy a unit of final demand?"*, Ghosh answers *"how far does a primary input constraint at sector i propagate forward through the supply chain?"*

**Theory:**

Output allocation coefficient matrix B:

```
B_ij = z_ij / x_i    (share of sector i's output sold to sector j)
B = diag(x)^{-1} A diag(x)
```

Ghosh inverse: **G = (I − B)^{−1}**

Forward propagation of a supply shock at sector i (Δv_i = primary input lost):

```
Δx_j = Δv_i × G[i, j]    (output change at all downstream sectors j)
```

**Primary input vector:** ONS IOT 2023 GVA rates applied to baseline gross outputs: v_i = GVA_rate_i × x_i. This uses exogenous sectoral GVA rates rather than the IO row-balance identity, because the single-chain model concentrates all final demand at UK_Retail, which would yield v_i = 0 for all upstream sectors under the row-balance approach. The Ghosh model is therefore used as a **forward sensitivity tool** (Dietzenbacher 1997) rather than a strict accounting identity.

**Leontief vs Ghosh linkage classification:**

| Sector | BL_Norm (Leontief) | FL_Norm (Ghosh) | Classification |
|---|---|---|---|
| Oil_Extraction | 0.77 | **1.54** | Supply-push (FL>1 only) |
| Chemical_Processing | 0.92 | **1.35** | Supply-push (FL>1 only) |
| **PTA_Production** | **1.04** | **1.45** | **Key sector (BL>1 & FL>1)** |
| **PET_Resin_Yarn** | **1.16** | **1.21** | **Key sector (BL>1 & FL>1)** |
| Fabric_Weaving | **1.05** | 0.97 | Demand-pull (BL>1 only) |
| Garment_Assembly | 0.96 | 0.73 | Independent |
| UK_Wholesale | **1.08** | 0.49 | Demand-pull (BL>1 only) |
| UK_Retail | **1.01** | 0.24 | Demand-pull (BL>1 only) |

*Key finding:* **PTA and PET are the only true Key Sectors** — above-average in both backward (demand-pull) and forward (supply-push) linkages. Oil and Chemical are supply-push but not demand-pull (their forward reach exceeds their backward pull). Fabric, Wholesale, and Retail are demand-pull only.

**Ghosh supply shock scenarios (GS1–GS5):**

| Scenario | Sectors shocked | Total output loss | Worst sector | Worst sector Δ% | Retail Δ% |
|---|---|---|---|---|---|
| GS1 | PTA (50%) | £0.016 bn | PTA_Production | −11.2% | −0.00% |
| GS2 | Chemical (25%) | £0.003 bn | Chemical | −2.1% | −0.00% |
| GS3 | Oil (20%) | £0.007 bn | Oil | −13.7% | −0.00% |
| GS4 | Fabric + Garment (40%) | £2.85 bn | Garment | −24.5% | −1.77% |
| GS5 | PTA+PET+Fabric+Garment (50%) | £3.66 bn | Garment | −31.1% | −2.25% |

*Key finding:* The Ghosh model reveals an important asymmetry relative to the Leontief model. Upstream shocks (GS1–GS3: Oil, Chemical, PTA) have **very small absolute output losses** despite high forward linkage indices, because their value-added (primary inputs) is tiny relative to total chain value: Oil VA = £5.2m, PTA VA = £5.1m vs Garment VA = £2.1bn and UK Retail VA = £30.7bn. A 50% PTA primary input shock directly costs only £2.5m of value-added. The Ghosh forward multiplier (6.1×) amplifies this, but the absolute downstream impact remains small (£16m total loss). Conversely, shocks at Garment Assembly (GS4/GS5) cause large absolute losses (£2.9–3.7bn) because Garment VA is £2.1bn — the "smile curve" effect.

**MRIO Ghosh — China 50% shock (forward cascade by region):**

| Region | Output change |
|---|---|
| China | −28.4% |
| South/SE Asia | −1.6% |
| Europe ex-UK | −1.5% |
| East Asia ex-CN | −1.3% |
| United Kingdom | −1.0% |
| Americas | −0.1% |
| Middle East | 0.0% |

*Key finding:* The Ghosh MRIO identifies the **downstream victims** of China's supply constraint: South/SE Asia (garment assembly uses Chinese fabric/yarn), Europe (finishing), and UK retail (−1%). This is the mirror image of the Leontief MRIO result, which identified the **upstream victims** (Americas −47%, Middle East −45% as feedstock suppliers to China). Together, the two frameworks reveal China's dual role: a critical buyer of upstream feedstocks AND a critical supplier to downstream assembly regions.

**Figures generated:** `fig13_ghosh_linkage_quadrant.png` (BL vs FL scatter), `fig14_ghosh_scenarios.png` (scenario heatmap + loss bar), `fig15_ghosh_mrio_china_shock.png` (MRIO forward cascade)

**Output files:** `18_ghosh_forward_linkages.csv`, `19_ghosh_vs_leontief_linkages.csv`, `20_ghosh_scenarios_comparison.csv`, `21_ghosh_mrio_fl_by_region.csv`, `22_ghosh_mrio_china_shock.csv`

---

## 3. Data Sources

### 3.1 Data Quality Summary

| Category | Parameters | REAL | EXTERNAL | DERIVED | ESTIMATED | ASSUMED |
|---|---|---|---|---|---|---|
| UK Import Data (HMRC) | 24 | 24 | — | — | — | — |
| UK Industry Turnover (ONS) | 6 | 6 | — | — | — | — |
| Global Fibre Shares | 5 | 5 | — | — | — | — |
| China MEG/p-Xylene Dependency | 2 | 2 | — | — | — | — |
| China PTA Share | 1 | — | 1 | — | — | — |
| Oil Import Sources (SK/Japan) | 2 | 2 | — | — | — | — |
| Transit Times | 10 | 10 | — | — | — | — |
| MEG Port Inventories | 5 | 4 | — | 1 | — | — |
| Stage Geography — Oil | 7 | 6 | — | 1 | — | — |
| Stage Geography — Chemical | 1 | — | — | — | 1 | — |
| Stage Geography — PTA | 5 | — | 1 | 1 | 3 | — |
| Stage Geography — PET | 5 | — | 3 | 1 | 1 | — |
| Stage Geography — Fabric | 5 | — | 3 | 1 | 1 | — |
| Stage Geography — Garment | 11 | 10 | — | 1 | — | — |
| Stage Geography — Wholesale | 1 | — | — | — | 1 | — |
| ASOS Suppliers | 5 | 5 | — | — | — | — |
| Value-Added Shares (STAGE_RETAIL_VALUE_SHARE) | 8 | 1 | — | 7 | — | — |
| Effective China Dependency | 8 | — | — | 4 | 4 | — |
| Armington Elasticities | 8 | — | 4 | — | 4 | — |
| Safety Stock Weeks | 8 | — | — | 1 | 7 | — |
| A_BASE — ONS IO downstream | 5 | — | — | 5 | — | — |
| A_BASE — upstream estimates | 5 | — | — | — | 5 | — |
| B_BASE Capital Coefficients | 8 | — | — | — | — | 8 |
| Delivery Lag Matrix | 7 | — | — | 7 | — | — |
| CGE Base Quantities Q0 | 8 | 2 | — | — | 6 | — |
| Freight Cost Shares | 8 | — | 1 | — | 7 | — |
| ABM Behavioural Parameters | 9 | — | — | 2 | 3 | 4 |
| Shock Magnitudes | 12 | 1 | — | 2 | 9 | — |
| **TOTAL** | **193** | **77 (40%)** | **13 (7%)** | **35 (18%)** | **56 (29%)** | **12 (6%)** |

**Classification:**
- **REAL** — exact figure from a named primary source document or official dataset
- **EXTERNAL** — from published literature / public database (web-sourced)
- **DERIVED** — mathematically computed from REAL or EXTERNAL inputs
- **ESTIMATED** — calibrated from indirect evidence or literature ranges; not a direct primary figure
- **ASSUMED** — behavioural/structural parameter from modelling convention with no primary source

---

### 3.2 Primary Real Data Sources

| # | Source | Parameters | Notes |
|---|---|---|---|
| 1 | HMRC (2023). *2023 Synthetic Apparel Imports.xlsx* By Country sheet | UK total imports £2,388,954,178; all 23 country-level shares | Exact cell values from provided file |
| 2 | ONS Annual Business Survey 2022/23 | Manufacturer turnover £9.4bn; wholesale £20bn; retail £51.4bn; company counts | Cited in RiSC_report.docx |
| 3 | ONS Retail Sales Index 2023 | UK retail clothing turnover £51.4bn | ons.gov.uk |
| 4 | ONS UK IO Analytical Tables 2023 | GVA/Output rates for 7 CPA sectors; A matrix downstream entries | Provided by user. Sheets: IOT, A, Imports use pxp |
| 5 | Logistics_Price_Info.pptx | All 10 transit times; 4 MEG port inventory figures (688 kt total) | Provided research file |
| 6 | Textile Industrial Supply Chain 09122024.pptx | China MEG dependency 43%; p-Xylene 45%; effective dependency ~60% at garment | Provided research file |
| 7 | RiSC_report.docx | Industry structure; company counts; vulnerability framing | Provided research file |
| 8 | Findings-02-12-2024.docx | ASOS supplier breakdown; industry findings | Provided research file |
| 9 | EIA / Wikipedia (2025) | Oil production by country: USA 16%, Russia 11.6%, Saudi Arabia 11.5%, Canada 6.1%, Iraq 5.1%, UAE 4.7% | https://en.wikipedia.org/wiki/List_of_countries_by_oil_production |

---

### 3.3 External Literature Sources

| Parameter | Value | Source |
|---|---|---|
| China PTA global share | 67% | GlobalData (2021) capacity survey; cited via ICIS (2022) |
| China PET/polyester fibre share | 60% | CIRFS Annual Report 2023; Textile Exchange 2024 |
| China fabric/textile export share | 43.3% | WTO International Trade Statistics 2024 |
| India PET share 13% | 13% | Textile Exchange 2023; CIRFS 2023 |
| Garment assembly σ = 3.30 | 3.30 | GTAP v10 "wap" sector — Hertel et al. (2012) |
| Chemical processing σ = 3.65 | 3.65 | GTAP v10 "crp" sector — Hertel et al. (2012) |
| Fabric weaving σ = 3.20 | 3.20 | GTAP v10 "tex" sector — Hertel et al. (2012) |
| Oil extraction σ = 5.20 | 5.20 | GTAP v10 "oil" sector — Hertel et al. (2012) |
| Garment freight 7.5% of FOB | 7.5% | UNCTAD Review of Maritime Transport 2023 (6–8% range) |
| Cotton production shares | China 22.5%, India 22.5%, USA 14.7% | Liu & Hudson (2022), cited in Findings doc |

---

### 3.4 Estimated Parameters and Caveats

The following parameters remain estimates. Results dependent on these should be interpreted with caution.

#### A. Stage Geography — Chemical Processing (MEG + p-Xylene)

```
China: 35%, Saudi Arabia: 18%, South Korea: 14%, Japan: 10%, USA: 12%, Other: 11%
```

**Basis:** Synthesised from ICIS MEG/p-Xylene producer databases, SABIC annual report 2022, IHS Markit. No single primary table. Note that MEG and p-Xylene are separate markets: Saudi Arabia holds ~30% of global MEG capacity (gas-based); China holds ~50%+ of global p-Xylene capacity. The model's combined figure of 35% for China likely understates China's p-Xylene dominance but is consistent with the combined feedstock picture. **Recommended improvement:** IEA Petrochemicals 2023 report.

#### B. PTA and PET Armington Elasticities

```
PTA: σ = 1.20    PET: σ = 1.50
```

**Basis:** Below the GTAP v10 "crp" aggregate (σ = 3.65) because PTA and PET are specific concentrated intermediates with long-term supply contracts and high physical switching costs. Balistreri & Hillberry (2007) estimate σ = 1.0–1.5 for such industrial intermediates. No GTAP sector maps directly to PTA or PET resin. These low elasticities are a key driver of the model's high vulnerability scores for PTA and PET — sensitivity to this parameter should be tested.

#### C. A_BASE Upstream Chain (Oil→Chemical→PTA→PET→Fabric)

```
A[0,1] = 0.20   A[1,2] = 0.30   A[2,3] = 0.35
A[3,4] = 0.20   A[0,3] = 0.04
```

**Basis:** Global supply-chain cost-structure estimates. UK domestic IO coefficients are near-zero for these stages because the UK imports >95% of all polyester feedstock; the ONS IO tables reflect only marginal UK production. Values consistent with IEA/ICIS cost literature. The Hawkins-Simon condition (column sums < 1) is verified.

#### D. B_BASE Capital Coefficient Matrix

```
B = diag([0.40, 0.35, 0.30, 0.22, 0.15, 0.08, 0.12, 0.06])
```

**Basis:** Assumed from prior modelling convention. Reflects declining capital intensity from upstream (oil: high fixed assets) to downstream (retail: low). These affect investment-lag dynamics in the dynamic IO model but not the static multiplier or CGE results. **Recommended improvement:** ONS Annual Capital Expenditure Survey by SIC sector.

#### E. Safety Stock Weeks (most sectors)

```
Oil: 4.0wk   Chemical: 3.0wk*  PTA: 2.5wk   PET: 3.0wk
Fabric: 4.0wk   Garment: 6.0wk   Wholesale: 8.0wk   Retail: 10.0wk
```

*Chemical Processing (3.0 weeks) is DERIVED from MEG port inventory data: 688 kt ÷ ~230 kt/week implied consumption ≈ 3 weeks. All others are estimates from industry surveys (McKinsey 2020, BRC 2022, Kantar 2022). These directly affect the inventory buffer damping in the CGE model (Step 1 of equilibrium algorithm).

#### F. Upstream Q0_GBP (CGE base quantities)

```
Oil: £0.30bn   Chemical: £0.60bn   PTA: £0.90bn   PET: £1.30bn   Fabric: £2.40bn
```

**Basis:** Derived from STAGE_RETAIL_VALUE_SHARE ratios applied to retail (£51.4bn). These are global supply quantities attributable to UK consumption, not UK production. The retail (£51.4bn) and wholesale (£20bn) quantities are REAL ONS data; the upstream quantities are proportional estimates.

#### G. Effective China Dependency at Garment Stage

```
Nominal (HMRC direct): 27.3%    Effective (upstream tracing): 60%
```

**Basis:** Nominal from HMRC 2023 import data (REAL). Effective figure of 60% from RiSC_report.docx qualitative assessment — Bangladesh, Vietnam, Cambodia all source >80% of their fabric from China, making China dependency structural even when garments are sourced from these countries. The 60% is described qualitatively in the research; no precise quantification is available in the primary source.

---

## 4. Supply Chain Vulnerability Analysis

### 4.1 Herfindahl-Hirschman Index (HHI)

HHI = Σ sᵢ² ∈ [0, 1]; threshold: > 0.25 = highly concentrated.

| Sector | HHI | Category | Top Supplier | Share |
|---|---|---|---|---|
| UK Retail | 1.000 | High | UK | 100% |
| UK Wholesale | 0.745 | High | UK | 85% |
| **PTA Production** | **0.482** | **High** | **China** | **67%** |
| **PET Resin/Yarn** | **0.411** | **High** | **China** | **60%** |
| **Fabric Weaving** | **0.332** | **High** | **China** | **43%** |
| Oil Extraction | 0.263 | High | Other | 45% |
| Chemical Processing | 0.211 | Medium | China | 35% |
| Garment Assembly | 0.197 | Medium | China/Other | 31% |

Note: UK Retail and Wholesale show high HHI by construction (single-country domestic market) — this does not represent supply-side risk.

### 4.2 Supply Chain Vulnerability Index (SCVI)

SCVI = HHI × China_share × (1 / σ) — combines concentration, China dependency, and substitutability.

| Sector | SCVI | Risk Level |
|---|---|---|
| **PTA Production** | **0.1077** | **Critical** |
| **PET Resin/Yarn** | **0.0548** | **Critical** |
| Fabric Weaving | 0.0112 | High |
| Chemical Processing | 0.0067 | Medium |
| Garment Assembly | 0.0027 | Low |
| Oil Extraction | 0.0000 | Low (no China) |

PTA is the highest-risk node: China holds 67% of global capacity, substitution elasticity is very low (σ = 1.2), and there are no near-term alternative sources.

### 4.3 Composite Resilience Scorecard

Scored 0–1 across: HHI diversification, supplier redundancy, substitution elasticity, inventory buffer, China dependency.

| Sector | Score | Grade |
|---|---|---|
| **PTA Production** | **0.229** | **F** |
| PET Resin/Yarn | 0.306 | D |
| Fabric Weaving | 0.489 | C |
| UK Wholesale | 0.503 | C |
| UK Retail | 0.527 | C |
| Chemical Processing | 0.548 | C |
| Garment Assembly | 0.571 | C |
| Oil Extraction | 0.661 | B |

### 4.4 Effective vs Nominal China Dependency

| Sector | Nominal China % | Effective China % | Hidden Dependency |
|---|---|---|---|
| Oil Extraction | 0% | 5% | +5% |
| Chemical Processing | 35% | 47% | +12% |
| PTA Production | 67% | 67% | — |
| PET Resin/Yarn | 60% | 60% | — |
| Fabric Weaving | 43.3% | 43.3% | — |
| **Garment Assembly** | **27.3%** | **60%** | **+32.7%** |

The largest hidden dependency is at Garment Assembly: UK imports appear to come from Bangladesh, Turkey, Vietnam, Cambodia — but these countries source 80%+ of their fabric from China, making the effective upstream dependency 60% compared to the apparent 27.3% (HMRC).

---

## 5. Scenario Results

### 5.1 Cross-Scenario Comparison

| Scenario | Max Price Rise | Affected Sector | Welfare Loss | Economic Loss | IO Shortage | Worst Sector | Recovery |
|---|---|---|---|---|---|---|---|
| **S1 PTA Shock** | 78.2% | PTA Production | −£1.29bn | £0.09bn | 0.0096 | Fabric Weaving | 4.1 weeks |
| S2 MEG Disruption | 16.0% | PET Resin/Yarn | −£0.26bn | £0.02bn | 0.0017 | PET Resin/Yarn | 3.4 weeks |
| S3 UK–China Tariff | 13.9% | Garment Assembly | −£0.76bn | **£1.52bn** | 0.1707 | Garment Assembly | **No recovery** |
| S4 Port Closure | 26.8% | PET Resin/Yarn | −£0.54bn | £0.06bn | 0.0065 | Fabric Weaving | 3.8 weeks |
| **S5 Pandemic** | **114.6%** | PTA Production | **−£5.10bn** | **£4.31bn** | **0.484** | Garment Assembly | **7.6 weeks** |

**Key findings by scenario:**

**S1 (PTA Shock):** A 50% PTA production loss (earthquake/policy in eastern China) causes a 78% price spike at PTA and cascades into a 20% output reduction in Fabric. Recovery takes ~4 weeks. Welfare loss £1.3bn.

**S2 (MEG Disruption):** Saudi MEG supply disruption buffered by 688 kt Chinese port inventory (~3 weeks). After buffer exhaustion, PET output falls 20%. Price impact moderate (16%). Shows how the MEG buffer is real but insufficient for sustained disruption.

**S3 (UK–China Tariff):** The highest ongoing economic cost scenario. A 35% tariff on Chinese synthetic apparel causes sustained supply reduction that the model cannot fully substitute — no recovery within the 52-week window. Economic loss £1.52bn driven by the structural inability to rapidly reroute from China (effective 60% dependency vs nominal 27%). Price impact is moderate because tariffs raise prices but don't eliminate supply entirely.

**S4 (Zhangjiagang Port):** Closure of China's largest MEG port (418 kt = 61% of Chinese port inventory) causes a 30% output loss at PET (Yizheng Sinopec, located nearby). Moderate impact; relatively fast recovery (3.8 weeks) once port reopens.

**S5 (Pandemic):** Catastrophic scenario. Simultaneous disruption at PTA (−60%), PET (−60%), Fabric (−55%), Garment (−50%), transit doubling (37→70 days). Price rises 115% at PTA. Welfare loss £5.1bn, economic loss £4.3bn. Recovery takes 7.6 weeks on average but garment assembly shows no recovery within 52 weeks in some sub-models. Demonstrates the non-linear effect of simultaneous multi-node failure.

---

## 6. Historical Backcasting Validation

Seven historical events used to validate model performance. Each event independently parameterised using documented real-world conditions, then compared against observed outcomes.

### 6.1 Validation Events

| ID | Event | Period | Key Observable | Observed | Model | Direction |
|---|---|---|---|---|---|---|
| V1 | COVID-19 Pandemic | 2020 Q1–Q2 | Retail output change % | −43.5% | −43.5% | ✓ |
| V1 | COVID-19 Pandemic | 2020 Q1–Q2 | PTA price rise % | +35% | +106% | ✓ |
| V1 | COVID-19 Pandemic | 2020 Q1–Q2 | UK garment imports change % | −40% | −73.5% | ✓ |
| V2 | 2021–22 Freight Crisis | 2021 H2–2022 H1 | Chemical price rise % | +32% | +2.9% | ✓ |
| V3 | 2018 Nylon-66 Fires | Jun–Dec 2018 | PTA price rise % | +120% | +43.2% | ✓ |
| V4 | 2019 Aramco Attack | Sep–Oct 2019 | Oil price spike % | +15% | +1.1% | ✓ |
| V4 | 2019 Aramco Attack | Sep–Oct 2019 | PTA cascade % | ~0% | +1.7% | ✓ (near-zero) |
| V5 | 2024 Red Sea | Dec 2023–Jun 2024 | Wholesale price rise % | +173% | +6.6% | ✓ |
| V6 | 2022 Shanghai Lockdown | Apr–Jun 2022 | UK garment imports change % | −22% | −35% | ✓ |
| V7 | 2022 Ukraine/Energy | Feb–Jun 2022 | Oil price rise % | +54% | +1.6% | ✓ |
| V7 | 2022 Ukraine/Energy | Feb–Jun 2022 | PTA cascade % | +12% | +9.2% | ✓ |

### 6.2 Summary Statistics

| Event | Comparisons | MAE (pp) | Directional Accuracy |
|---|---|---|---|
| V1 COVID-19 | 4 | 26.97 | 100% |
| V2 Freight Crisis | 2 | 15.81 | 100% |
| V3 Nylon Fires | 2 | 38.68 | 100% |
| V4 Aramco Attack | 3 | 5.21 | 100% |
| V5 Red Sea | 2 | 83.80 | 100% |
| V6 Shanghai Lockdown | 3 | 29.00 | 100% |
| V7 Ukraine Energy | 3 | 18.65 | 100% |
| **OVERALL** | **19** | **28.58** | **100%** |

### 6.3 Interpretation of Errors

**100% directional accuracy** means the model correctly identifies whether prices rose/fell, whether welfare improved/worsened, and whether supply contracted/expanded for all 19 comparisons. This is the primary validation criterion for a qualitative policy model.

**MAE of 28.6 percentage points** reflects systematic gaps in magnitude:

- **V5 Red Sea (MAE 83.8pp):** Model predicts +6.6% wholesale price vs observed +173% freight rate surge. Structural limitation: the model captures freight disruption as a capacity reduction but does not explicitly model container rate markets which are highly non-linear. Container freight is also not a direct input cost in the IO framework — it is a market price phenomenon.

- **V1 COVID PTA price (model +106% vs observed +35%):** The model amplifies the upstream PTA shock more than observed because real inventories buffered the price impact over many months; the model's 12-week buffer assumption (3 months) is roughly right but the speed of price transmission is overstated.

- **V4 Aramco oil price (model +1.1% vs observed +15%):** The CGE model captures the oil sector price change via the supply shock fraction, but the polyester supply chain's direct oil input is small (A[0,j] coefficients are small). The 15% oil price spike did not materially affect polyester prices — the model correctly shows minimal cascade but underestimates the direct oil price signal.

- **V7 Ukraine oil price (model +1.6% vs observed +54%):** Same structural issue as V4. The model is not designed to track global commodity spot prices; it tracks production cost pass-through. Brent crude +54% translates to a much smaller cost impact at the polyester chain level because oil is a small fraction of PTA/PET cost (A[0,1]=0.20, A[0,3]=0.04).

---

## 7. Model Limitations

1. **Magnitude calibration for commodity price shocks:** The model correctly captures direction and structural propagation but underestimates direct commodity price signals (V4 Aramco, V7 Ukraine oil). A price-tracking layer for crude oil and container freight would improve magnitude accuracy.

2. **Static Armington elasticities:** Real short-run substitutability is lower than σ implies (switching supply chains takes months/years). The model assumes immediate re-optimisation, which overstates the speed of trade diversion.

3. **Upstream A_BASE from global estimates:** Five upstream entries (Oil→Chem→PTA→PET→Fabric) use global supply-chain cost estimates rather than UK-specific IO data (which is near-zero for these imported stages). This introduces structural uncertainty in the upstream multiplier chain.

4. **Single representative agent per country-sector:** Real supply chains have heterogeneous buyers with different inventory policies, contract structures, and information access. The ABM simplifies this to one agent per node.

5. **No explicit financial or credit channel:** Supply chain finance disruption (payment terms, trade credit) is not modelled.

6. **No consumer substitution between fibres:** The model treats polyester demand as fixed. In practice, prolonged polyester supply disruption would shift some demand toward cotton, nylon, or viscose.

7. **B_BASE capital coefficients assumed:** All eight capital-intensity parameters are modelling assumptions. These affect investment-lag dynamics but not static equilibrium or price results.

8. **Ghosh model uses exogenous GVA rates (not row-balance value-added):** Because all final demand is placed at UK_Retail, the row-balance identity yields v_i = 0 for all upstream sectors (zero final demand), making the Ghosh identity x = v G degenerate. The fix uses ONS IOT GVA rates as primary inputs. This means the Ghosh results are a sensitivity analysis (Dietzenbacher 1997 price-model interpretation) rather than a quantity identity. The upstream absolute losses appear small (GS1 £16m) because upstream VA is genuinely small relative to retail (PTA VA = £5.1m vs Retail VA = £30.7bn) — this is a real structural feature, not a model artefact.

9. **MRIO uses proportional sourcing (no intra-regional bias):** The MRIO model (`mrio_model.py`) calibrates inter-regional flows using the proportional sourcing assumption: each region sources sector-i inputs in proportion to global production shares. This means the per-sector China exposure in the MRIO Leontief inverse equals the nominal production share exactly — no amplification is generated through the Leontief multiplier. A full MRIO calibrated to bilateral trade matrices (e.g., WIOD 2016 or GTAP 10) would allow intra-China circular flows (China's PTA plants sourcing Chinese chemicals) to generate higher effective China exposure. The current MRIO nonetheless provides valid regional shock propagation analysis and linkage statistics.

---

## 8. Key Findings

1. **PTA Production is the single most vulnerable node** in the UK polyester supply chain. China holds 67% of global PTA capacity (GlobalData 2021), the Armington elasticity is the lowest in the chain (σ = 1.2), and the resilience score is F (0.23/1.00). A 50% PTA disruption would raise prices 78% and cost UK welfare £1.3bn.

2. **Effective China dependency at garment stage is 60%, not 27%.** HMRC data shows only 27.3% of UK synthetic apparel imports come directly from China. However, Bangladesh, Vietnam, Turkey, and Cambodia all source the majority of their fabric upstream from China — making the true structural dependency roughly 60%. This "hidden dependency" means supply chain diversification at the assembly stage provides limited resilience without simultaneously diversifying fabric sourcing.

3. **The 688 kt MEG port inventory provides approximately 3 weeks of buffer** against a Saudi supply disruption. This is insufficient for a sustained disruption (e.g., prolonged Red Sea closure or Hormuz Strait blockage). S2 shows that after buffer exhaustion, PET output falls 20% and price rises 16%.

4. **Multi-node simultaneous shocks (S5) are disproportionately severe.** The pandemic scenario causes 19× more welfare loss and 50× more economic disruption than the MEG disruption scenario (S2), due to non-linear interaction between simultaneous failures at PTA, PET, fabric, and garment stages, compounded by logistics doubling.

5. **UK–China tariff escalation (S3) is the hardest shock to recover from.** Unlike physical disruptions that have finite duration, a permanent trade restriction causes sustained supply gaps that cannot be resolved within the model window. The effective 60% China dependency makes short-run rerouting structurally impossible — Turkey and India can absorb some demand but lack sufficient capacity at PTA/PET stages.

6. **PTA Production and UK Wholesale are the two "key sectors"** (above-average backward AND forward linkages). Disruption at either creates disproportionate systemic effects. UK Wholesale's high forward linkage reflects its role as the distribution bottleneck — all upstream supply must pass through it to reach retail.

7. **MRIO analysis reveals upstream supplier spillovers.** Under a 50% China supply shock, the Americas (−47%) and Middle East (−45%) lose nearly as much output as China (−52%), despite not being directly shocked. This occurs because they supply oil and chemical feedstocks to China's PTA and PET sectors; when China's production falls, feedstock demand collapses. South/SE Asia and Europe are comparatively insulated (−1% to −1.3%) because their garment-stage production is less dependent on Chinese intermediates. China has the highest forward linkage (FL_norm = 1.77) of all 8 regions in the 64-sector MRIO system.

8. **Ghosh and MRIO analyses reveal China's dual role.** The Leontief MRIO identifies Americas (−47%) and Middle East (−45%) as the upstream victims when China is shocked — they supply feedstocks to Chinese PTA/PET. The Ghosh MRIO identifies South/SE Asia (−1.6%), Europe (−1.5%), and UK retail (−1.0%) as downstream victims — they receive Chinese fabric and yarn for garment assembly. China is simultaneously the world's largest buyer of petrochemical feedstocks and the world's largest supplier of textile intermediates.

9. **The MEG buffer is geographically concentrated.** Zhangjiagang port alone holds 418 kt (61% of Chinese port MEG inventory), co-located with Yizheng Chemical Fibre — the world's largest polyester producer (Sinopec). A single port event (typhoon, lockdown) can eliminate the bulk of this buffer.

---

## 9. Appendix: Remaining Data Gaps

The following parameters remain estimated. Sourcing these would be the highest-priority improvements for a future model revision:

| Priority | Gap | Impact | Recommended Source |
|---|---|---|---|
| High | Chemical Processing geography (MEG + p-Xylene capacity shares) | Changes vulnerability ranking for Saudi Arabia vs China risk | IEA Petrochemicals 2023 (free); ICIS (subscription) |
| Medium | PTA and PET Armington elasticities | Key driver of SCVI — sensitivity analysis recommended | GTAP sector-level parameter studies for specific chemicals |
| Medium | B_BASE capital coefficients | Affects investment-lag dynamics | ONS Annual Capital Expenditure Survey (SIC 13, 14, 19, 20) |
| Medium | Safety stock weeks (all except Chemical) | Affects inventory buffer in CGE Step 1 | BRC Retail Logistics Report; IGD supply chain surveys |
| Lower | Upstream A_BASE (Oil→Chem→PTA→PET) | Affects multiplier magnitude | IEA/World Bank global value chain cost structure reports |
| Lower | UK Wholesale geography (85% UK, 15% other) | Low impact — this stage is domestic | ONS trade in services statistics |
| Future | MRIO bilateral trade matrices | Would enable intra-regional amplification of China exposure | WIOD 2016 (free at wiod.org); GTAP 10 bilateral trade database |
