"""
integrated_model.py
Integrates the Dynamic I-O, CGE, and ABM models into a single simulation.

Integration architecture:
  ┌─────────────┐    structural    ┌─────────────┐
  │  I-O Model  │ ──coefficients──▶│  CGE Model  │
  │ (Leontief)  │                  │  (prices /  │
  │ multipliers │◀── demand vec ──│ equilibrium)│
  └──────┬──────┘                  └──────┬──────┘
         │ output path                    │ price signals
         ▼                                ▼
  ┌─────────────────────────────────────────────┐
  │               ABM (Beer Game)               │
  │  Agents use I-O coefficients as input ratios │
  │  and CGE prices to form ordering decisions   │
  │  → emergent bullwhip, recovery trajectories  │
  └─────────────────────────────────────────────┘

Coupling steps each period t:
  1. ABM agents compute orders based on price signals from CGE
  2. I-O model computes structural multiplier effects of aggregate orders
  3. CGE clears markets, updates prices
  4. ABM agents receive deliveries and update inventories
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from io_model import DynamicIOModel
from cge_model import CGEModel, Q0, Q0_GBP
from abm_model import PolyesterSupplyChainABM
from shocks import Shock, build_cge_supply_array, build_io_shock_schedule
from resilience import (
    resilience_all_sectors, resilience_scorecard, scvi_all_sectors,
    hhi_all_sectors, effective_china_dependency_table,
    system_resilience_summary, shortage_value_gbp,
)
from real_data import SECTORS, N_SECTORS
from policies import Policy


class IntegratedSupplyChainModel:
    """
    Unified model coupling I-O, CGE, and ABM for the polyester supply chain.
    """

    def __init__(self):
        self.io  = DynamicIOModel()
        self.cge = CGEModel()
        self.abm = PolyesterSupplyChainABM(agents_per_sector=3)

        # Baseline final demand vector (normalised, retail = 1)
        self.fd_base = np.zeros(N_SECTORS)
        self.fd_base[-1] = 1.0             # all final demand enters at retail stage

        # Baseline outputs
        self.x_base = self.io.static_output(self.fd_base)

        # Baseline ABM orders per sector (capacity-normalised) for demand-mult conversion
        self._abm_baseline_orders = np.array([
            sum(ag.base_capacity for ag in self.abm.agents[j])
            for j in range(N_SECTORS)
        ])

    def rebuild_abm(self, agents_per_sector) -> None:
        """
        Replace the ABM network with new per-sector firm counts.

        Parameters
        ----------
        agents_per_sector : int or list[int]
            Passed directly to PolyesterSupplyChainABM.  A list must have
            N_SECTORS entries; an int applies to every stage.

        Call this before run_coupled() or run_coupled_gs() whenever the user
        changes the firm configuration so the coupled simulation uses the
        updated network.  The IO and CGE components are unaffected.
        """
        self.abm = PolyesterSupplyChainABM(agents_per_sector=agents_per_sector)
        # Recompute baseline order normalisation used by _abm_to_demand_mults()
        self._abm_baseline_orders = np.array([
            sum(ag.base_capacity for ag in self.abm.agents[j])
            for j in range(N_SECTORS)
        ])

    # ── Policy helpers ────────────────────────────────────────────────────────

    def _apply_policy_to_abm(self, policy: Optional[Policy]) -> None:
        """Apply pre-shock policy interventions to ABM agent state."""
        if policy is None:
            return

        # Buffer sectors: scale safety stock and initial inventory
        for sector_name, mult in policy.buffer_sectors.items():
            if sector_name not in SECTORS:
                continue
            s_idx = SECTORS.index(sector_name)
            for ag in self.abm.agents[s_idx]:
                ag.safety_stock *= mult
                ag.inventory    *= mult

        # Diversify sectors: shift divert_fraction of China capacity to non-China
        for sector_name, divert in policy.diversify_sectors.items():
            if sector_name not in SECTORS:
                continue
            s_idx = SECTORS.index(sector_name)
            agents = self.abm.agents[s_idx]
            china_agents = [ag for ag in agents
                            if ag.country in ("China", "China_PTA", "China_MEG")]
            other_agents = [ag for ag in agents
                            if ag.country not in ("China", "China_PTA", "China_MEG")]
            if not china_agents or not other_agents:
                continue
            freed = sum(ag.base_capacity * divert for ag in china_agents)
            for ag in china_agents:
                ag.base_capacity *= (1.0 - divert)
                ag.capacity       = ag.base_capacity
            other_total = sum(ag.base_capacity for ag in other_agents) + 1e-12
            for ag in other_agents:
                ag.base_capacity += freed * (ag.base_capacity / other_total)
                ag.capacity       = ag.base_capacity

        # Recompute baseline orders after capacity changes
        self._abm_baseline_orders = np.array([
            sum(ag.base_capacity for ag in self.abm.agents[j])
            for j in range(N_SECTORS)
        ])

    def _policy_rec_mult(self, policy: Optional[Policy]) -> np.ndarray:
        """Return per-sector recovery rate multipliers from policy.recovery_boost."""
        mult = np.ones(N_SECTORS)
        if policy is not None:
            for sector_name, boost in policy.recovery_boost.items():
                if sector_name in SECTORS:
                    mult[SECTORS.index(sector_name)] = float(boost)
        return mult

    def _reserve_schedule(self, policy: Optional[Policy],
                          onset_week: int, T: int) -> np.ndarray:
        """
        Return (T, N_SECTORS) array of capacity boosts from policy.reserve_release.
        Non-zero only during [onset + delay, onset + delay + duration).
        """
        boosts = np.zeros((T, N_SECTORS))
        if policy is None or not policy.reserve_release:
            return boosts
        t_start = onset_week + policy.release_delay_weeks
        t_end   = t_start + policy.release_duration_weeks
        for sector_name, frac in policy.reserve_release.items():
            if sector_name not in SECTORS:
                continue
            s_idx = SECTORS.index(sector_name)
            for t in range(max(0, t_start), min(T, t_end)):
                boosts[t, s_idx] = float(frac)
        return boosts

    def _policy_adjusted_io_sched(self, io_sched: Dict, policy: Optional[Policy]) -> Dict:
        """
        Scale IO shock fractions down at diversified stages.

        For each sector in policy.diversify_sectors, a fraction `divert` of
        China capacity has been moved to non-China suppliers.  The IO shock was
        calibrated assuming the original China dependency, so when China is
        disrupted the effective sector-level shock is proportionally smaller:

            adjusted_s_frac = s_frac * (1 - divert)

        This mirrors how the ABM agent capacities are redistributed in
        _apply_policy_to_abm and ensures IO/CGE welfare responds to P2.
        """
        if policy is None or not policy.diversify_sectors:
            return io_sched
        adj = {}
        for t, shocks in io_sched.items():
            new_shocks = []
            if isinstance(shocks, tuple):
                shocks = [shocks]
            for s_idx, s_frac in shocks:
                sec_name = SECTORS[s_idx] if s_idx < len(SECTORS) else None
                if sec_name and sec_name in policy.diversify_sectors:
                    divert = policy.diversify_sectors[sec_name]
                    s_frac = s_frac * (1.0 - divert)
                new_shocks.append((s_idx, s_frac))
            adj[t] = new_shocks
        return adj

    # ── Baseline characterisation ─────────────────────────────────────────────

    def baseline_report(self) -> Dict:
        """Full baseline characterisation of the supply chain."""
        linkages  = self.io.linkages()
        multip    = self.io.multipliers()
        calibration = self.io.calibration_report()
        hhi       = hhi_all_sectors()
        scvi      = scvi_all_sectors()
        eff_china = effective_china_dependency_table()
        geo_risk  = self.cge.geographic_risk_score()
        scorecard = resilience_scorecard()

        return {
            "linkages":     linkages,
            "multipliers":  multip,
            "calibration":  calibration,
            "hhi":          hhi,
            "scvi":         scvi,
            "eff_china":    eff_china,
            "geo_risk":     geo_risk,
            "scorecard":    scorecard,
        }

    # ── Single scenario run ───────────────────────────────────────────────────

    def run_scenario(self, scenario: Shock, T: int = 52,
                     verbose: bool = True) -> Dict:
        """
        Run all three model components for a given shock scenario.

        Returns
        -------
        dict with:
          'io_result'   : DynamicIOModel.simulate output
          'cge_result'  : CGEModel.equilibrium output
          'abm_result'  : PolyesterSupplyChainABM.run output
          'resilience'  : resilience triangle metrics
          'scorecard'   : resilience scorecard
          'trade_flows' : CGE trade flow rebalancing
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"Running scenario: {scenario.name}")
            print(f"  {scenario.description[:100]}...")
            print(f"{'='*60}")

        # ── 1. I-O model ──────────────────────────────────────────────────────
        io_shock_schedule = build_io_shock_schedule(scenario)
        io_result = self.io.simulate(
            T                  = T,
            final_demand_base  = self.fd_base,
            shock_schedule     = io_shock_schedule,
        )

        # ── 2. CGE model ──────────────────────────────────────────────────────
        # Apply tariffs if any
        cge_model = self.cge
        if scenario.tariffs:
            cge_model = CGEModel(tariff_schedule=scenario.tariffs)

        supply_shocks = build_cge_supply_array(scenario)
        cge_result = cge_model.equilibrium(
            supply_shocks = supply_shocks,
            final_demand  = self.fd_base,
        )

        if verbose:
            p_change = cge_result["price_index_change_pct"]
            max_p    = p_change.max()
            max_s    = SECTORS[p_change.argmax()]
            welfare  = cge_result["welfare_change_gbp"]
            print(f"  CGE: max price increase {max_p:.1f}% at {max_s}")
            print(f"  CGE: welfare change £{welfare/1e9:.2f}bn")
            print(f"  CGE: converged in {cge_result['iterations']} iterations")

        # ── 3. ABM model ──────────────────────────────────────────────────────
        # Use CGE price signals to modulate ABM demand noise
        # (higher CGE prices → agents order more precautionarily)
        max_price_signal = float(cge_result["equilibrium_prices"].max())
        demand_noise = 0.03 * max_price_signal   # price uncertainty amplifies noise

        abm_result = self.abm.run(
            T              = T,
            baseline_demand = 1.0,
            shock_schedule  = scenario.abm_schedule,
            demand_noise    = demand_noise,
        )

        # ── 4. Resilience metrics ─────────────────────────────────────────────
        res_triangle = resilience_all_sectors(io_result, self.x_base)
        scorecard    = resilience_scorecard(io_result, self.x_base)
        bullwhip     = self.abm.bullwhip_ratio(abm_result)
        service_lv   = self.abm.service_level(abm_result)
        rec_time     = self.abm.recovery_time(abm_result)

        # ── 5. Economic impact ────────────────────────────────────────────────
        # Total shortage converted to £bn
        uk_retail_gbp = 51_400_000_000
        polyester_share = 0.57 * 0.40   # polyester fraction of UK retail
        retail_shortage = io_result["shortage"][:, -1].sum()
        total_shortage_gbp = retail_shortage * uk_retail_gbp * polyester_share / 52

        if verbose:
            print(f"  I-O: total shortage (normalised) {io_result['shortage'].sum():.4f}")
            print(f"  I-O: estimated economic loss £{total_shortage_gbp/1e9:.3f}bn")
            print(f"  ABM: bullwhip ratio at garment stage "
                  f"{bullwhip.loc[bullwhip.Sector=='Garment_Assembly','Bullwhip_Ratio'].values[0]:.2f}")
            worst_sl = service_lv.loc[service_lv['Service_Level_%'].idxmin()]
            print(f"  ABM: worst service level at {worst_sl['Sector']} "
                  f"({worst_sl['Service_Level_%']:.1f}%)")

        return {
            "scenario":           scenario.name,
            "io_result":          io_result,
            "cge_result":         cge_result,
            "abm_result":         abm_result,
            "resilience_triangle": res_triangle,
            "scorecard":          scorecard,
            "bullwhip":           bullwhip,
            "service_level":      service_lv,
            "recovery_time":      rec_time,
            "trade_flows":        cge_result["trade_flows"],
            "total_shortage_gbp": total_shortage_gbp,
        }

    # ── Bidirectional coupled simulation ─────────────────────────────────────

    def _abm_to_demand_mults(self, agg_orders: np.ndarray) -> np.ndarray:
        """Convert ABM aggregate orders to CGE demand multipliers (1 = baseline)."""
        raw = agg_orders / (self._abm_baseline_orders + 1e-12)
        return np.clip(raw, 0.1, 5.0)

    def run_coupled(self, scenario: Shock, T: int = 52,
                    demand_noise: float = 0.03,
                    start_month: int = 1,
                    apply_seasonality: bool = True,
                    abm_demand_feedback: bool = False,
                    policy: Optional[Policy] = None,
                    verbose: bool = False) -> Dict:
        """
        Bidirectional per-period coupled simulation: IO ↔ CGE ↔ ABM.

        Each period t:
          1. IO step   → x(t), shortage(t), supply_fractions(t)
          2. CGE step  → prices(t) given IO supply + prior ABM demand
          3. ABM step  → orders(t) using CGE prices + IO fill rates
          4. Carry forward: CGE prices → IO capacity recovery multiplier
                            ABM orders → next-period CGE demand mults (if abm_demand_feedback)

        Feedback channels:
          IO  → CGE  : supply_fractions (sector output / baseline)
          IO  → ABM  : supply_fractions as pipeline fill-rate modifier
          CGE → ABM  : equilibrium price vector (drives precautionary ordering)
          CGE → IO   : price signal amplifies capacity recovery speed
          ABM → CGE  : EMA-smoothed order mults (optional; abm_demand_feedback=True)
                       Smoothing weight 0.10 dampens Beer-Game bullwhip so only
                       persistent demand shifts enter the CGE equilibrium.
        """
        io_sched  = self._policy_adjusted_io_sched(
                        build_io_shock_schedule(scenario), policy)
        abm_sched = scenario.abm_schedule
        n         = N_SECTORS

        # ── Initialise state ────────────────────────────────────────────────
        max_lag = int(self.io.lags.max())   # = 5
        buf_len = max_lag + 2               # 7 slots in circular buffer
        x_buf   = np.zeros((buf_len, n))
        x_buf[:] = self.x_base             # seed all lag slots at steady-state
        buf_ptr  = 0

        capacity      = np.ones(n)
        cge_prices    = np.ones(n)
        demand_mults  = np.ones(n)         # always exogenous (1.0); CGE final demand is exogenous
        cap_rec_mult  = np.ones(n)         # CGE → IO recovery multiplier

        # Output accumulators
        io_out   = np.zeros((T, n))
        io_short = np.zeros((T, n))
        io_cap   = np.ones((T, n))
        price_ts = np.ones((T, n))
        abm_ord  = np.zeros((T, n))
        abm_sht  = np.zeros((T, n))
        abm_inv  = np.zeros((T, n))
        sf_ts    = np.ones((T, n))         # supply fractions time-series

        io_out[0]   = self.x_base
        price_ts[0] = cge_prices
        io_cap[0]   = capacity

        self.abm.reset()
        self._apply_policy_to_abm(policy)

        # Pre-compute policy arrays
        pol_rec_mult  = self._policy_rec_mult(policy)   # (n,) static multiplier
        reserve_sched = self._reserve_schedule(policy, scenario.onset_week, T)  # (T, n)
        B_diag_manual = np.diag(self.io.B)              # for manual recovery step

        for t in range(1, T):
            # ── Supply shock ────────────────────────────────────────────────
            if io_sched and t in io_sched:
                shock_list = io_sched[t]
                if isinstance(shock_list, tuple):
                    shock_list = [shock_list]
                for s_idx, s_frac in shock_list:
                    capacity[s_idx] = max(0.0, capacity[s_idx] * (1 - s_frac))

            # ── 1. IO step ──────────────────────────────────────────────────
            fd = self.fd_base
            reserve_t = reserve_sched[t]
            combined_rec = cap_rec_mult * pol_rec_mult   # CGE price × policy boost

            if reserve_t.any():
                # Reserve active: boost effective capacity for output, but track
                # real capacity recovery separately so the reserve doesn't persist.
                eff_cap = np.minimum(capacity + reserve_t, 1.0)
                x_t, sht_t, sf_t = self.io.io_step(
                    x_buf, buf_ptr, eff_cap, fd, self.x_base, combined_rec,
                    apply_recovery=False,
                )
                for i in range(n):
                    if capacity[i] < 1.0:
                        base_rate    = 0.04 / (1.0 + 5.0 * B_diag_manual[i])
                        capacity[i]  = min(1.0, capacity[i] + base_rate * float(combined_rec[i]))
            else:
                x_t, sht_t, sf_t = self.io.io_step(
                    x_buf, buf_ptr, capacity, fd, self.x_base, combined_rec,
                )
            x_buf[buf_ptr] = x_t
            buf_ptr = (buf_ptr + 1) % buf_len

            # ── 2. CGE price step ───────────────────────────────────────────
            cge_prices = self.cge.price_step(sf_t, demand_mults, cge_prices)

            # ── 3. ABM step (CGE prices + IO fill rates) ────────────────────
            ord_t, asht_t, ainv_t = self.abm.step_period(
                t, demand=1.0,
                external_prices=cge_prices,
                io_supply_ratios=sf_t,
                demand_noise=demand_noise,
                start_month=start_month,
                apply_seasonality=apply_seasonality,
                shock_schedule=abm_sched,
            )

            # ── 4. Carry-forward ────────────────────────────────────────────
            # CGE final demand stays exogenous by default.  When
            # abm_demand_feedback=True, EMA-smooth ABM orders → demand_mults so
            # only persistent ordering shifts (not short-term bullwhip spikes)
            # influence CGE equilibrium prices next period.
            if abm_demand_feedback:
                raw_mults    = self._abm_to_demand_mults(ord_t)
                demand_mults = 0.90 * demand_mults + 0.10 * np.clip(raw_mults, 0.5, 1.5)
            cap_rec_mult = np.clip(cge_prices, 0.5, 3.0)

            # Store
            io_out[t]   = x_t
            io_short[t] = sht_t
            io_cap[t]   = capacity.copy()
            price_ts[t] = cge_prices
            sf_ts[t]    = sf_t
            abm_ord[t]  = ord_t
            abm_sht[t]  = asht_t
            abm_inv[t]  = ainv_t

        # ── Package results ─────────────────────────────────────────────────
        io_result = {
            "output": io_out, "shortage": io_short, "prices": price_ts,
            "capacity": io_cap, "sectors": SECTORS, "T": T,
        }
        abm_result = {
            "inventory": abm_inv, "shortage": abm_sht, "orders": abm_ord,
            "capacity": io_cap, "prices": price_ts, "sectors": SECTORS, "T": T,
        }

        res_triangle = resilience_all_sectors(io_result, self.x_base)
        scorecard    = resilience_scorecard(io_result, self.x_base)
        bullwhip     = self.abm.bullwhip_ratio(abm_result)
        service_lv   = self.abm.service_level(abm_result)
        rec_time     = self.abm.recovery_time(abm_result)

        uk_retail_gbp = 51_400_000_000
        poly_share    = 0.57 * 0.40
        retail_short  = io_short[:, -1].sum()
        total_loss    = retail_short * uk_retail_gbp * poly_share / 52
        # Welfare = average price deviation over all periods × sector output.
        # Using mean rather than final-period prices captures shocks that fully
        # recover before period T (fast-recovering downstream sectors like Garment
        # otherwise show zero welfare at week 51 even when severely disrupted).
        avg_prices  = price_ts.mean(axis=0)
        welfare_gbp = -(Q0_GBP * (avg_prices - 1)).sum()
        trade_flows   = self.cge._compute_trade_flows(avg_prices, sf_ts.mean(axis=0))

        if verbose:
            print(f"Coupled run — scenario {scenario.name}")
            print(f"  Max price: {price_ts.max():.3f}x  Max drop: {(1-io_out.min(axis=0)/self.x_base).max()*100:.1f}%")
            print(f"  Welfare: £{welfare_gbp/1e9:.3f}bn  Loss: £{total_loss/1e9:.3f}bn")

        return {
            "scenario":              scenario.name,
            "coupled":               True,
            "io_result":             io_result,
            "abm_result":            abm_result,
            "coupled_supply_fracs":  sf_ts,
            "cge_result": {
                "equilibrium_prices":    avg_prices,
                "price_series":          price_ts,
                "price_index_change_pct": (avg_prices - 1) * 100,
                "welfare_change_gbp":    welfare_gbp,
                "trade_flows":           trade_flows,
                "converged":             True,
                "iterations":            T,
            },
            "resilience_triangle":   res_triangle,
            "scorecard":             scorecard,
            "bullwhip":              bullwhip,
            "service_level":         service_lv,
            "recovery_time":         rec_time,
            "trade_flows":           trade_flows,
            "total_shortage_gbp":    total_loss,
            "welfare_gbp":           welfare_gbp,
        }

    # ── Gauss–Seidel coupled simulation (document architecture) ──────────────

    def run_coupled_gs(self, scenario: Shock, T: int = 52,
                       lambda_A: float = 0.08,
                       max_inner: int = 8,
                       eps_A: float = 1e-3,
                       eps_x: float = 1e-3,
                       demand_noise: float = 0.03,
                       start_month: int = 1,
                       apply_seasonality: bool = True,
                       abm_demand_feedback: bool = False,
                       policy: Optional[Policy] = None,
                       verbose: bool = False) -> Dict:
        """
        Bidirectional iterative coupling following the CGEABM document architecture.

        Within each macro period t, runs Gauss–Seidel (Picard) iterations k until
        the technical coefficient matrix A and sectoral output x both converge:

          Initialise:  A_t^(0) = A_{t-1}*

          Repeat k = 0, 1, … until convergence:
            Step 1 (CGE)  : prices^(k) = price_step(supply_fracs, demand_mults,
                                                     prev_prices, A=A_t^(k))
            Step 2 (IO)   : x^(k), sf^(k) = io_step(…, A=A_t^(k))
            Step 3 (ABM)  : orders^(k), X_abm^(k) = step_period(prices^(k), sf^(k))
            Step 4 (Â)    : Â_t^ABM^(k) = compute_abm_flows(X_abm, sf, A_t^(k))
            Step 5 (relax): A_t^(k+1) = (1−λ)·A_t^(k) + λ·Â_t^ABM^(k)
            Step 6 (check): stop if ‖ΔA‖ < ε_A and ‖Δx‖ < ε_X

          After convergence:
            Adapt supplier shares:  s_{ab,t+1} ∝ s_{ab,t}·exp(−η·eff_cost)
            Capital accumulation:   K_{t+1} = (1−δ)·K_t + I_t*  (δ = 0.002/wk)

        Parameters
        ----------
        lambda_A   : relaxation weight for A update ∈ (0,1]. Smaller = more stable.
        max_inner  : maximum Gauss–Seidel iterations per period.
        eps_A      : convergence tolerance on ‖ΔA‖_max.
        eps_x      : convergence tolerance on ‖Δx‖_max / x_baseline.
        """
        from io_model import A_BASE, B_BASE
        io_sched  = self._policy_adjusted_io_sched(
                        build_io_shock_schedule(scenario), policy)
        abm_sched = scenario.abm_schedule
        n         = N_SECTORS

        # ── Capital stock initialisation ────────────────────────────────────
        # K_i = base_capital * capacity; start at steady state (cap=1)
        # Depreciation δ = 0.002/week ≈ 10%/year
        delta     = 0.002
        K         = self.x_base.copy()         # normalised capital stock (1 = baseline)
        K_base    = self.x_base.copy()          # reference

        # ── IO history buffer ───────────────────────────────────────────────
        max_lag = int(self.io.lags.max())
        buf_len = max_lag + 2
        x_buf   = np.zeros((buf_len, n))
        x_buf[:] = self.x_base
        buf_ptr  = 0

        # ── Mutable A — start from calibrated base ──────────────────────────
        A_current = A_BASE.copy()
        self.io.set_A(A_current)

        capacity      = np.ones(n)
        cge_prices    = np.ones(n)
        demand_mults  = np.ones(n)
        cap_rec_mult  = np.ones(n)
        x_prev        = self.x_base.copy()

        # Output accumulators
        io_out   = np.zeros((T, n))
        io_short = np.zeros((T, n))
        io_cap   = np.ones((T, n))
        price_ts = np.ones((T, n))
        abm_ord  = np.zeros((T, n))
        abm_sht  = np.zeros((T, n))
        sf_ts    = np.ones((T, n))
        A_ts     = np.zeros((T, n, n))   # track A evolution
        gs_iters = np.zeros(T, dtype=int)  # GS iterations needed per period

        io_out[0]  = self.x_base
        A_ts[0]    = A_current.copy()

        self.abm.reset()
        self._apply_policy_to_abm(policy)

        # Pre-compute policy arrays
        pol_rec_mult  = self._policy_rec_mult(policy)   # (n,)
        reserve_sched = self._reserve_schedule(policy, scenario.onset_week, T)  # (T, n)

        abm_inv  = np.zeros((T, n))

        for t in range(1, T):

            # ── Supply shock (modifies capacity) ────────────────────────────
            if io_sched and t in io_sched:
                shock_list = io_sched[t]
                if isinstance(shock_list, tuple):
                    shock_list = [shock_list]
                for s_idx, s_frac in shock_list:
                    capacity[s_idx] = max(0.0, capacity[s_idx] * (1 - s_frac))

            # ── Gauss–Seidel inner loop ─────────────────────────────────────
            # Each iteration refines A, prices, and x until convergence.
            # capacity is NOT modified inside the loop (each iteration uses a
            # snapshot cap_snap) to avoid accumulating recovery N_inner times.
            # ABM step_period is also NOT called inside the loop to avoid
            # corrupting agent state; it runs once after convergence.
            A_k      = A_current.copy()
            prices_k = cge_prices.copy()
            x_k      = x_prev.copy()
            sf_k     = np.clip(x_k / (self.x_base + 1e-12), 0.0, 1.0)
            sht_k    = np.zeros(n)
            reserve_t = reserve_sched[t]
            # cap_snap includes reserve boost for output; GS uses this boosted snap
            cap_snap  = np.minimum(capacity + reserve_t, 1.0)

            delta_A = 0.0
            delta_x = 0.0

            for k in range(max_inner):

                # Step 1 — CGE: prices given current A_k and IO supply fracs
                self.io.set_A(A_k)
                prices_k = self.cge.price_step(
                    sf_k, demand_mults, prices_k, A=A_k
                )

                # Step 2 — IO: output given current A_k.
                # apply_recovery=False so capacity recovery does not accumulate
                # across GS iterations; it is applied exactly once after
                # convergence (below) using the converged price vector.
                x_new, sht_new, sf_k = self.io.io_step(
                    x_buf, buf_ptr, cap_snap.copy(),
                    self.fd_base, self.x_base, cap_rec_mult,
                    apply_recovery=False,
                )
                sht_k = sht_new

                # Step 3 — Micro→Macro: ABM-implied A from capacity fractions.
                # Use cap_snap (stable across iterations) so A recovers in
                # proportion to rebuilt capacity, not output ratio.
                cap_sf = np.clip(cap_snap, 0.0, 1.0)
                A_hat = self.abm.compute_abm_flows(
                    x_new, cap_sf, A_k, A_base=A_BASE
                )

                # Step 4 — Relaxed A update with Hawkins–Simon enforcement
                A_next = (1.0 - lambda_A) * A_k + lambda_A * A_hat
                col_sums = A_next.sum(axis=0)
                for j in range(n):
                    if col_sums[j] >= 1.0:
                        A_next[:, j] *= 0.95 / col_sums[j]

                # Step 5 — Convergence check
                delta_A = float(np.max(np.abs(A_next - A_k)))
                delta_x = float(np.max(
                    np.abs(x_new - x_k) / (self.x_base + 1e-12)
                ))

                x_k = x_new.copy()
                A_k = A_next

                if delta_A < eps_A and delta_x < eps_x:
                    gs_iters[t] = k + 1
                    break
            else:
                gs_iters[t] = max_inner

            # ── True ABM step (once per period, after GS convergence) ───────
            # Called here — not inside the GS loop — so agent state advances
            # exactly one period regardless of how many GS iterations ran.
            ord_k, asht_k, ainv_k = self.abm.step_period(
                t, demand=1.0,
                external_prices=prices_k,
                io_supply_ratios=sf_k,
                demand_noise=demand_noise,
                start_month=start_month,
                apply_seasonality=apply_seasonality,
                shock_schedule=abm_sched,
            )

            # ── Accept converged A and update circular buffer ────────────────
            A_current      = A_k
            x_buf[buf_ptr] = x_k          # write converged x(t) for future lags
            buf_ptr        = (buf_ptr + 1) % buf_len

            # ── Adaptive supplier shares (document Section 3.2) ─────────────
            self.abm.adapt_supplier_shares(eta=0.05)

            # ── Capital accumulation ─────────────────────────────────────────
            delta_x_vec   = np.maximum(0.0, x_k - x_prev)
            I_replacement = delta * K
            I_expansion   = self.io.B @ delta_x_vec
            K             = (1.0 - delta) * K + I_replacement + I_expansion
            cap_from_K    = np.clip(K / (K_base + 1e-12), 0.0, 2.0)

            # ── One-shot capacity recovery with converged prices ─────────────
            # Start from cap_snap (capacity at start of period t, post-shock)
            # and apply exactly ONE recovery step using the converged price
            # vector.  This corrects the prior double-recovery bug where
            # io_step applied recovery during GS iterations AND a second manual
            # step ran here afterward.
            B_diag    = np.diag(self.io.B)
            # Combined recovery multiplier: CGE price signal × policy boost
            price_rec = np.clip(prices_k, 0.5, 3.0) * pol_rec_mult
            # Recover from pre-shock capacity (not boosted snap) so reserve
            # doesn't permanently accelerate underlying infrastructure rebuild.
            capacity  = capacity.copy()   # already the pre-period value (cap_snap minus reserve)
            for i in range(n):
                if capacity[i] < 1.0:
                    base_rate    = 0.04 / (1.0 + 5.0 * B_diag[i])
                    capacity[i]  = min(1.0, capacity[i] + base_rate * float(price_rec[i]))
            capacity = np.minimum(capacity, cap_from_K)

            # ── Carry-forward state ──────────────────────────────────────────
            cap_rec_mult = np.clip(prices_k, 0.5, 3.0)
            # Optional ABM→CGE demand feedback: EMA-smooth ABM orders so only
            # sustained demand shifts (not short-term bullwhip) reach CGE.
            if abm_demand_feedback:
                raw_mults    = self._abm_to_demand_mults(ord_k)
                demand_mults = 0.90 * demand_mults + 0.10 * np.clip(raw_mults, 0.5, 1.5)
            cge_prices   = prices_k.copy()
            x_prev       = x_k.copy()

            # Store
            io_out[t]   = x_k
            io_short[t] = sht_k
            io_cap[t]   = capacity.copy()
            price_ts[t] = prices_k
            sf_ts[t]    = sf_k
            abm_ord[t]  = ord_k
            abm_sht[t]  = asht_k
            abm_inv[t]  = ainv_k
            A_ts[t]     = A_current.copy()

            if verbose and t % 10 == 0:
                print(f"  t={t:3d}  GS iters={gs_iters[t]}  "
                      f"dA={delta_A:.4f}  max_price={prices_k.max():.3f}")

        # Restore IO to baseline A so other model methods are unaffected
        self.io.set_A(A_BASE.copy())

        # ── Package results ─────────────────────────────────────────────────
        io_result = {
            "output": io_out, "shortage": io_short, "prices": price_ts,
            "capacity": io_cap, "investment": np.zeros((T, n)),
            "sectors": SECTORS, "T": T,
        }
        abm_result = {
            "inventory": abm_inv, "shortage": abm_sht,
            "orders": abm_ord, "capacity": io_cap,
            "prices": price_ts, "sectors": SECTORS, "T": T,
        }

        res_triangle = resilience_all_sectors(io_result, self.x_base)
        scorecard    = resilience_scorecard(io_result, self.x_base)
        bullwhip     = self.abm.bullwhip_ratio(abm_result)
        service_lv   = self.abm.service_level(abm_result)
        rec_time     = self.abm.recovery_time(abm_result)

        uk_retail_gbp  = 51_400_000_000
        poly_share     = 0.57 * 0.40
        retail_short   = io_short[:, -1].sum()
        total_loss     = retail_short * uk_retail_gbp * poly_share / 52
        avg_prices_gs  = price_ts.mean(axis=0)
        welfare_gbp    = -(Q0_GBP * (avg_prices_gs - 1)).sum()
        trade_flows    = self.cge._compute_trade_flows(avg_prices_gs, sf_ts.mean(axis=0))

        # A-matrix drift: how much has A changed from baseline by period end?
        A_drift = np.abs(A_ts[-1] - A_BASE).max()

        return {
            "scenario":             scenario.name,
            "coupled_gs":           True,
            "io_result":            io_result,
            "abm_result":           abm_result,
            "coupled_supply_fracs": sf_ts,
            "A_evolution":          A_ts,
            "A_drift_final":        float(A_drift),
            "gs_iterations":        gs_iters,
            "cge_result": {
                "equilibrium_prices":     avg_prices_gs,
                "price_series":           price_ts,
                "price_index_change_pct": (avg_prices_gs - 1) * 100,
                "welfare_change_gbp":     welfare_gbp,
                "trade_flows":            trade_flows,
                "converged":              True,
                "iterations":             T,
            },
            "resilience_triangle":  res_triangle,
            "scorecard":            scorecard,
            "bullwhip":             bullwhip,
            "service_level":        service_lv,
            "recovery_time":        rec_time,
            "trade_flows":          trade_flows,
            "total_shortage_gbp":   total_loss,
            "welfare_gbp":          welfare_gbp,
        }

    # ── Multi-scenario comparison ─────────────────────────────────────────────

    def run_all_scenarios(self, scenarios: Dict[str, Shock],
                           T: int = 52) -> Dict[str, Dict]:
        """Run all scenarios and return a nested results dict."""
        results = {}
        for key, scenario in scenarios.items():
            results[key] = self.run_scenario(scenario, T=T)
        return results

    def comparison_table(self, all_results: Dict[str, Dict]) -> pd.DataFrame:
        """
        Side-by-side comparison of all scenarios across key metrics.
        """
        rows = []
        for sc_key, res in all_results.items():
            cge  = res["cge_result"]
            io_r = res["io_result"]
            abm  = res["abm_result"]
            rec  = res["recovery_time"]
            bw   = res["bullwhip"]
            sl   = res["service_level"]

            # Worst-affected sector (highest IO shortage)
            io_shortage_by_sector = io_r["shortage"].sum(axis=0)
            worst_idx = int(io_shortage_by_sector.argmax())
            worst_sec = SECTORS[worst_idx]

            # Max CGE price increase
            p_change  = cge["price_index_change_pct"]
            max_p_sec = SECTORS[int(p_change.argmax())]

            # Weighted average recovery time (ABM)
            rt_vals = rec["Recovery_Week"].dropna()
            avg_rec = float(rt_vals.mean()) if len(rt_vals) > 0 else None

            # Bullwhip at retail (amplification arriving at consumer)
            bw_retail = bw.loc[bw.Sector == "UK_Retail", "Bullwhip_Ratio"].values
            bw_retail_v = float(bw_retail[0]) if len(bw_retail) > 0 else np.nan

            rows.append({
                "Scenario":                 sc_key,
                "Max_Price_Rise_%":         round(p_change.max(), 1),
                "Max_Price_Sector":         max_p_sec,
                "Welfare_Change_£bn":       round(cge["welfare_change_gbp"] / 1e9, 3),
                "Economic_Loss_£bn":        round(res["total_shortage_gbp"] / 1e9, 3),
                "IO_Total_Shortage":        round(io_shortage_by_sector.sum(), 4),
                "Worst_Sector":             worst_sec,
                "Avg_Recovery_Weeks":       round(avg_rec, 1) if avg_rec else "No recovery",
                "Bullwhip_Ratio_Retail":    round(bw_retail_v, 2),
                "CGE_Converged":            cge["converged"],
            })

        return pd.DataFrame(rows)
