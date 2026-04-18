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
        total_shortage_gbp = (
            io_result["shortage"].sum()
            * uk_retail_gbp
            * polyester_share
            / self.x_base.sum()
        )

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
                    verbose: bool = False) -> Dict:
        """
        Bidirectional per-period coupled simulation: IO ↔ CGE ↔ ABM.

        Each period t:
          1. IO step   → x(t), shortage(t), supply_fractions(t)
          2. CGE step  → prices(t) given IO supply + prior ABM demand
          3. ABM step  → orders(t) using CGE prices + IO fill rates
          4. Carry forward: ABM orders → next-period CGE demand mults
                            CGE prices → IO capacity recovery multiplier

        Feedback channels (all bidirectional):
          IO  → CGE  : supply_fractions (sector output / baseline)
          IO  → ABM  : supply_fractions as pipeline fill-rate modifier
          CGE → ABM  : equilibrium price vector (drives precautionary ordering)
          ABM → CGE  : aggregate order multipliers (demand-side pressure)
          CGE → IO   : price signal amplifies capacity recovery speed
        """
        io_sched  = build_io_shock_schedule(scenario)
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
        demand_mults  = np.ones(n)         # ABM demand signal, starts at baseline
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

        for t in range(1, T):
            # ── Supply shock ────────────────────────────────────────────────
            if io_sched and t in io_sched:
                shock_list = io_sched[t]
                if isinstance(shock_list, tuple):
                    shock_list = [shock_list]
                for s_idx, s_frac in shock_list:
                    capacity[s_idx] = max(0.0, capacity[s_idx] * (1 - s_frac))

            # ── 1. IO step ──────────────────────────────────────────────────
            # IO uses exogenous final demand — consumer demand doesn't collapse
            # with agent order behaviour. ABM demand_mults feed CGE only.
            fd = self.fd_base
            x_buf[buf_ptr] = io_out[t - 1]   # write last period before step
            x_t, sht_t, sf_t = self.io.io_step(
                x_buf, buf_ptr, capacity, fd, self.x_base, cap_rec_mult,
            )
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
            demand_mults = self._abm_to_demand_mults(ord_t)
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
        total_loss    = (
            io_short.sum() * uk_retail_gbp * poly_share / (self.x_base.sum() + 1e-12)
        )
        welfare_gbp   = -(Q0_GBP * (price_ts[-1] - 1)).sum()
        trade_flows   = self.cge._compute_trade_flows(price_ts[-1], sf_ts[-1])

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
                "equilibrium_prices":    price_ts[-1],
                "price_series":          price_ts,
                "price_index_change_pct": (price_ts[-1] - 1) * 100,
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
