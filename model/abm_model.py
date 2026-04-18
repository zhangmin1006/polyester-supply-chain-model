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


# ── Agent definitions ─────────────────────────────────────────────────────────

@dataclass
class SupplyChainAgent:
    """
    Represents a node in the supply chain (one sector × one country).

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
    lead_time:     int   = 2      # weeks (order→receipt)
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

    # ── Forecasting ───────────────────────────────────────────────────────────

    def update_forecast(self, alpha: float = 0.3):
        """Exponential smoothing forecast."""
        if self.demand_history:
            d = self.demand_history[-1]
            self.demand_forecast = alpha * d + (1 - alpha) * self.demand_forecast

    # ── Ordering decision ─────────────────────────────────────────────────────

    def compute_order(self, demand: float, price_signal: float = 1.0) -> float:
        """
        Order-up-to policy.
        When prices rise (scarcity signal), agents may increase safety stock
        (precautionary ordering → bullwhip effect).
        """
        self.demand_history.append(demand)
        self.update_forecast()

        # Adaptive safety stock: increase when supply is uncertain (price > 1.1)
        if price_signal > 1.1:
            self.safety_stock = min(
                self.safety_stock * 1.05,
                self.base_capacity * 20   # cap at 20 weeks
            )
        elif price_signal < 1.0:
            self.safety_stock = max(
                self.safety_stock * 0.98,
                self.base_capacity * SAFETY_STOCK_WEEKS.get(
                    SECTORS[self.sector_idx], 2.0)
            )

        pipeline_total = sum(self.pipeline)
        target = self.demand_forecast + self.safety_stock
        order  = max(0.0, target - self.inventory - pipeline_total)

        self.order_history.append(order)
        return order

    # ── Production / fulfilment ────────────────────────────────────────────────

    def produce(self, inputs_available: float) -> float:
        """
        Produce goods given available upstream inputs.
        Output ≤ min(capacity, inputs_available).
        """
        if self.disrupted:
            if self.disruption_remaining > 0:
                self.disruption_remaining -= 1
                if self.disruption_remaining == 0:
                    self.disrupted = False
            # Disrupted: only 5 % output
            effective_cap = self.capacity * 0.05
        else:
            effective_cap = self.capacity

        output = min(effective_cap, inputs_available)
        return output

    def receive_delivery(self, amount: float):
        """Receive goods from upstream (pipeline → inventory)."""
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
        severity ∈ [0, 1]: fraction of capacity lost.
        """
        self.disrupted = True
        self.disruption_remaining = duration_weeks
        self.capacity = self.base_capacity * (1 - severity)

    def recover(self):
        """Gradually restore capacity."""
        if not self.disrupted:
            recovery = self.base_capacity * 0.05  # 5 % per week
            self.capacity = min(self.base_capacity, self.capacity + recovery)


# ── Supply chain network ──────────────────────────────────────────────────────

def _lead_time_from_real_data(sector_idx: int, country: str) -> int:
    """Map sector × country to lead time in weeks from transit data."""
    # Assembly → UK wholesale (main bottleneck)
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

    # ── Simulation ────────────────────────────────────────────────────────────

    def run(self, T: int, baseline_demand: float,
            shock_schedule: Optional[Dict[int, Dict]] = None,
            demand_noise: float = 0.03,
            start_month: int = 1,
            apply_seasonality: bool = True) -> Dict:
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
            # ── Apply shocks (list of shocks per week) ───────────────────────
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

            # ── Demand realisation ────────────────────────────────────────────
            noise  = RNG.normal(0, demand_noise)
            # Seasonal factor: map simulation week to calendar month (0-indexed)
            # HMRC_MONTHLY_SEASONAL_FACTORS derived from OTS API 2002-2024 average.
            if apply_seasonality:
                month_idx = ((start_month - 1 + (t * 7 // 30)) % 12)
                seasonal  = HMRC_MONTHLY_SEASONAL_FACTORS[month_idx]
            else:
                seasonal = 1.0
            demand = baseline_demand * seasonal * (1 + noise)

            # ── Simulate stage by stage (downstream → upstream) ───────────────
            downstream_demand = demand    # final consumer demand hits retail first

            for s_idx in range(n - 1, -1, -1):
                sector_agents = self.agents[s_idx]
                total_agents  = len(sector_agents)
                if total_agents == 0:
                    continue

                # Distribute demand across agents proportional to capacity share
                total_cap = sum(ag.capacity for ag in sector_agents) + 1e-12

                sector_shortage = 0.0
                sector_shipped  = 0.0
                sector_inventory = 0.0
                sector_orders   = 0.0

                for ag in sector_agents:
                    cap_share = ag.capacity / total_cap
                    ag_demand = downstream_demand * cap_share

                    # Upstream inputs available = inventory from previous period
                    if s_idx > 0:
                        inputs_avail = ag.inventory
                    else:
                        inputs_avail = ag.base_capacity * 2  # oil is not constrained

                    # Production
                    produced  = ag.produce(inputs_avail)
                    ag.inventory = max(0.0, ag.inventory - (ag_demand - produced))
                    ag.inventory += produced

                    # Shipping to downstream
                    shipped, shortage = ag.ship(ag_demand)
                    sector_shortage  += shortage
                    sector_shipped   += shipped
                    sector_inventory += ag.inventory

                    # Recovery
                    ag.recover()

                    # Ordering upstream
                    # Price signal: proxy by shortage ratio
                    p_signal = 1.0 + shortage / (ag_demand + 1e-12)
                    ag.price = p_signal
                    order = ag.compute_order(ag_demand, p_signal)
                    sector_orders += order

                    # Add orders to pipeline
                    ag.pipeline.append(order)
                    if len(ag.pipeline) > ag.lead_time + 5:
                        ag.pipeline.pop(0)

                    # Simulate pipeline delivery
                    if len(ag.pipeline) >= ag.lead_time:
                        delivery = ag.pipeline[0] * 0.9   # 90 % fill rate
                        ag.receive_delivery(delivery)

                # Upstream demand = total orders placed by this sector
                downstream_demand = sector_orders

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

    # ── Derived metrics ───────────────────────────────────────────────────────

    def bullwhip_ratio(self, results: Dict) -> pd.DataFrame:
        """
        Bullwhip effect: ratio of order variance to demand variance.
        BWE_s = Var(orders_s) / Var(final_demand)
        BWE > 1 means orders are more volatile than demand → supply amplification.
        """
        demand_var = np.var(results["orders"][:, -1]) + 1e-12
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
        """
        T = results["T"]
        rows = []
        for j, s in enumerate(SECTORS):
            shortage = results["shortage"][:, j]
            orders   = results["orders"][:, j]
            sl = (shortage < 1e-6).mean()
            fill_rate = 1 - shortage.sum() / (orders.sum() + 1e-12)
            rows.append({
                "Sector":        s,
                "Service_Level_%": sl * 100,
                "Fill_Rate_%":    fill_rate * 100,
                "Total_Shortage": shortage.sum(),
            })
        return pd.DataFrame(rows)

    def recovery_time(self, results: Dict,
                      threshold: float = 0.95) -> pd.DataFrame:
        """
        Time to recover to `threshold` × baseline capacity after a shock.

        Algorithm (fix for always-0 bug):
          1. Use week-0 capacity as the true baseline (pre-shock).
          2. Find the first week the sector drops BELOW threshold × baseline
             (shock onset).  If it never drops, there is no disruption.
          3. Find the first week AFTER that trough where capacity returns
             to >= threshold × baseline.
          4. Recovery time = (recovery week) − (shock onset week).
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
