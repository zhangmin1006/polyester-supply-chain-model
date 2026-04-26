"""
cge_model.py
Computable General Equilibrium model for the polyester textile supply chain.

Structure (industry-focused CGE):
  ┌──────────────────────────────────────────────────────────────────┐
  │  Nested CES production (Leontief top-nest / Cobb-Douglas VA)     │
  │    Output_j = min(Intermediate bundle_j , VA_j / v_j)            │
  │    VA_j = A_j · L_j^α_j · K_j^(1-α_j)   [Cobb-Douglas]         │
  ├──────────────────────────────────────────────────────────────────┤
  │  Armington import aggregation (Hertel et al. GTAP v10)           │
  │    Q_c = δ_c · (P_agg / P_c)^σ · Q_total                        │
  ├──────────────────────────────────────────────────────────────────┤
  │  Factor markets (short-run specific capital)                     │
  │    Labour: L_j / L_j^0 = sf_j · (P_VA_j / P_VA_j^0)           │
  │    Capital: sector-specific, rental rate = (1-α_j)·P_VA_j·X_j   │
  ├──────────────────────────────────────────────────────────────────┤
  │  Mini-SAM calibration (ONS IOT 2023 + GTAP v10 factor shares)   │
  │    Rows: sectors, Labour, Capital, Household, ROW                │
  │    Columns: sectors, factors, Household, ROW                     │
  ├──────────────────────────────────────────────────────────────────┤
  │  Welfare: Equivalent Variation decomposed into                   │
  │    (a) UK consumer price effect (CES expenditure function)       │
  │    (b) UK factor income change (Wholesale + Retail)              │
  │    (c) Global supply-chain factor income change (all 8 stages)   │
  └──────────────────────────────────────────────────────────────────┘

  Market clearing via tatonnement warm-started from previous period.
  Price propagation uses full A-matrix cost push each iteration.

Data sources:
  Base quantities  : ONS Industry Accounts 2023 + HMRC OTS 2023
  IO coefficients  : ONS Supply-Use Tables 2023 (C13, C14, C20B, G46)
  GVA/Output ratios: ONS IO Analytical Tables 2023
  Labour shares    : GTAP v10 factor database + ONS ABS 2023
  Armington σ      : GTAP v10 (Hertel et al. 2012)
  Freight shares   : UNCTAD Review of Maritime Transport 2023
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import pandas as pd
from real_data import (
    SECTORS, N_SECTORS, STAGE_GEOGRAPHY, ARMINGTON_ELASTICITY,
    UK_IMPORTS_TOTAL_GBP, UK_IMPORTS_BY_COUNTRY, UK_INDUSTRY,
    CHINA_PTA_GLOBAL_SHARE, EFFECTIVE_CHINA_DEPENDENCY,
    SAFETY_STOCK_WEEKS, GVA_RATE, LABOUR_SHARE_IN_VA, VA_ELASTICITY,
)

# ── Freight cost share of each sector's total input cost ─────────────────────
# Fraction of output price attributable to transport/logistics costs.
# Sourced from: UNCTAD Review of Maritime Transport 2023 (garment 6-8% of FOB),
# World Bank logistics cost estimates, ICIS industry cost breakdowns.
# Used in Step 2b: UK_Wholesale price rise propagates to downstream sectors.
FREIGHT_COST_SHARE = {
    "Oil_Extraction":     0.010,  # pipeline / tanker, low unit cost
    "Chemical_Processing": 0.020,
    "PTA_Production":     0.030,
    "PET_Resin_Yarn":     0.040,
    "Fabric_Weaving":     0.055,
    "Garment_Assembly":   0.075,  # sea freight from Asia dominates (UNCTAD 6-8% FOB)
    "UK_Wholesale":       0.200,  # logistics IS the product
    "UK_Retail":          0.030,  # last-mile delivery
}

# ── International sea freight share ──────────────────────────────────────────
# Fraction of output price attributable specifically to INTERNATIONAL SEA
# freight costs.  Used by the freight_multiplier parameter (which represents
# global shipping rate indices such as Drewry WCI / Freightos FBX).
#
# This is deliberately separate from FREIGHT_COST_SHARE:
#   • FREIGHT_COST_SHARE covers ALL logistics (domestic + international).
#   • SEA_FREIGHT_SHARE covers only international ocean freight.
#
# Key difference: UK_Wholesale sector's VALUE-ADD is logistics, so total
# logistics = 20% of costs (FREIGHT_COST_SHARE). But sea freight (the Drewry
# WCI) is only ~3% of wholesale operating costs — the rest is domestic road
# haulage, warehousing, and last-mile. Using 0.20 with the Drewry WCI inflates
# wholesale costs by a factor the sector does not actually face from spot rates.
SEA_FREIGHT_SHARE = {
    "Oil_Extraction":      0.005,  # tanker, but mostly pipeline
    "Chemical_Processing": 0.015,
    "PTA_Production":      0.020,
    "PET_Resin_Yarn":      0.030,
    "Fabric_Weaving":      0.045,
    "Garment_Assembly":    0.075,  # sea freight 6-8% of garment FOB (UNCTAD)
    "UK_Wholesale":        0.030,  # sea freight ~3% of UK wholesale opex
    "UK_Retail":           0.010,  # last-mile is domestic; sea freight minimal
}


# ── Calibration: base-year prices and quantities ──────────────────────────────
# Normalise so that UK retail = 1 (price index = 1 in baseline)
P0 = np.ones(N_SECTORS)          # base prices (normalised to 1)

# Base-year quantities calibrated from UK data (£bn, 2023)
# Garment assembly stage ≈ UK imports (£2.39bn) + some domestic
# Retail ≈ UK retail turnover (£51.4bn)
Q0_GBP = np.array([
    0.30e9,    # Oil (fraction attributable to polyester)
    0.60e9,    # Chemicals
    0.90e9,    # PTA
    1.30e9,    # PET resin + yarn
    2.40e9,    # Fabric
    4.20e9,    # Garment assembly (cf. UK imports £2.39bn + domestic)
    20.0e9,    # UK Wholesale (ONS)
    51.4e9,    # UK Retail (ONS)
])
Q0 = Q0_GBP / Q0_GBP[-1]   # normalise to retail = 1


# ── Geographic supplier shares at each stage ──────────────────────────────────
# Each row = sector, each key = supplying country / region
# Values = share of that sector's global output
SUPPLIER_SHARES = {s: STAGE_GEOGRAPHY.get(s, {"Other": 1.0}) for s in SECTORS}


class CGEModel:
    """
    Simplified CGE for the polyester textile supply chain.

    Agents:
      - Producers at each sector/geography (maximise profit subject to CES tech)
      - UK final consumer (maximises CES utility across sectors)
      - Government (exogenous tariffs / taxes)

    Equilibrium:
      - Walras law: all markets clear simultaneously
      - Solved via iterative tatonnement or Newton-Raphson on excess demand
    """

    def __init__(self, sigma: Optional[Dict[str, float]] = None,
                 tariff_schedule: Optional[Dict[str, float]] = None):
        """
        Parameters
        ----------
        sigma           : Armington substitution elasticities by sector
                          (defaults to ARMINGTON_ELASTICITY from real_data)
        tariff_schedule : {sector_name: ad_valorem_tariff_rate}
        """
        self.sectors = SECTORS
        self.n = N_SECTORS

        # Armington elasticities (σ > 1: substitutes; closer to 1 = more locked-in)
        self.sigma = {s: ARMINGTON_ELASTICITY[s] for s in SECTORS}
        if sigma:
            self.sigma.update(sigma)

        # Tariffs (baseline = 0)
        self.tariffs = {s: 0.0 for s in SECTORS}
        if tariff_schedule:
            self.tariffs.update(tariff_schedule)

        # Base-year calibration
        self.P0 = P0.copy()
        self.Q0 = Q0.copy()

        # ── Factor-market parameters ──────────────────────────────────────────
        # α_L : labour share in value-added (Cobb-Douglas exponent)
        # σ_VA: capital-labour substitution elasticity
        # gva_rate for SAM: derived from A matrix column sums to ensure the
        #   CGE production accounts are internally consistent with IO coefficients.
        #   gva_j = 1 - Σ_i A[i,j]  (total intermediate cost share in A).
        #   ONS GVA_RATE values are retained for reference but NOT used in the
        #   SAM, because A captures global production technology while ONS GVA
        #   covers UK domestic accounts — mixing them creates an imbalanced SAM.
        from io_model import A_BASE as _A_FOR_GVA
        _col_sums = _A_FOR_GVA.sum(axis=0)
        self.alpha_L  = np.array([LABOUR_SHARE_IN_VA[s] for s in SECTORS])
        self.sigma_va = np.array([VA_ELASTICITY[s]       for s in SECTORS])
        self.gva_rate = np.maximum(1.0 - _col_sums, 0.05)   # A-matrix-implied GVA
        self._gva_rate_ons = np.array([GVA_RATE[s] for s in SECTORS])  # reference only

        # Supplier shares calibrated from real data
        self._build_supplier_shares()

        # Calibrate CES share parameters (δ) from base-year data
        self._calibrate_ces_shares()

        # Build balanced mini-SAM
        self._calibrate_sam()

    # ── Calibration ───────────────────────────────────────────────────────────

    def _build_supplier_shares(self):
        """
        Build supplier share matrix:
        supplier_shares[sector_idx] = {country: share}
        """
        self.supplier_shares = []
        for s in SECTORS:
            geo = STAGE_GEOGRAPHY.get(s, {"Other": 1.0})
            self.supplier_shares.append(geo)

    def _calibrate_ces_shares(self):
        """
        Calibrate CES expenditure share parameters δ from base-year data.
        At P=P0, optimal demand shares = δ (standard CES property).
        """
        self.delta = []
        for i, s in enumerate(SECTORS):
            geo = self.supplier_shares[i]
            countries = list(geo.keys())
            shares = np.array([geo[c] for c in countries])
            # δ_s ∝ share_s * P0_s^(1-σ) at baseline P=1, so δ_s = share_s
            self.delta.append(dict(zip(countries, shares / shares.sum())))

    # ── SAM calibration ───────────────────────────────────────────────────────

    def _calibrate_sam(self):
        """
        Build a balanced mini-SAM from base-year data.

        Accounts (rows = receipts, columns = payments):
          Sectors (8)   — production accounts
          Labour        — wage bill per sector
          Capital       — capital returns per sector
          Household     — receives factor income, spends on final demand
          ROW residual  — other intermediate inputs not in the polyester chain

        Column balance per sector j:
          Σ_i F[i,j]  +  ROW_j  +  VA_j  =  X_j
        where:
          F[i,j]  = A_BASE[i,j] * X_j          (polyester chain intermediate inputs)
          VA_j    = (1 - col_sum(A)_j) * X_j    (A-matrix-implied GVA, for consistency)
          ROW_j   = 0  (VA absorbs the full residual by construction)

        Row balance per sector j:
          Σ_k F[j,k]  +  FD_j  =  X_j
        where FD_j = X_j - Σ_k A_BASE[j,k]*X_k  (residual final demand)
        """
        from io_model import A_BASE
        n  = N_SECTORS
        X0 = Q0_GBP.copy()

        # Intermediate flow matrix: F[i,j] = input i consumed by sector j
        F = A_BASE * X0[np.newaxis, :]   # (n, n)

        # Value-added components
        VA  = self.gva_rate * X0                     # total GVA per sector
        WL  = self.alpha_L  * VA                     # labour income
        RK  = (1.0 - self.alpha_L) * VA              # capital income

        # Residual "other intermediate inputs" to balance each column
        col_sum = A_BASE.sum(axis=0)                  # polyester-chain input share
        ROW_col = np.maximum(0.0,
                             (1.0 - col_sum - self.gva_rate) * X0)

        # Final demand: what each sector sells outside the intermediate chain
        row_sum_F = (A_BASE * X0[np.newaxis, :]).sum(axis=1)  # Σ_k F[j,k]
        FD  = np.maximum(0.0, X0 - row_sum_F)        # residual final sales

        # Household income = all factor payments in the chain
        HH_income = WL.sum() + RK.sum()
        # Household expenditure = final demand (primarily retail)
        HH_expend = FD.sum()

        self._sam_X0      = X0
        self._sam_F       = F
        self._sam_VA      = VA
        self._sam_WL      = WL
        self._sam_RK      = RK
        self._sam_ROW_col = ROW_col
        self._sam_FD      = FD
        self._sam_HH_income = HH_income
        self._sam_HH_expend = HH_expend

        # Implied VA rate from A matrix (used as P_VA baseline, all prices = 1)
        self._pva0 = np.maximum(1.0 - col_sum, 0.01)   # (n,)

    def build_sam(self) -> pd.DataFrame:
        """
        Return the mini-SAM as a formatted DataFrame (£bn, base year 2023).

        Rows    : supply-side accounts (sectors + factor aggregates)
        Columns : demand-side accounts (sectors + final demand aggregates)
        """
        n   = N_SECTORS
        X0  = self._sam_X0 / 1e9
        F   = self._sam_F  / 1e9
        WL  = self._sam_WL / 1e9
        RK  = self._sam_RK / 1e9
        FD  = self._sam_FD / 1e9
        ROW = self._sam_ROW_col / 1e9

        short = [s.replace("_", " ").replace("UK ", "") for s in SECTORS]

        # Build (n+4) × (n+4) SAM
        dim   = n + 4   # sectors + Labour + Capital + Household + Total
        labels = short + ["Labour", "Capital", "Household", "TOTAL"]
        sam   = np.zeros((dim, dim))

        # Intermediate flows
        sam[:n, :n] = F

        # Labour and Capital rows → sector columns (factor payments)
        sam[n,   :n] = WL
        sam[n+1, :n] = RK

        # Residual other-intermediate row → sector columns
        # (ROW_col added as a special "Other inputs" row; shown in total only)

        # Household column: final demand
        sam[:n, n+2] = FD

        # Household row: receives factor income (from Labour + Capital rows)
        sam[n+2, n]   = WL.sum()    # Labour account → Household
        sam[n+2, n+1] = RK.sum()    # Capital account → Household

        # Totals column / row
        sam[:n,   n+3] = X0               # sector row totals = gross output
        sam[n,    n+3] = WL.sum()
        sam[n+1,  n+3] = RK.sum()
        sam[n+2,  n+3] = WL.sum() + RK.sum()

        sam[n+3, :n]   = X0               # sector column totals = gross output
        sam[n+3, n]    = WL.sum()
        sam[n+3, n+1]  = RK.sum()
        sam[n+3, n+2]  = FD.sum()

        df = pd.DataFrame(sam, index=labels, columns=labels)
        return df.round(3)

    # ── Factor-market methods ─────────────────────────────────────────────────

    def _va_prices(self, prices: np.ndarray, A: np.ndarray) -> np.ndarray:
        """
        Value-added price index per sector: P_VA_j = P_j − Σ_i a_ij · P_i.

        Represents the residual price after paying for intermediate inputs.
        At baseline (all P=1): P_VA_j^0 = 1 − col_sum_j = self._pva0[j].
        When supply is disrupted: P_VA may rise (scarcity rent) or fall
        (input cost squeeze).
        """
        int_cost = A.T @ prices           # (n,): Σ_i a_ij * P_i per sector j
        return np.maximum(prices - int_cost, 0.01)

    def factor_incomes(self, prices: np.ndarray,
                       supply_fractions: np.ndarray,
                       A: Optional[np.ndarray] = None) -> Dict:
        """
        Compute endogenous factor incomes and employment from equilibrium prices.

        Production structure (short-run specific capital):
          Output_j    = sf_j · X_j^0                  [supply-constrained]
          P_VA_j      = P_j − Σ_i a_ij · P_i          [value-added price]
          WageBill_j  = α_j · P_VA_j · X_j            [Shephard's lemma, CD]
          CapReturn_j = (1−α_j) · P_VA_j · X_j
          Employ_j    = sf_j · (P_VA_j / P_VA_j^0)    [sticky wages, Shephard]

        Employment index interpretation:
          > 1 : sector over-employed relative to baseline (price surge + output)
          < 1 : job losses due to supply shock
          Dampened by price rise: when VA price rises despite output falling,
          firms retain more labour (higher marginal revenue product).

        UK-specific flag: Wholesale (idx 6) and Retail (idx 7) are UK-domestic
        stages. Their factor income changes directly affect UK households.
        """
        from io_model import A_BASE
        A_use = A if A is not None else A_BASE

        n   = self.n
        sf  = np.asarray(supply_fractions, dtype=float)
        p   = np.asarray(prices, dtype=float)
        X0  = self._sam_X0
        X   = sf * X0

        pva   = self._va_prices(p, A_use)           # current VA prices
        pva0  = self._pva0                           # baseline VA prices (all P=1)

        # Wage bill and capital return at current prices
        wl  = self.alpha_L          * pva * X       # (n,)
        rk  = (1.0 - self.alpha_L)  * pva * X       # (n,)

        # Employment index: sticky wages, labour adjusts to equate MVPs
        # L_j/L_j^0 = sf_j · (P_VA_j / P_VA_j^0)
        employ = np.clip(sf * (pva / pva0), 0.0, 2.0)

        # Separate UK stages from global upstream stages
        uk_idx = [SECTORS.index("UK_Wholesale"), SECTORS.index("UK_Retail")]

        return {
            "wage_bill_gbp":       wl,
            "capital_return_gbp":  rk,
            "employment_index":    employ,
            "va_price_index":      pva / pva0,
            "delta_wage_bill_gbp":      wl - self._sam_WL,
            "delta_capital_return_gbp": rk - self._sam_RK,
            # UK-specific (wholesale + retail workers and capital)
            "uk_delta_factor_income_gbp": (
                (wl[uk_idx] - self._sam_WL[uk_idx]).sum() +
                (rk[uk_idx] - self._sam_RK[uk_idx]).sum()
            ),
            # Full supply-chain global factor income change
            "global_delta_factor_income_gbp": (
                (wl - self._sam_WL).sum() + (rk - self._sam_RK).sum()
            ),
        }

    def equivalent_variation(self, prices: np.ndarray,
                              supply_fractions: np.ndarray,
                              A: Optional[np.ndarray] = None) -> Dict:
        """
        Equivalent Variation welfare decomposition.

        EV_total = UK_factor_income_change − consumer_price_loss

        Consumer price loss uses the CES expenditure function:
          EV_consumer = Y_retail · [(P_retail/P0_retail)^(1−1/σ) − 1] / (1−1/σ)

        For σ → 1 (Cobb-Douglas limit):
          EV_consumer = −Y_retail · ln(P_retail)

        This replaces the previous first-order approximation −ΔP · Q0
        which overestimates welfare loss when σ > 1.

        Returns
        -------
        dict with ev_gbp, consumer_loss_gbp, uk_factor_gain_gbp,
                  global_factor_gain_gbp, ev_breakdown (Series)
        """
        fi   = self.factor_incomes(prices, supply_fractions, A)
        p    = np.asarray(prices, dtype=float)

        # Consumer welfare: final demand is concentrated at UK_Retail
        ret_idx = SECTORS.index("UK_Retail")
        sigma_r = self.sigma[SECTORS[ret_idx]]
        p_r     = float(p[ret_idx])
        Y_r     = float(self._sam_FD[ret_idx])   # base household final expenditure

        if abs(sigma_r - 1.0) < 1e-4:            # Cobb-Douglas limit
            consumer_loss = Y_r * np.log(max(p_r, 1e-6))
        else:
            consumer_loss = Y_r * (p_r ** (1.0 - 1.0/sigma_r) - 1.0) / (1.0 - 1.0/sigma_r)

        uk_factor_gain     = fi["uk_delta_factor_income_gbp"]
        global_factor_gain = fi["global_delta_factor_income_gbp"]
        ev_uk              = uk_factor_gain - consumer_loss
        ev_global          = global_factor_gain - consumer_loss

        rows = {
            "Consumer price loss (UK)":           -consumer_loss,
            "UK factor income change":             uk_factor_gain,
            "EV (UK net welfare)":                 ev_uk,
            "Global supply-chain factor change":   global_factor_gain,
            "EV (global chain welfare)":           ev_global,
        }

        return {
            "ev_gbp":               ev_uk,
            "ev_global_gbp":        ev_global,
            "consumer_loss_gbp":    consumer_loss,
            "uk_factor_gain_gbp":   uk_factor_gain,
            "global_factor_gain_gbp": global_factor_gain,
            "ev_breakdown":         pd.Series(rows),
            "factor_incomes":       fi,
        }

    # ── CES demand functions ───────────────────────────────────────────────────

    def ces_demand(self, sector_idx: int, prices: Dict[str, float],
                   total_expenditure: float) -> Dict[str, float]:
        """
        CES demand for inputs to sector_idx across supplier countries.
        Armington aggregation: Q_c = δ_c * (P_agg / P_c)^σ * Q_total

        Returns dict {country: quantity demanded}
        """
        s = SECTORS[sector_idx]
        sigma = self.sigma[s]
        delta = self.delta[sector_idx]
        tariff = self.tariffs[s]

        countries = list(delta.keys())
        p = np.array([prices.get(c, 1.0) * (1 + tariff if c != "UK" else 1.0)
                      for c in countries])
        d = np.array([delta[c] for c in countries])

        # CES price index: P_agg = [Σ δ_c * P_c^(1-σ)]^(1/(1-σ))
        if abs(sigma - 1) < 1e-6:   # Cobb-Douglas limit
            p_agg = np.prod(p ** d)
        else:
            p_agg = (d @ p ** (1 - sigma)) ** (1 / (1 - sigma))

        # Individual demands: q_c = δ_c * (p_agg / p_c)^σ * Q_total
        q_total = total_expenditure / p_agg
        q = d * (p_agg / p) ** sigma * q_total

        return dict(zip(countries, q))

    def aggregate_price(self, sector_idx: int,
                        country_prices: Dict[str, float]) -> float:
        """CES aggregate (Armington) price index for a sector."""
        s = SECTORS[sector_idx]
        sigma = self.sigma[s]
        delta = self.delta[sector_idx]
        tariff = self.tariffs[s]

        p = np.array([country_prices.get(c, 1.0) * (1 + tariff if c != "UK" else 1.0)
                      for c in delta])
        d = np.array(list(delta.values()))

        if abs(sigma - 1) < 1e-6:
            return float(np.prod(p ** d))
        return float((d @ p ** (1 - sigma)) ** (1 / (1 - sigma)))

    # ── Market clearing ────────────────────────────────────────────────────────

    def equilibrium(self, supply_shocks: np.ndarray,
                    final_demand: np.ndarray,
                    max_iter: int = 300,
                    tol: float = 1e-7,
                    lambda_: float = 0.08,
                    demand_shocks: Optional[np.ndarray] = None,
                    shock_duration_weeks: int = 12,
                    freight_multiplier: float = 1.0,
                    commodity_prices: Optional[Dict[str, float]] = None) -> Dict:
        """
        Find general equilibrium prices and quantities.

        Revision V1 (validation-driven):
        ─────────────────────────────────
        Step 1 — Partial equilibrium with inventory buffer damping:
            P_j* = supply_shock_j^(-1/σ_j)
            Dampened by safety-stock buffer: shocks covered by inventory
            do not immediately raise prices.  Buffer fraction =
            min(1, safety_stock_weeks_j / shock_duration_weeks).
            Price impact = 1 + (P* - 1) × (1 - 0.7 × buffer_fraction)

        Step 2 — Upstream I-O cost propagation (unchanged).

        Step 2b — Freight cost pass-through:
            When the logistics sector (UK_Wholesale) price rises, that cost
            is passed through to all downstream sectors proportional to
            their freight cost share (FREIGHT_COST_SHARE).
            ΔP_j += freight_share_j × (P_logistics - 1)

        Step 2c — Exogenous freight-rate multiplier (Issues 1/V2/V5):
            When global freight rates surge independently of the wholesale
            capacity (e.g. Drewry WCI +563%), inject cost-push directly:
            ΔP_j += freight_share_j × (freight_multiplier - 1)
            This captures cost-push that cannot be avoided by sourcing
            substitution — it raises costs at ALL import-using sectors.

        Step 2d — Exogenous commodity price floor (Issues 2/V4/V7):
            commodity_prices = {sector_name: price_multiplier} sets a
            minimum price at a sector (e.g. oil at 1.54 after Brent +54%).
            Applied before A-matrix propagation so downstream cost-push
            reflects the commodity price shock correctly.

        Step 3 — Tatonnement refinement with demand shocks:
            Demand shocks (e.g. COVID retail lockdown) scale Q0 downward.
            When demand_shocks[j] < 1: demand collapses → price falls.
            When demand_shocks[j] > 1: demand surge → price rises.
            ED_j = Q0_j × dsh_j × (P_j/P0_j)^(-σ_j) - Q0_j × s_j

        Parameters
        ----------
        supply_shocks       : (n,) fraction of baseline supply available
        final_demand        : (n,) final demand vector (normalised)
        demand_shocks       : (n,) optional multiplier on demand (1=baseline,
                              <1=demand collapse, >1=demand surge)
        shock_duration_weeks: expected duration of the shock (for buffer calc)
        freight_multiplier  : global freight cost index relative to baseline
                              (1.0=normal; 5.63=Drewry WCI Sep 2021 peak).
                              Injects cost-push at every import-intensive sector.
        commodity_prices    : {sector_name: price_multiplier} — sets a floor on
                              sector price before A-matrix propagation.  Use for
                              oil/energy price shocks (e.g. Brent +54% → {"Oil": 1.54}).

        Returns
        -------
        dict with equilibrium prices, quantities, welfare, and trade flows
        """
        from io_model import A_BASE

        if demand_shocks is None:
            demand_shocks = np.ones(self.n)
        demand_shocks = np.asarray(demand_shocks, dtype=float)

        # ── Step 2d: commodity price floors (before partial equilibrium) ─────
        # Apply these before the Armington step so the oil/energy price is
        # already "priced in" when Step 2 propagates costs downstream.
        commodity_floor = np.ones(self.n)
        if commodity_prices:
            for s_name, price_mult in commodity_prices.items():
                if s_name in SECTORS:
                    commodity_floor[SECTORS.index(s_name)] = float(price_mult)

        # ── Step 1: partial equilibrium + inventory buffer damping ────────────
        P_partial = np.ones(self.n)
        for j in range(self.n):
            s_j  = float(supply_shocks[j])
            dsh  = float(demand_shocks[j])
            sig  = self.sigma[SECTORS[j]]
            buf  = SAFETY_STOCK_WEEKS.get(SECTORS[j], 2.0)

            # Effective supply-demand balance
            if s_j <= 0:
                P_partial[j] = 8.0   # hard cap: near-zero supply
            elif s_j < 1.0 or dsh != 1.0:
                # Notional market-clearing price (no buffer)
                # Supply shortage raises price; demand collapse lowers it
                effective_ratio = s_j / max(dsh, 1e-6)   # supply / demand
                if effective_ratio <= 0:
                    P_raw = 8.0
                else:
                    P_raw = effective_ratio ** (-1.0 / sig)

                # Inventory buffer damping: buffer absorbs part of supply shock.
                # Fraction of shock duration covered by safety stock.
                buffer_frac = min(1.0, buf / max(shock_duration_weeks, 1))
                # Only supply shortages are buffered (demand collapses are not).
                if s_j < 1.0:
                    # Dampen price rise: immediate price = P_raw weighted by
                    # fraction NOT covered by buffer (0.7 scaling = partial pass-through).
                    P_partial[j] = 1.0 + (P_raw - 1.0) * (1.0 - 0.7 * buffer_frac)
                else:
                    # Pure demand shock: no buffer effect
                    P_partial[j] = P_raw
            # else no shock → P_partial[j] = 1.0

        # Apply commodity price floors before A-matrix propagation
        P_partial = np.maximum(P_partial, commodity_floor)

        # ── Step 2: upstream I-O cost propagation (full A matrix) ────────────
        # Use vectorised column dot-product: cost_push_j = A[:,j] · (P-1)
        # A is lower-triangular for this supply chain, so sequential order
        # gives the correct upstream-first propagation.
        #
        # Inventory-buffer damping on cost propagation: a downstream sector
        # with safety stock covering the shock duration can absorb upstream
        # cost increases from inventory rather than immediately re-pricing.
        # Same buffer formula as Step 1: damp = 1 - 0.7 × buffer_fraction.
        # For very short shocks (e.g. V4: 2 weeks) all downstream sectors
        # have buffer_frac = 1.0, reducing cascade to ~30% of the raw push.
        # For long shocks (≥ 26 weeks) buffer_frac ≈ 0, so damping is minimal
        # and cost propagation behaves as before.
        P_propagated = P_partial.copy()
        for j in range(1, self.n):
            cost_push = float(A_BASE[:j, j] @ (P_partial[:j] - 1.0))
            if cost_push > 0:
                buf_j      = SAFETY_STOCK_WEEKS.get(SECTORS[j], 2.0)
                buf_frac_j = min(1.0, buf_j / max(shock_duration_weeks, 1))
                cost_push  = cost_push * (1.0 - 0.7 * buf_frac_j)
            P_propagated[j] = max(P_partial[j], 1.0 + cost_push)

        # ── Step 2b: freight cost pass-through from logistics price ──────────
        # UK_Wholesale price rise (from capacity shock) feeds into all sectors.
        logistics_idx = SECTORS.index("UK_Wholesale")
        P_logistics   = P_propagated[logistics_idx]
        if P_logistics > 1.0:
            for j in range(self.n):
                if j == logistics_idx:
                    continue
                fshare = FREIGHT_COST_SHARE.get(SECTORS[j], 0.03)
                freight_push = fshare * (P_logistics - 1.0)
                P_propagated[j] = min(P_propagated[j] + freight_push, 8.0)

        # ── Step 2c: exogenous freight-rate multiplier ────────────────────────
        # Global freight rate surge (e.g. Drewry WCI +563%) raises costs at
        # every import-intensive sector regardless of wholesale capacity.
        # This captures cost-push from rising spot market freight rates.
        if freight_multiplier > 1.0:
            for j in range(self.n):
                fshare = SEA_FREIGHT_SHARE.get(SECTORS[j], 0.02)
                exog_push = fshare * (freight_multiplier - 1.0)
                P_propagated[j] = min(P_propagated[j] + exog_push, 8.0)

        # ── Step 3: tatonnement with demand shocks ─────────────────────────────
        # Pre-compute constant price floors: prices cannot fall below the cost
        # imposed by freight rates or commodity price shocks.
        # Uses SEA_FREIGHT_SHARE (not FREIGHT_COST_SHARE) because freight_multiplier
        # represents global shipping rate indices (Drewry WCI / Freightos) which
        # apply only to the sea freight component of costs, not total logistics.
        #
        # IMPORTANT: freight push is applied as a FLOOR (np.maximum), not added on
        # each iteration. Adding it each iteration would cause price accumulation
        # and non-convergence. The floor correctly models a minimum cost at which
        # producers will supply (i.e., the supply curve shifts up by freight cost).
        freight_push_vec = np.zeros(self.n)
        if freight_multiplier > 1.0:
            for j in range(self.n):
                freight_push_vec[j] = SEA_FREIGHT_SHARE.get(SECTORS[j], 0.02) * (freight_multiplier - 1.0)
        # Combined floor: max of (1 + freight_push, commodity_floor)
        price_floor = np.maximum(1.0 + freight_push_vec, commodity_floor)

        P = P_propagated.copy()
        history = [P.copy()]
        converged = False

        for it in range(max_iter):
            ED = np.zeros(self.n)
            for j in range(self.n):
                sig  = self.sigma[SECTORS[j]]
                dsh  = float(demand_shocks[j])
                # Demand: scaled by demand_shock (lockdown/surge)
                D    = self.Q0[j] * dsh * (P[j] / self.P0[j]) ** (-sig)
                S    = self.Q0[j] * float(supply_shocks[j])
                ED[j] = D - S

            P_new = P * (1 + lambda_ * ED / (self.Q0 + 1e-12))
            P_new = np.clip(P_new, 0.3, 8.0)
            # Enforce exogenous cost floors: tatonnement cannot push prices below
            # the minimum implied by freight costs or commodity price shocks.
            P_new = np.maximum(P_new, price_floor)

            history.append(P_new.copy())
            if np.max(np.abs(P_new - P)) < tol:
                converged = True
                break
            P = P_new

        # Quantities: min of supply and demand at equilibrium
        Q_eq = np.minimum(
            self.Q0 * np.array([float(s) for s in supply_shocks]),
            self.Q0 * demand_shocks,
        )

        # Welfare (Compensating Variation = -Σ Q0 * ΔP - demand quantity loss)
        delta_P = P - self.P0
        welfare_change_gbp = -(Q0_GBP * delta_P).sum()

        trade_flows = self._compute_trade_flows(P, supply_shocks)

        return {
            "equilibrium_prices":     P,
            "equilibrium_quantities": Q_eq,
            "price_index_change_pct": (P / self.P0 - 1) * 100,
            "welfare_change_gbp":     welfare_change_gbp,
            "iterations":             it + 1,
            "converged":              converged,
            "trade_flows":            trade_flows,
            "price_history":          np.array(history),
            "demand_shocks_applied":  demand_shocks,
            "inventory_buffer_used":  True,
            "shock_duration_weeks":   shock_duration_weeks,
        }

    # ── Per-period price step for coupled simulation ──────────────────────────

    def price_step(self,
                   supply_fractions: np.ndarray,
                   demand_mults: np.ndarray,
                   prev_prices: np.ndarray,
                   max_iter: int = 40,
                   lambda_: float = 0.08,
                   A: np.ndarray = None,
                   freight_multiplier: float = 1.0,
                   commodity_prices: Optional[Dict[str, float]] = None,
                   ) -> np.ndarray:
        """
        Lightweight per-period price update for the coupled IO × CGE × ABM loop.

        Warm-starts tatonnement from prev_prices (already near-equilibrium) and
        applies IO cost propagation each iteration. Skips the inventory-buffer
        damping from equilibrium() — by the time this is called the shock is
        ongoing and buffers are already depleted.

        Parameters
        ----------
        supply_fractions : (n,) IO output / baseline — range [0, 1].
        demand_mults     : (n,) ABM-derived demand multipliers (1 = baseline).
        prev_prices      : (n,) prices from the previous period (warm start).
        max_iter         : tatonnement iterations (40 sufficient near equilibrium).
        lambda_          : price adjustment speed.

        Returns
        -------
        (n,) updated equilibrium price vector for this period.
        """
        from io_model import A_BASE
        A_use = A if A is not None else A_BASE

        # Pre-compute commodity floors and freight push vectors (constant per call)
        commodity_floor = np.ones(self.n)
        if commodity_prices:
            for s_name, pm in commodity_prices.items():
                if s_name in SECTORS:
                    commodity_floor[SECTORS.index(s_name)] = float(pm)

        freight_push_vec = np.zeros(self.n)
        if freight_multiplier > 1.0:
            for j in range(self.n):
                freight_push_vec[j] = SEA_FREIGHT_SHARE.get(SECTORS[j], 0.02) * (freight_multiplier - 1.0)
        # Combined constant floor: freight cost + commodity price floors
        price_floor = np.maximum(1.0 + freight_push_vec, commodity_floor)

        P = np.maximum(prev_prices.copy(), price_floor)

        for _ in range(max_iter):
            ED = np.zeros(self.n)
            for j in range(self.n):
                sig  = self.sigma[SECTORS[j]]
                dsh  = float(demand_mults[j])
                D    = self.Q0[j] * dsh * (P[j] / self.P0[j]) ** (-sig)
                S    = self.Q0[j] * float(supply_fractions[j])
                ED[j] = D - S

            P_new = P * (1.0 + lambda_ * ED / (self.Q0 + 1e-12))

            # Upstream cost propagation using current A (dynamic in GS loop)
            for j in range(1, self.n):
                cost_push = sum(A_use[i, j] * (P_new[i] - 1.0) for i in range(j))
                P_new[j]  = max(P_new[j], 1.0 + cost_push)

            # Enforce exogenous cost floors (freight + commodity): prices cannot
            # fall below the minimum implied cost level. Applied as np.maximum
            # (not addition) so the floor does not accumulate across iterations.
            P_new = np.maximum(P_new, price_floor)
            P_new = np.clip(P_new, 0.3, 4.0)
            if np.max(np.abs(P_new - P)) < 1e-6:
                break
            P = P_new

        return P_new

    def _compute_trade_flows(self, P: np.ndarray,
                             supply_shocks: np.ndarray) -> pd.DataFrame:
        """
        Compute how trade flows shift in response to prices and shocks.
        Based on Armington elasticities.
        """
        rows = []
        for j, sector in enumerate(SECTORS):
            sigma = self.sigma[sector]
            geo = self.supplier_shares[j]
            shock = supply_shocks[j]

            for country, base_share in geo.items():
                # Price effect on share: when P rises, substitute to alternatives
                # China-specific shock: reduce China's supply share by shock
                if country == "China":
                    adj_share = base_share * shock
                else:
                    # Other suppliers capture redirected demand
                    china_share = geo.get("China", 0.0)
                    redir = china_share * (1 - shock) * (base_share / max(1 - china_share, 1e-6))
                    adj_share = base_share + redir

                rows.append({
                    "Sector":        sector,
                    "Country":       country,
                    "Baseline_Share": base_share,
                    "Shocked_Share":  adj_share,
                    "Share_Change_%": (adj_share - base_share) / base_share * 100
                    if base_share > 0 else 0,
                })
        return pd.DataFrame(rows)

    # ── Substitution analysis ─────────────────────────────────────────────────

    def substitution_matrix(self, sector_idx: int,
                            price_change: Dict[str, float]) -> Dict:
        """
        Compute how demand shifts between suppliers when one country's price rises.
        Uses CES cross-price demand elasticities.
        """
        s = SECTORS[sector_idx]
        sigma = self.sigma[s]
        delta = self.delta[sector_idx]
        countries = list(delta.keys())

        base_prices = {c: 1.0 for c in countries}
        new_prices  = {**base_prices, **price_change}

        q_base = self.ces_demand(sector_idx, base_prices, self.Q0[sector_idx])
        q_new  = self.ces_demand(sector_idx, new_prices,  self.Q0[sector_idx])

        result = {}
        for c in countries:
            result[c] = {
                "base_demand":    q_base.get(c, 0),
                "new_demand":     q_new.get(c, 0),
                "change_%":       (q_new.get(c, 0) - q_base.get(c, 0))
                                  / (q_base.get(c, 0) + 1e-12) * 100,
            }
        return result

    # ── Tariff / policy scenarios ─────────────────────────────────────────────

    def apply_tariff(self, sector: str, tariff_rate: float) -> "CGEModel":
        """Return new CGEModel with tariff applied to a sector."""
        new_tariffs = {**self.tariffs, sector: tariff_rate}
        return CGEModel(sigma=self.sigma, tariff_schedule=new_tariffs)

    # ── Concentration metrics ─────────────────────────────────────────────────

    def herfindahl_index(self) -> pd.DataFrame:
        """
        Herfindahl-Hirschman Index (HHI) for supplier concentration at each stage.
        HHI = Σ s_i^2 ∈ [0, 1]; >0.25 = highly concentrated.
        """
        rows = []
        for j, sector in enumerate(SECTORS):
            geo = self.supplier_shares[j]
            shares = np.array(list(geo.values()))
            hhi = (shares ** 2).sum()
            china_share = geo.get("China", 0.0)
            rows.append({
                "Sector":        sector,
                "HHI":           hhi,
                "Concentration": "High" if hhi > 0.25 else ("Medium" if hhi > 0.15 else "Low"),
                "China_Share_%": china_share * 100,
                "Top_Supplier":  max(geo, key=geo.get),
                "Top_Share_%":   max(geo.values()) * 100,
            })
        return pd.DataFrame(rows)

    def geographic_risk_score(self) -> pd.DataFrame:
        """
        Composite geographic risk score for each sector:
          Risk = HHI * China_share * (1 / Armington_elasticity)
        Higher = more vulnerable to geographic disruption.
        """
        hhi_df = self.herfindahl_index()
        rows = []
        for _, row in hhi_df.iterrows():
            s = row["Sector"]
            sigma = self.sigma[s]
            risk = row["HHI"] * (row["China_Share_%"] / 100) * (1 / sigma)
            rows.append({
                "Sector":          s,
                "HHI":             row["HHI"],
                "China_Share_%":   row["China_Share_%"],
                "Armington_σ":     sigma,
                "Geographic_Risk": risk,
                "Risk_Category":   "Critical" if risk > 0.15 else
                                   ("High" if risk > 0.08 else
                                    ("Medium" if risk > 0.03 else "Low")),
            })
        df = pd.DataFrame(rows)
        df = df.sort_values("Geographic_Risk", ascending=False).reset_index(drop=True)
        return df
