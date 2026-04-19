# -*- coding: utf-8 -*-
"""
abm_model.py
Agent-Based Model of the polyester textile supply chain.

Based on the Beer Distribution Game (Sterman, 1989) extended to:
  - 8-stage polyester supply chain
  - Geographic multi-sourcing (agents can order from multiple countries)
  - Adaptive inventory policies (agents update safety-stock targets)
  - Information delays (orders take time to propagate upstream)
  - Capacity constraints (each node has limited throughput)
  - Disruption events (shock specific nodes, varying durations)

Calibrated from:
  - Transit times (TRANSIT_DAYS from real_data)
  - Safety stock targets (SAFETY_STOCK_WEEKS)
  - UK import shares (UK_IMPORTS_BY_COUNTRY)
  - MEG port inventories (MEG_PORT_INVENTORY_KT)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import pandas as pd
from real_data import (
    SECTORS, N_SECTORS, SAFETY_STOCK_WEEKS, TRANSIT_DAYS,
    STAGE_GEOGRAPHY, UK_IMPORTS_TOTAL_GBP, EFFECTIVE_CHINA_DEPENDENCY,
    MEG_TOTAL_INVENTORY_KT, HMRC_MONTHLY_SEASONAL_FACTORS,
)

RNG = np.random.default_rng(42)


# -- Agent definitions ---------------------------------------------------------

@dataclass
class SupplyChainAgent:
    """
    Represents a node in the supply chain (one sector x one country).

    Policy: order-up-to inventory policy with adaptive safety stock.
      Order_t = max(0, demand_forecast + safety_stock - (inventory + pipeline))
    """
    name:          str
    sector_idx:    int
    country:       str
    base_capacity: float           # baseline weekly throughput (normalised units)
    capacity:      float = field(init=False)
    inventory:     float = field(init=False)
    backlog:       float = 0.0    # unfilled orders
    pipeline:      List[float] = field(default_factory=list)  # in-transit orders
    demand_history: List[float] = field(default_factory=list)
    demand_forecast: float = field(init=False)
    safety_stock:  float = field(init=False)
    lead_time:     int   = 2      # weeks (order->receipt)
    price:         float = 1.0    # relative price (1 = baseline)
    disrupted:     bool  = False
    disruption_remaining: int = 0
    total_shortage: float = 0.0
    total_cost:    float  = 0.0

    # History
    inventory_history:  List[float] = field(default_factory=list)
    order_history:      List[float] = field(default_factory=list)
    shortage_history:   List[float] = field(default_factory=list)
    price_history:      List[float] = field(default_factory=list)

    def __post_init__(self):
        self.capacity = self.base_capacity
        ss_weeks = SAFETY_STOCK_WEEKS.get(SECTORS[self.sector_idx], 4.0)
        self.safety_stock  = self.base_capacity * ss_weeks
        self.inventory     = self.safety_stock   # start at target
        self.demand_forecast = self.base_capacity
        self.pipeline = [0.0] * max(1, self.lead_time)

    # -- Forecasting -----------------------------------------------------------

    def update_forecast(self, alpha: float = 0.3):
        """Exponential smoothing forecast."""
        if self.demand_history:
            d = self.demand_history[-1]
            self.demand_forecast = alpha * d + (1 - alpha) * self.demand_forecast

    # -- Ordering decision -----------------------------------------------------

    def compute_order(self, demand: float, price_signal: float = 1.0,
                      theta: float = 0.0, alpha: float = 0.3) -> float:
        """
        Order policy.

        theta == 0  : standard order-up-to (used in step_period / coupled run).
            order = max(0, demand_forecast + safety_stock - inventory - pipeline)

        theta > 0   : Sterman (1989) anchored-order rule (used in standalone run).
            order = max(0, demand_forecast + (safety_stock - inventory) / theta)
            Bounded: even when inventory=0, order ≤ demand + SS/theta, preventing
            the runaway backlog cascade that unbounded catch-up ordering produces.

        Adaptive safety stock: grows cautiously when prices signal scarcity,
        capped at 4 weeks of base capacity (was 20 weeks, which caused SS → 13x
        base and order explosions over long disruptions).
        """
        self.demand_history.append(demand)
        self.update_forecast(alpha=alpha)

        # Adaptive safety stock: increase when supply is uncertain (price > 1.1)
        if price_signal > 1.1:
            self.safety_stock = min(
                self.safety_stock * 1.02,           # slower growth (was 1.05)
                self.base_capacity * 4              # cap at 4 weeks (was 20)
            )
        elif price_signal < 1.0:
            self.safety_stock = max(
                self.safety_stock * 0.99,
                self.base_capacity * SAFETY_STOCK_WEEKS.get(
                    SECTORS[self.sector_idx], 2.0)
            )

        if theta > 0.0:
            # Sterman anchored-order: gradual inventory correction over theta periods.
            # Bounded even when inventory = 0 (order ≤ demand + SS/theta).
            order = self.demand_forecast + (self.safety_stock - self.inventory) / theta
        else:
            pipeline_total = sum(self.pipeline)
            target = self.demand_forecast + self.safety_stock
            order  = target - self.inventory - pipeline_total

        order = max(0.0, order)
        self.order_history.append(order)
        return order

    # -- Production / fulfilment ------------------------------------------------

    def produce(self, inputs_available: float) -> float:
        """
        Produce goods given available upstream inputs.
        Output <= min(capacity, inputs_available).
        """
        if self.disrupted:
            if self.disruption_remaining > 0:
                self.disruption_remaining -= 1
                if self.disruption_remaining == 0:
                    self.disrupted = False
            # self.capacity was already set to base_capacity*(1-severity)
            # by apply_disruption(); use it directly.
            effective_cap = self.capacity
        else:
            effective_cap = self.capacity

        output = min(effective_cap, inputs_available)
        return output

    def receive_delivery(self, amount: float):
        """Receive goods from upstream (pipeline -> inventory)."""
        self.inventory += amount
        if self.pipeline:
            self.pipeline.pop(0)

    def ship(self, demand: float) -> Tuple[float, float]:
        """
        Fill demand from inventory.
        Returns (shipped, shortage).
        """
        shipped  = min(demand + self.backlog, self.inventory)
        shortage = max(0.0, (demand + self.backlog) - shipped)
        self.inventory -= shipped
        self.backlog    = shortage
        self.total_shortage += shortage

        self.inventory_history.append(self.inventory)
        self.shortage_history.append(shortage)
        self.price_history.append(self.price)
        return shipped, shortage

    def apply_disruption(self, duration_weeks: int, severity: float = 1.0):
        """
        Disrupt agent for `duration_weeks` weeks.
        severity in [0, 1]: fraction of capacity lost.
        """
        self.disrupted = True
        self.disruption_remaining = duration_weeks
        self.capacity = self.base_capacity * (1 - severity)

    def recover(self):
        """Gradually restore capacity."""
        if not self.disrupted:
            recovery = self.base_capacity * 0.05  # 5 % per week
            self.capacity = min(self.base_capacity, self.capacity + recovery)


# -- Supply chain network ------------------------------------------------------

def _lead_time_from_real_data(sector_idx: int, country: str) -> int:
    """Map sector x country to lead time in weeks from transit data."""
    # Assembly -> UK wholesale (main bottleneck)
    if sector_idx == 5:   # Garment Assembly
        td = TRANSIT_DAYS.get((country, "UK"), TRANSIT_DAYS.get(("China", "UK"), 37))
        return max(1, td // 7)
    # Chemical Processing: oil-producing countries to China
    if sector_idx == 1:
        td = TRANSIT_DAYS.get(("Saudi_Arabia", "China"), 23)
        return max(1, td // 7)
    # Default: 2 weeks
    return 2


class PolyesterSupplyChainABM:
    """
    Full agent-based simulation of the 8-stage polyester supply chain.

    The network is a directed graph: agents at stage s feed agents at stage s+1.
    Multiple agents can exist per sector (geographic multi-sourcing).
    """

    def __init__(self, agents_per_sector: int = 3):
        self.sectors = SECTORS
        self.n       = N_SECTORS
        self.agents: List[List[SupplyChainAgent]] = []  # [sector][agent]
        self._build_network(agents_per_sector)

    def _build_network(self, agents_per_sector: int):
        """
        Create agents at each stage weighted by real geographic shares.
        """
        for s_idx, sector in enumerate(SECTORS):
            geo = STAGE_GEOGRAPHY.get(sector, {"Other": 1.0})
            # Select top countries by share (up to agents_per_sector)
            top = sorted(geo.items(), key=lambda x: -x[1])[:agents_per_sector]
            sector_agents = []
            for country, share in top:
                lt = _lead_time_from_real_data(s_idx, country)
                agent = SupplyChainAgent(
                    name          = f"{sector}_{country}",
                    sector_idx    = s_idx,
                    country       = country,
                    base_capacity = share,   # normalised to 1 = global share
                    lead_time     = lt,
                )
                sector_agents.append(agent)
            self.agents.append(sector_agents)

    # -- Simulation ------------------------------------------------------------

    def run(self, T: int, baseline_demand: float,
            shock_schedule: Optional[Dict[int, Dict]] = None,
            demand_noise: float = 0.03,
            start_month: int = 1,
            apply_seasonality: bool = True,
            alpha: float = 0.3) -> Dict:
        """
        Simulate the supply chain for T weeks.

        Parameters
        ----------
        T                : weeks to simulate
        baseline_demand  : normalised weekly demand for final goods (=1)
        shock_schedule   : {week: {'sector': idx, 'country': str,
                                   'severity': float, 'duration': int}}
        demand_noise     : std dev of random demand fluctuations (fraction)

        Returns
        -------
        dict with per-sector time series of:
          inventory, shortage, orders, prices, capacity
        """
        n = N_SECTORS

        # Aggregate time-series (sum across agents per sector)
        agg_inventory = np.zeros((T, n))
        agg_shortage  = np.zeros((T, n))
        agg_orders    = np.zeros((T, n))
        agg_capacity  = np.zeros((T, n))
        agg_prices    = np.ones((T, n))

        # Initialise inventories
        for s_idx, sector_agents in enumerate(self.agents):
            for ag in sector_agents:
                agg_inventory[0, s_idx] += ag.inventory
                agg_capacity[0, s_idx]  += ag.base_capacity

        for t in range(1, T):
            # -- Apply shocks (list of shocks per week) -----------------------
            if shock_schedule and t in shock_schedule:
                shock_list = shock_schedule[t]
                if isinstance(shock_list, dict):
                    shock_list = [shock_list]   # backwards compat
                for shock in shock_list:
                    s_idx    = shock["sector"]
                    country  = shock.get("country", None)
                    severity = shock.get("severity", 0.8)
                    duration = shock.get("duration", 8)
                    for ag in self.agents[s_idx]:
                        if country is None or ag.country == country:
                            ag.apply_disruption(duration, severity)

            # -- Demand realisation --------------------------------------------
            noise  = RNG.normal(0, demand_noise)
            # Seasonal factor: map simulation week to calendar month (0-indexed)
            # HMRC_MONTHLY_SEASONAL_FACTORS derived from OTS API 2002-2024 average.
            if apply_seasonality:
                month_idx = ((start_month - 1 + (t * 7 // 30)) % 12)
                seasonal  = HMRC_MONTHLY_SEASONAL_FACTORS[month_idx]
            else:
                seasonal = 1.0
            demand = baseline_demand * seasonal * (1 + noise)

            # -- Simulate stage by stage (downstream -> upstream) ---------------
            downstream_demand = demand    # final consumer demand hits retail first

            for s_idx in range(n - 1, -1, -1):
                sector_agents = self.agents[s_idx]
                total_agents  = len(sector_agents)
                if total_agents == 0:
                    continue

                # Each agent handles its GLOBAL share of demand based on BASE
                # capacity (pre-disruption share). Using base_capacity for demand
                # assignment ensures that a disrupted agent still "sees" its full
                # share of demand but can only partially fulfil it (shortage).
                # Using current capacity would mask disruptions by simultaneously
                # reducing both demand and supply → no shortage observed.
                modeled_cap = sum(ag.base_capacity for ag in sector_agents) + 1e-12

                sector_shortage  = 0.0
                sector_shipped   = 0.0
                sector_inventory = 0.0
                sector_orders    = 0.0

                for ag in sector_agents:
                    # Agent's fair share uses BASE capacity (pre-disruption global
                    # share).  Disrupted capacity is lower, so ag_demand exceeds
                    # production → shortage is correctly recorded.
                    ag_demand = downstream_demand * ag.base_capacity

                    # Clean production model:
                    #   • inventory = finished-goods buffer (output stock)
                    #   • production = throughput limited by effective capacity
                    #   • production is NOT limited by inventory (no input-
                    #     scarcity feedback in standalone run; that is handled
                    #     by the IO model in coupled simulations)
                    #   • oil sector: unlimited inputs → always at full cap
                    produced = ag.produce(ag.base_capacity * 2)  # inputs unlimited
                    ag.inventory += produced

                    # Shipping to downstream — lost-sales model: unfulfilled demand
                    # is not carried forward as backlog (cleared each period).
                    # This prevents compounding backlog from amplifying shortages
                    # to orders-of-magnitude beyond the original disruption.
                    # Backlog is retained in step_period() for the coupled model.
                    ag.backlog = 0.0
                    shipped, shortage = ag.ship(ag_demand)
                    sector_shortage  += shortage
                    sector_shipped   += shipped
                    sector_inventory += ag.inventory

                    # Gradual capacity recovery
                    ag.recover()

                    # Ordering upstream using Sterman (1989) anchored-order rule
                    # (theta=4 periods).  Bounded: max order = demand + SS/4
                    # when inventory=0, preventing runaway upstream demand cascade.
                    # Pipeline rolls (pop oldest, append new) for order-accounting
                    # only (no physical delivery — goods come from production).
                    p_signal = 1.0 + shortage / (ag_demand + 1e-12)
                    ag.price = p_signal
                    order = ag.compute_order(ag_demand, p_signal, theta=4.0, alpha=alpha)
                    sector_orders += order

                    if ag.pipeline:
                        ag.pipeline.pop(0)   # conceptual delivery (order tracking)
                    ag.pipeline.append(order)

                # Scale modelled sector orders back to represent full sector
                # (extrapolate from top-N agents to full global sector demand).
                # At steady state this recovers downstream_demand exactly.
                scale = 1.0 / modeled_cap
                downstream_demand = sector_orders * scale

                # Record aggregates
                agg_inventory[t, s_idx] = sector_inventory
                agg_shortage[t, s_idx]  = sector_shortage
                agg_orders[t, s_idx]    = sector_orders
                agg_capacity[t, s_idx]  = sum(ag.capacity for ag in sector_agents)
                agg_prices[t, s_idx]    = 1.0 + sector_shortage / (demand + 1e-12)

        return {
            "inventory":  agg_inventory,
            "shortage":   agg_shortage,
            "orders":     agg_orders,
            "capacity":   agg_capacity,
            "prices":     agg_prices,
            "sectors":    SECTORS,
            "T":          T,
        }

    # -- Coupled-simulation helpers --------------------------------------------

    def reset(self) -> None:
        """
        Restore all agent state to post-__post_init__ defaults.
        Call before run_coupled() to get a clean simulation without
        reconstructing the network.
        """
        for sector_agents in self.agents:
            for ag in sector_agents:
                ss_weeks           = SAFETY_STOCK_WEEKS.get(SECTORS[ag.sector_idx], 4.0)
                ag.capacity        = ag.base_capacity
                ag.safety_stock    = ag.base_capacity * ss_weeks
                ag.inventory       = ag.safety_stock
                ag.demand_forecast = ag.base_capacity
                ag.backlog         = 0.0
                ag.pipeline        = [0.0] * max(1, ag.lead_time)
                ag.disrupted       = False
                ag.disruption_remaining = 0
                ag.total_shortage  = 0.0
                ag.total_cost      = 0.0
                ag.demand_history.clear()
                ag.inventory_history.clear()
                ag.order_history.clear()
                ag.shortage_history.clear()
                ag.price_history.clear()

    def step_period(self,
                    t: int,
                    demand: float,
                    external_prices: Optional[np.ndarray] = None,
                    io_supply_ratios: Optional[np.ndarray] = None,
                    demand_noise: float = 0.03,
                    start_month: int = 1,
                    apply_seasonality: bool = True,
                    shock_schedule: Optional[Dict] = None,
                    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        One period of the ABM with external CGE price signals and IO supply ratios.

        Parameters
        ----------
        t                : period index (for seasonality calculation).
        demand           : baseline demand scalar (= 1.0 normally).
        external_prices  : (n,) CGE equilibrium prices -- replaces the internal
                           shortage-proxy price signal in agents' ordering decisions.
        io_supply_ratios : (n,) IO supply fractions -- modulates pipeline fill rate
                           so IO shortfalls reduce how much agents actually receive.
        shock_schedule   : same format as run() shock_schedule.

        Returns
        -------
        agg_orders     : (n,) aggregate orders placed upstream by each sector
        agg_shortage   : (n,) aggregate shortage per sector
        agg_inventory  : (n,) aggregate inventory per sector
        """
        n = N_SECTORS

        # Apply shocks
        if shock_schedule and t in shock_schedule:
            shock_list = shock_schedule[t]
            if isinstance(shock_list, dict):
                shock_list = [shock_list]
            for shock in shock_list:
                s_idx    = shock["sector"]
                country  = shock.get("country", None)
                severity = shock.get("severity", 0.8)
                duration = shock.get("duration", 8)
                for ag in self.agents[s_idx]:
                    if country is None or ag.country == country:
                        ag.apply_disruption(duration, severity)

        # Demand realisation
        noise = RNG.normal(0, demand_noise)
        if apply_seasonality:
            month_idx = ((start_month - 1 + (t * 7 // 30)) % 12)
            seasonal  = HMRC_MONTHLY_SEASONAL_FACTORS[month_idx]
        else:
            seasonal = 1.0
        realized_demand = demand * seasonal * (1 + noise)

        agg_orders     = np.zeros(n)
        agg_shortage   = np.zeros(n)
        agg_inventory  = np.zeros(n)

        downstream_demand = realized_demand

        for s_idx in range(n - 1, -1, -1):
            sector_agents = self.agents[s_idx]
            if not sector_agents:
                continue

            modeled_cap = sum(ag.base_capacity for ag in sector_agents) + 1e-12

            # CGE price signal for this sector (falls back to shortage proxy)
            p_ext = float(external_prices[s_idx]) if external_prices is not None else None
            # IO fill rate: how much of the pipeline order is delivered
            fill  = float(io_supply_ratios[s_idx]) * 0.9 if io_supply_ratios is not None else 0.9
            fill  = float(np.clip(fill, 0.0, 1.0))

            sec_short = sec_ship = sec_inv = sec_ord = 0.0

            for ag in sector_agents:
                # Global-share normalisation using base_capacity (same as run())
                ag_demand = downstream_demand * ag.base_capacity

                inputs_avail  = ag.inventory if s_idx > 0 else ag.base_capacity * 2
                ss_deficit    = max(0.0, ag.safety_stock - ag.inventory)
                prod_needed   = max(0.0, ag_demand + ss_deficit)
                inputs_avail  = min(inputs_avail, prod_needed)

                produced  = ag.produce(inputs_avail)
                ag.inventory = max(0.0, ag.inventory - (ag_demand - produced))
                ag.inventory += produced

                shipped, shortage = ag.ship(ag_demand)
                sec_short += shortage
                sec_ship  += shipped
                sec_inv   += ag.inventory

                ag.recover()

                # Price signal: external CGE or internal shortage proxy
                p_sig = p_ext if p_ext is not None else (1.0 + shortage / (ag_demand + 1e-12))
                ag.price = p_sig
                order = ag.compute_order(ag_demand, p_sig)
                sec_ord += order

                ag.pipeline.append(order)
                if len(ag.pipeline) > ag.lead_time + 5:
                    ag.pipeline.pop(0)

                if len(ag.pipeline) >= ag.lead_time:
                    delivery = ag.pipeline[0] * fill
                    ag.receive_delivery(delivery)

            # Extrapolate to full sector and pass upstream
            downstream_demand = sec_ord / modeled_cap

            agg_orders[s_idx]    = sec_ord
            agg_shortage[s_idx]  = sec_short
            agg_inventory[s_idx] = sec_inv

        return agg_orders, agg_shortage, agg_inventory

    def compute_abm_flows(self,
                          X_abm: np.ndarray,
                          supply_fractions: np.ndarray,
                          A_current: np.ndarray,
                          A_base: np.ndarray = None,
                          min_coeff_frac: float = 0.5,
                          ) -> np.ndarray:
        """
        Micro -> Macro bridge: compute ABM-implied technical coefficient matrix.

        From the document (Section 4):
          Z_ij^ABM = Sum_a Sum_b z_ab^(j)  -- aggregate inter-sector deliveries
          a-hat_ij^ABM = Z_ij^ABM / X_i^ABM  -- implied technical coefficient

        Realized delivery from sector j to sector i:
          Z_ij = A_current[j,i] * X_i^ABM * min(1, supply_fractions[j])

        When supply of j is constrained (sf[j] < 1), firms in i receive less
        than planned -> a-hat_ij drops below A[j,i], reflecting actual network state.
        After sustained disruption firms adapt (imports reroute, substitutes found),
        and A evolves toward the new realized structure via the relaxed GS update.

        Parameters
        ----------
        X_abm            : (n,) aggregate output per sector from ABM step.
        supply_fractions : (n,) IO supply fractions for this iteration.
        A_current        : (n,n) current technical coefficient matrix.

        Returns
        -------
        A_hat : (n,n) ABM-implied technical coefficient matrix.
        """
        n      = self.n
        A_ref  = A_base if A_base is not None else A_current
        A_hat  = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if A_ref[j, i] < 1e-12:
                    continue
                # Effective supply fraction -- floors at min_coeff_frac so the
                # coefficient never collapses to 0 (firms maintain irreducible
                # minimum input requirements even in complete supply disruption).
                sf_eff      = float(np.clip(supply_fractions[j],
                                            min_coeff_frac, 1.0))
                A_hat[j, i] = A_ref[j, i] * sf_eff
        return A_hat

    def adapt_supplier_shares(self, eta: float = 0.05) -> None:
        """
        Adaptive supplier update rule (Section 3.2 of document):
          s_ab,t+1 proportional to s_ab,t * exp(-eta * eff_cost_ab)

        Effective cost is proxied by each agent recent shortage rate.
        Agents with high shortage (poor delivery) lose share;
        alternatives within the sector gain share proportionally.

        Only renormalises within sector so total sector capacity is conserved.
        """
        for sector_agents in self.agents:
            if len(sector_agents) < 2:
                continue   # no reallocation possible with a single supplier

            # Compute shortage-based effective cost for each agent
            eff_costs = []
            for ag in sector_agents:
                recent_short = sum(ag.shortage_history[-4:]) if ag.shortage_history else 0.0
                recent_ord   = sum(ag.order_history[-4:])    if ag.order_history   else 1e-12
                shortage_rate = recent_short / (recent_ord + 1e-12)
                eff_costs.append(float(np.clip(shortage_rate, 0.0, 1.0)))

            # s_new proportional to s_old * exp(-eta * eff_cost)
            weights = np.array([
                ag.base_capacity * np.exp(-eta * c)
                for ag, c in zip(sector_agents, eff_costs)
            ])

            total_old = sum(ag.base_capacity for ag in sector_agents)
            total_new = weights.sum()
            if total_new < 1e-12:
                continue

            scale = total_old / total_new
            for ag, w in zip(sector_agents, weights):
                ag.base_capacity = float(w * scale)

    # -- Derived metrics -------------------------------------------------------

    def bullwhip_ratio(self, results: Dict) -> pd.DataFrame:
        """
        Bullwhip effect: ratio of order variance to demand variance.
        BWE_s = Var(orders_s) / Var(final_demand)
        BWE > 1 means orders are more volatile than demand (supply amplification).

        Denominator is the retail (final) sector's order variance, with a floor
        equal to the mean-squared retail order to avoid division-by-zero when
        demand noise is zero or retail orders are nearly constant.
        """
        retail_orders = results["orders"][:, -1]
        mean_ret      = retail_orders.mean()
        # Floor: variance must be at least (1% of mean)^2 so BW is bounded when
        # demand noise is zero.  This equals exactly 1.0 when all sectors have
        # the same constant order rate (correct baseline behaviour).
        demand_var = max(np.var(retail_orders), (0.01 * mean_ret) ** 2, 1e-12)
        rows = []
        for j, s in enumerate(SECTORS):
            order_var = np.var(results["orders"][:, j])
            rows.append({
                "Sector":         s,
                "Order_Variance": order_var,
                "Bullwhip_Ratio": order_var / demand_var,
            })
        return pd.DataFrame(rows)

    def service_level(self, results: Dict) -> pd.DataFrame:
        """
        Service level = fraction of periods with zero shortage.
        Fill rate = shipped / demanded, using capacity as a proxy for demand
        when orders are near-zero (avoids -inf fill rate in no-noise baseline).
        """
        T = results["T"]
        rows = []
        for j, s in enumerate(SECTORS):
            shortage = results["shortage"][:, j]
            orders   = results["orders"][:, j]
            capacity = results.get("capacity", np.zeros((T, len(SECTORS))))[:, j]
            sl = (shortage < 1e-6).mean()
            # Use max(orders, capacity) as denominator so fill rate is ≥0
            denom = np.maximum(orders, capacity).sum() + 1e-12
            fill_rate = max(0.0, 1 - shortage.sum() / denom)
            rows.append({
                "Sector":          s,
                "Service_Level_%": sl * 100,
                "Fill_Rate_%":     fill_rate * 100,
                "Total_Shortage":  shortage.sum(),
            })
        return pd.DataFrame(rows)

    def recovery_time(self, results: Dict,
                      threshold: float = 0.95) -> pd.DataFrame:
        """
        Time to recover to `threshold` x baseline capacity after a shock.

        Algorithm (fix for always-0 bug):
          1. Use week-0 capacity as the true baseline (pre-shock).
          2. Find the first week the sector drops BELOW threshold x baseline
             (shock onset).  If it never drops, there is no disruption.
          3. Find the first week AFTER that trough where capacity returns
             to >= threshold x baseline.
          4. Recovery time = (recovery week) - (shock onset week).
        """
        rows = []
        baseline_cap = results["capacity"][0]   # pre-shock baseline (week 0)
        for j, s in enumerate(SECTORS):
            cap = results["capacity"][:, j]
            bc  = baseline_cap[j]
            if bc < 1e-12:
                rows.append({
                    "Sector": s, "Recovery_Week": None,
                    "Baseline_Cap": bc, "Trough_Cap": 0.0, "Trough_Cap_%": 0.0,
                    "Shock_Onset_Week": None,
                })
                continue

            thresh_abs = threshold * bc
            # Step 1: find first week capacity drops below threshold
            dropped = np.where(cap < thresh_abs)[0]
            if len(dropped) == 0:
                # No disruption for this sector
                rows.append({
                    "Sector":           s,
                    "Recovery_Week":    0,
                    "Baseline_Cap":     bc,
                    "Trough_Cap":       cap.min(),
                    "Trough_Cap_%":     cap.min() / bc * 100,
                    "Shock_Onset_Week": None,
                })
                continue

            onset = int(dropped[0])
            # Step 2: find first week AFTER onset where capacity recovers
            post_onset = cap[onset:]
            recovered  = np.where(post_onset >= thresh_abs)[0]
            if len(recovered) == 0:
                rt = None   # never recovered within simulation window
            else:
                rt = int(recovered[0])   # weeks from onset to recovery

            rows.append({
                "Sector":           s,
                "Recovery_Week":    rt,
                "Baseline_Cap":     bc,
                "Trough_Cap":       cap[onset:].min(),
                "Trough_Cap_%":     cap[onset:].min() / bc * 100,
                "Shock_Onset_Week": onset,
            })
        return pd.DataFrame(rows)
