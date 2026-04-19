"""
cge_model.py
Computable General Equilibrium model for the polyester textile supply chain.

Structure:
  - CES (Constant Elasticity of Substitution) production at each sector
  - Armington aggregation: domestic vs. imported goods
  - Market clearing via tatonnement (iterative price adjustment)
  - Calibrated to 2023 HMRC import data and UK industry turnover

Key equations:
  CES production:  Q = A * [Σ_s δ_s * q_s^((σ-1)/σ)]^(σ/(σ-1))
  Armington:       Q_c = (α * Q_dom^ρ + (1-α) * Q_imp^ρ)^(1/ρ), ρ=(σ-1)/σ
  Market clearing: Σ demands = Σ supplies at equilibrium price vector P*
  Price adjustment: ΔP/P = λ * (D - S) / S
"""

import numpy as np
from scipy.optimize import fsolve, minimize
from typing import Dict, List, Optional, Tuple
import pandas as pd
from real_data import (
    SECTORS, N_SECTORS, STAGE_GEOGRAPHY, ARMINGTON_ELASTICITY,
    UK_IMPORTS_TOTAL_GBP, UK_IMPORTS_BY_COUNTRY, UK_INDUSTRY,
    CHINA_PTA_GLOBAL_SHARE, EFFECTIVE_CHINA_DEPENDENCY,
    SAFETY_STOCK_WEEKS,
)

# ── Freight cost share of each sector's total input cost ─────────────────────
# Fraction of output price attributable to transport/logistics costs.
# Sourced from: UNCTAD Review of Maritime Transport 2023 (garment 6-8% of FOB),
# World Bank logistics cost estimates, ICIS industry cost breakdowns.
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

        # Supplier shares calibrated from real data
        self._build_supplier_shares()

        # Calibrate CES share parameters (δ) from base-year data
        self._calibrate_ces_shares()

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
                    shock_duration_weeks: int = 12) -> Dict:
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

        Returns
        -------
        dict with equilibrium prices, quantities, welfare, and trade flows
        """
        from io_model import A_BASE

        if demand_shocks is None:
            demand_shocks = np.ones(self.n)
        demand_shocks = np.asarray(demand_shocks, dtype=float)

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

        # ── Step 2: upstream I-O cost propagation ─────────────────────────────
        P_propagated = P_partial.copy()
        for j in range(1, self.n):
            cost_push = sum(A_BASE[i, j] * (P_partial[i] - 1.0)
                            for i in range(j))
            P_propagated[j] = max(P_partial[j], 1.0 + cost_push)

        # ── Step 2b: freight cost pass-through ────────────────────────────────
        # Logistics (UK_Wholesale, idx=6) price rise feeds into all sectors
        # via their freight cost share.
        logistics_idx = SECTORS.index("UK_Wholesale")
        P_logistics   = P_propagated[logistics_idx]
        if P_logistics > 1.0:
            for j in range(self.n):
                if j == logistics_idx:
                    continue
                fshare = FREIGHT_COST_SHARE.get(SECTORS[j], 0.03)
                freight_push = fshare * (P_logistics - 1.0)
                P_propagated[j] = min(P_propagated[j] + freight_push, 8.0)

        # ── Step 3: tatonnement with demand shocks ─────────────────────────────
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

        P = prev_prices.copy()

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
