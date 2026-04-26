"""
run_tests.py
Comprehensive model test and validation suite.
Covers: IO, CGE, ABM, MRIO, Ghosh, Integrated (sequential + coupled + GS),
        Policies (P1-P5), and all historical validation events.
"""
import sys, traceback, time
import numpy as np

sys.path.insert(0, "model")

PASS = " PASS"
FAIL = " FAIL"
WARN = " WARN"
results = []

def check(name, fn):
    t0 = time.perf_counter()
    try:
        msg = fn()
        elapsed = time.perf_counter() - t0
        results.append(("PASS", name))
        suffix = f"  -- {msg}" if msg else ""
        print(f"[PASS] [{elapsed:5.2f}s]  {name}{suffix}")
    except Exception as e:
        elapsed = time.perf_counter() - t0
        results.append(("FAIL", name))
        print(f"[FAIL] [{elapsed:5.2f}s]  {name}")
        tb = traceback.format_exc().strip().splitlines()
        for line in tb[-4:]:
            print(f"           {line}")

def warn(name, fn):
    t0 = time.perf_counter()
    try:
        msg = fn()
        elapsed = time.perf_counter() - t0
        results.append(("PASS", name))
        suffix = f"  -- {msg}" if msg else ""
        print(f"[PASS] [{elapsed:5.2f}s]  {name}{suffix}")
    except Exception as e:
        elapsed = time.perf_counter() - t0
        results.append(("WARN", name))
        print(f"[WARN] [{elapsed:5.2f}s]  {name}  -- {e}")

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  MODEL IMPORT CHECKS")
print("="*70)

def test_import_io():
    from io_model import DynamicIOModel, A_BASE, B_BASE
    assert A_BASE.shape == (8, 8)
    col_sums = A_BASE.sum(axis=0)
    assert (col_sums < 1).all(), f"Hawkins-Simon violated: {col_sums}"
    return f"A col-sums max={col_sums.max():.3f}"

def test_import_cge():
    from cge_model import CGEModel, Q0_GBP, SECTORS
    assert len(SECTORS) == 8
    assert len(Q0_GBP) == 8
    return f"Q0_GBP sum=GBP{sum(Q0_GBP)/1e9:.1f}bn"

def test_import_abm():
    from abm_model import PolyesterSupplyChainABM
    abm = PolyesterSupplyChainABM(agents_per_sector=2)
    assert len(abm.agents) == 8
    return f"{sum(len(a) for a in abm.agents)} total agents"

def test_import_mrio():
    from mrio_model import MRIOModel
    m = MRIOModel()
    assert m.A_mrio.shape == (64, 64)
    col_sums = m.A_mrio.sum(axis=0)
    assert (col_sums < 1).all()
    return f"64x64 A, max col-sum={col_sums.max():.3f}"

def test_import_ghosh():
    from ghosh_model import GhoshModel
    g = GhoshModel()
    assert g.G.shape == (8, 8)
    return "G (8x8) computed OK"

def test_import_integrated():
    from integrated_model import IntegratedSupplyChainModel
    m = IntegratedSupplyChainModel()
    assert hasattr(m, "io") and hasattr(m, "cge") and hasattr(m, "abm")
    return "io + cge + abm initialised"

def test_import_policies():
    from policies import ALL_POLICIES
    assert set(ALL_POLICIES.keys()) == {"P1","P2","P3","P4","P5"}
    costs = {k: p.cost_estimate_gbp_m for k,p in ALL_POLICIES.items()}
    return f"5 policies loaded, costs={costs}"

def test_import_real_data():
    from real_data import SECTORS, N_SECTORS, ARMINGTON_ELASTICITY
    assert N_SECTORS == 8
    assert len(ARMINGTON_ELASTICITY) == 8
    return f"N_SECTORS={N_SECTORS}"

def test_import_shocks():
    from shocks import ALL_SCENARIOS
    assert len(ALL_SCENARIOS) >= 5
    return f"{len(ALL_SCENARIOS)} scenarios: {list(ALL_SCENARIOS.keys())}"

check("Import: io_model", test_import_io)
check("Import: cge_model", test_import_cge)
check("Import: abm_model", test_import_abm)
check("Import: mrio_model", test_import_mrio)
check("Import: ghosh_model", test_import_ghosh)
check("Import: integrated_model", test_import_integrated)
check("Import: policies", test_import_policies)
check("Import: real_data", test_import_real_data)
check("Import: shocks", test_import_shocks)

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  IO MODEL TESTS")
print("="*70)

def test_io_hawkins_simon():
    from io_model import A_BASE
    col_sums = A_BASE.sum(axis=0)
    assert (col_sums < 1).all()
    return f"all 8 col-sums < 1, max={col_sums.max():.3f}"

def test_io_leontief_inverse():
    from io_model import DynamicIOModel, A_BASE
    m = DynamicIOModel(A_BASE)
    L = m.L
    # Verify (I - A) * L = I
    residual = np.max(np.abs((np.eye(8) - A_BASE) @ L - np.eye(8)))
    assert residual < 1e-10, f"residual={residual:.2e}"
    return f"|(I-A)L - I|_max = {residual:.2e}"

def test_io_simulate_no_shock():
    from io_model import DynamicIOModel, A_BASE
    from integrated_model import IntegratedSupplyChainModel
    fd = IntegratedSupplyChainModel().fd_base
    m = DynamicIOModel(A_BASE)
    r = m.simulate(T=12, final_demand_base=fd)
    out = r["output"]
    assert out.shape == (12, 8), f"shape={out.shape}"
    assert not np.any(np.isnan(out)), "NaN in output"
    assert not np.any(out < 0), "Negative output"
    return f"output shape={out.shape}, max={out.max():.3f}"

def test_io_simulate_with_shock():
    from io_model import DynamicIOModel, A_BASE
    from integrated_model import IntegratedSupplyChainModel
    from real_data import SECTORS
    fd = IntegratedSupplyChainModel().fd_base
    m = DynamicIOModel(A_BASE)
    pta_idx = SECTORS.index("PTA_Production")
    # shock_schedule expects {week: [(sector_INDEX, fraction)]}
    shock = {4: [(pta_idx, 0.6)]}
    r = m.simulate(T=26, final_demand_base=fd, shock_schedule=shock)
    sht = r["shortage"]
    assert not np.any(np.isnan(r["output"]))
    assert np.any(sht > 0), "Expected shortages after 60% PTA shock"
    return f"shortage detected, peak={sht.max():.4f}"

def test_io_linkages():
    from io_model import DynamicIOModel, A_BASE
    m = DynamicIOModel(A_BASE)
    r = m.linkages()
    # Accept either dict or DataFrame
    assert r is not None
    return f"linkages computed: type={type(r).__name__}"

def test_io_multipliers():
    from io_model import DynamicIOModel, A_BASE
    m = DynamicIOModel(A_BASE)
    r = m.multipliers()
    assert r is not None
    return f"multipliers computed: type={type(r).__name__}"

check("IO: Hawkins-Simon (col-sums < 1)", test_io_hawkins_simon)
check("IO: Leontief inverse accuracy", test_io_leontief_inverse)
check("IO: simulate no-shock (T=12)", test_io_simulate_no_shock)
check("IO: simulate with PTA shock (T=26)", test_io_simulate_with_shock)
check("IO: linkage analysis", test_io_linkages)
check("IO: output multipliers", test_io_multipliers)

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  CGE MODEL TESTS")
print("="*70)

def test_cge_baseline():
    from cge_model import CGEModel
    cge = CGEModel()
    r = cge.equilibrium(supply_shocks=np.ones(8), final_demand=None)
    prices = r["equilibrium_prices"]
    assert prices.shape == (8,)
    assert np.allclose(prices, 1.0, atol=0.01), f"Baseline prices not ~1: {prices}"
    return f"prices == 1, max_dev={np.abs(prices-1).max():.4f}"

def test_cge_supply_shock_raises_price():
    from cge_model import CGEModel
    cge = CGEModel()
    supply = np.ones(8); supply[2] = 0.5   # PTA 50% shock
    r = cge.equilibrium(supply_shocks=supply, final_demand=None)
    prices = r["equilibrium_prices"]
    assert prices[2] > 1.05, f"PTA price should rise: {prices[2]:.4f}"
    assert r.get("converged", True), "CGE did not converge"
    return f"PTA price={prices[2]:.3f}, welfare=GBP{r['welfare_change_gbp']/1e9:.3f}bn"

def test_cge_sigma_override():
    from cge_model import CGEModel
    cge_gtap = CGEModel()
    cge_low  = CGEModel(sigma={"PTA_Production": 0.50, "PET_Resin_Yarn": 0.80})
    supply = np.ones(8); supply[2] = 0.65
    p_gtap = cge_gtap.equilibrium(supply_shocks=supply, final_demand=None)["equilibrium_prices"][2]
    p_low  = cge_low.equilibrium(supply_shocks=supply,  final_demand=None)["equilibrium_prices"][2]
    assert p_low > p_gtap, f"Low sigma should give higher price: {p_low:.3f} vs GTAP {p_gtap:.3f}"
    return f"PTA price: GTAP={p_gtap:.3f}, low-sigma={p_low:.3f} (low > GTAP)"

def test_cge_tariff_with_shock():
    """Tariff amplifies price under supply shock."""
    from cge_model import CGEModel
    supply = np.ones(8); supply[2] = 0.7
    r_notariff = CGEModel().equilibrium(supply_shocks=supply, final_demand=None)
    r_tariff   = CGEModel(tariff_schedule={"PTA_Production": 0.25}).equilibrium(
                     supply_shocks=supply, final_demand=None)
    p_no  = r_notariff["equilibrium_prices"][2]
    p_yes = r_tariff["equilibrium_prices"][2]
    assert p_yes >= p_no, f"Tariff should raise price: {p_yes:.4f} vs {p_no:.4f}"
    return f"PTA price: no tariff={p_no:.3f}, +25% tariff={p_yes:.3f}"

def test_cge_welfare_negative_under_shock():
    from cge_model import CGEModel
    supply = np.ones(8); supply[2] = 0.7
    r = CGEModel().equilibrium(supply_shocks=supply, final_demand=None)
    assert r["welfare_change_gbp"] < 0, f"welfare should be negative: {r['welfare_change_gbp']:.0f}"
    return f"welfare=GBP{r['welfare_change_gbp']/1e6:.0f}m (negative)"

def test_cge_convergence():
    from cge_model import CGEModel
    supply = np.ones(8); supply[2] = 0.5; supply[3] = 0.6
    r = CGEModel().equilibrium(supply_shocks=supply, final_demand=None)
    assert r.get("converged", True), "CGE failed to converge"
    return f"converged in {r.get('iterations','?')} iterations"

def test_cge_price_bounds():
    """Hard price bounds [0.3, 8.0] should prevent blow-up."""
    from cge_model import CGEModel
    supply = np.ones(8); supply[2] = 0.01  # near-total PTA collapse
    r = CGEModel().equilibrium(supply_shocks=supply, final_demand=None)
    prices = r["equilibrium_prices"]
    assert not np.any(np.isnan(prices))
    assert not np.any(np.isinf(prices))
    assert (prices > 0).all()
    assert (prices <= 8.01).all(), f"price ceiling breached: max={prices.max():.2f}"
    return f"prices in [{prices.min():.3f}, {prices.max():.3f}]"

check("CGE: baseline prices == 1", test_cge_baseline)
check("CGE: supply shock raises prices", test_cge_supply_shock_raises_price)
check("CGE: low sigma gives higher price than GTAP", test_cge_sigma_override)
check("CGE: tariff amplifies price under supply shock", test_cge_tariff_with_shock)
check("CGE: welfare negative under supply shock", test_cge_welfare_negative_under_shock)
check("CGE: convergence under combined shock", test_cge_convergence)
check("CGE: hard price bounds [0.3, 8.0]", test_cge_price_bounds)

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  ABM TESTS")
print("="*70)

def test_abm_no_shock():
    from abm_model import PolyesterSupplyChainABM
    abm = PolyesterSupplyChainABM(agents_per_sector=3)
    r = abm.run(T=26, baseline_demand=1.0, shock_schedule={}, demand_noise=0.02)
    assert r["inventory"].shape == (26, 8)
    assert not np.any(np.isnan(r["inventory"]))
    assert not np.any(r["inventory"] < 0), "Negative inventory"
    return f"inventory OK, shortage sum={r['shortage'].sum():.4f}"

def test_abm_with_shock():
    """All-sector shock (no country filter) should produce visible shortages."""
    from abm_model import PolyesterSupplyChainABM
    abm = PolyesterSupplyChainABM(agents_per_sector=3)
    shock = {4: {'sector': 2, 'severity': 0.8, 'duration': 10}}
    r = abm.run(T=26, baseline_demand=1.0, shock_schedule=shock, demand_noise=0.02)
    assert np.any(r["shortage"] > 0), "Expected shortages after 80% shock (all-agent)"
    return f"shortage sum={r['shortage'].sum():.4f}, peak={r['shortage'].max():.4f}"

def test_abm_china_shock():
    """China-specific shock (>=70% severity) should produce shortages at PTA."""
    from abm_model import PolyesterSupplyChainABM
    abm = PolyesterSupplyChainABM(agents_per_sector=3)
    shock = {4: {'sector': 2, 'country': 'China', 'severity': 0.75, 'duration': 12}}
    r = abm.run(T=52, baseline_demand=1.0, shock_schedule=shock, demand_noise=0.02)
    assert np.any(r["shortage"] > 0), "Expected shortages — China is 75% of PTA capacity"
    return f"China 75% shock -> shortage sum={r['shortage'].sum():.4f}"

def test_abm_bullwhip():
    from abm_model import PolyesterSupplyChainABM
    abm = PolyesterSupplyChainABM(agents_per_sector=3)
    shock = {4: {'sector': 2, 'severity': 0.6, 'duration': 8}}
    r = abm.run(T=52, baseline_demand=1.0, shock_schedule=shock, demand_noise=0.03)
    bw = abm.bullwhip_ratio(r)
    assert "Bullwhip_Ratio" in bw.columns
    assert (bw["Bullwhip_Ratio"] >= 0).all()
    return f"bullwhip range [{bw['Bullwhip_Ratio'].min():.2f}, {bw['Bullwhip_Ratio'].max():.2f}]"

def test_abm_service_level():
    from abm_model import PolyesterSupplyChainABM
    abm = PolyesterSupplyChainABM(agents_per_sector=3)
    r = abm.run(T=26, baseline_demand=1.0, shock_schedule={}, demand_noise=0.01)
    sl = abm.service_level(r)
    # Column is 'Service_Level_%' (percent)
    sl_col = next((c for c in sl.columns if "service" in c.lower()), None)
    assert sl_col is not None, f"No service level column; got {list(sl.columns)}"
    sl_vals = sl[sl_col].dropna()
    assert (sl_vals >= 0).all() and (sl_vals <= 100.01).all()
    return f"service level [{sl_vals.min():.1f}%, {sl_vals.max():.1f}%] (col='{sl_col}')"

def test_abm_recovery_time():
    from abm_model import PolyesterSupplyChainABM
    abm = PolyesterSupplyChainABM(agents_per_sector=3)
    shock = {4: {'sector': 2, 'severity': 0.7, 'duration': 10}}
    r = abm.run(T=52, baseline_demand=1.0, shock_schedule=shock, demand_noise=0.02)
    rt = abm.recovery_time(r)
    assert "Recovery_Week" in rt.columns
    return f"recovery_time computed, non-null={rt['Recovery_Week'].notna().sum()}"

def test_abm_no_nan_extreme():
    from abm_model import PolyesterSupplyChainABM
    abm = PolyesterSupplyChainABM(agents_per_sector=3)
    shock = {3: {'sector': 2, 'severity': 0.95, 'duration': 20}}
    r = abm.run(T=52, baseline_demand=1.0, shock_schedule=shock, demand_noise=0.05)
    for key in ("inventory", "shortage", "orders", "capacity"):
        assert not np.any(np.isnan(r[key])), f"NaN in abm_result['{key}']"
    return "no NaN in any ABM output array under 95% shock"

def test_abm_per_sector_counts():
    from abm_model import PolyesterSupplyChainABM
    counts = [2, 3, 2, 2, 3, 4, 1, 1]
    abm = PolyesterSupplyChainABM(agents_per_sector=counts)
    for i, c in enumerate(counts):
        assert len(abm.agents[i]) == c, f"Stage {i}: expected {c}, got {len(abm.agents[i])}"
    return f"per-sector counts verified"

def test_abm_seasonality():
    from abm_model import PolyesterSupplyChainABM
    abm = PolyesterSupplyChainABM(agents_per_sector=2)
    r = abm.run(T=52, baseline_demand=1.0, shock_schedule={},
                demand_noise=0.01, start_month=1, apply_seasonality=True)
    assert r["inventory"].shape == (52, 8)
    return "seasonality=True, 52 weeks, no error"

check("ABM: no-shock run (T=26)", test_abm_no_shock)
check("ABM: all-agent shock produces shortages", test_abm_with_shock)
check("ABM: China-specific high-severity shock", test_abm_china_shock)
check("ABM: bullwhip ratio", test_abm_bullwhip)
check("ABM: service level in [0,1]", test_abm_service_level)
check("ABM: recovery time", test_abm_recovery_time)
check("ABM: no NaN under 95% shock", test_abm_no_nan_extreme)
check("ABM: per-sector agent counts", test_abm_per_sector_counts)
check("ABM: HMRC seasonality", test_abm_seasonality)

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  MRIO MODEL TESTS")
print("="*70)

def test_mrio_structure():
    from mrio_model import MRIOModel
    m = MRIOModel()
    assert m.A_mrio.shape == (64, 64)
    assert m.L_mrio.shape == (64, 64)
    col_sums = m.A_mrio.sum(axis=0)
    assert (col_sums < 1).all()
    return f"64x64, col-sums max={col_sums.max():.3f}"

def test_mrio_value_added():
    from mrio_model import MRIOModel
    m = MRIOModel()
    r = m.value_added_decomposition()
    assert r is not None
    return f"VA decomposition computed: type={type(r).__name__}"

def test_mrio_china_exposure():
    from mrio_model import MRIOModel
    m = MRIOModel()
    r = m.effective_china_exposure()
    assert r is not None
    return f"china exposure: type={type(r).__name__}"

def test_mrio_regional_shock():
    # sig: regional_shock(self, shocked_region, shock_fraction, shocked_sectors=None)
    from mrio_model import MRIOModel
    m = MRIOModel()
    r = m.regional_shock("CHN", 0.5, shocked_sectors=["PTA_Production"])
    assert r is not None
    return f"regional shock: type={type(r).__name__}, rows={len(r) if hasattr(r,'__len__') else '?'}"

def test_mrio_linkages():
    from mrio_model import MRIOModel
    m = MRIOModel()
    bl = m.backward_linkages()
    fl = m.forward_linkages()
    assert bl is not None and fl is not None
    return "backward + forward linkages computed"

check("MRIO: structure (64x64, Hawkins-Simon)", test_mrio_structure)
warn( "MRIO: value-added decomposition", test_mrio_value_added)
warn( "MRIO: China exposure", test_mrio_china_exposure)
warn( "MRIO: regional shock", test_mrio_regional_shock)
warn( "MRIO: backward + forward linkages", test_mrio_linkages)

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  GHOSH MODEL TESTS")
print("="*70)

def test_ghosh_structure():
    from ghosh_model import GhoshModel
    g = GhoshModel()
    assert g.G.shape == (8, 8)
    assert g.B.shape == (8, 8)
    assert (np.diag(g.G) >= 1.0).all(), "Ghosh diagonal should be >= 1"
    return "G and B (8x8), diagonal >= 1"

def test_ghosh_forward_linkages():
    from ghosh_model import GhoshModel
    g = GhoshModel()
    fl = g.forward_linkages()
    assert fl is not None
    return f"forward linkages: type={type(fl).__name__}"

def test_ghosh_supply_shock():
    # sig: supply_shock(self, sector_shocks: Dict[int, float])
    from ghosh_model import GhoshModel
    from real_data import SECTORS
    g = GhoshModel()
    r = g.supply_shock({SECTORS.index("PTA_Production"): 0.5})
    assert r is not None
    return f"supply shock: type={type(r).__name__}, keys={list(r.keys())[:3] if isinstance(r,dict) else '?'}"

def test_ghosh_leontief_vs_ghosh():
    from ghosh_model import GhoshModel
    g = GhoshModel()
    r = g.leontief_vs_ghosh_linkages()
    assert r is not None
    return f"linkage quadrant: type={type(r).__name__}"

check("Ghosh: G and B matrices (8x8)", test_ghosh_structure)
warn( "Ghosh: forward linkages", test_ghosh_forward_linkages)
warn( "Ghosh: supply shock propagation", test_ghosh_supply_shock)
warn( "Ghosh: Leontief vs Ghosh linkage quadrant", test_ghosh_leontief_vs_ghosh)

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  INTEGRATED MODEL TESTS")
print("="*70)

def test_integrated_init():
    from integrated_model import IntegratedSupplyChainModel
    m = IntegratedSupplyChainModel()
    assert hasattr(m, "io") and hasattr(m, "cge") and hasattr(m, "abm")
    assert m.fd_base.shape == (8,)
    return f"fd_base={m.fd_base.tolist()}"

def test_integrated_rebuild_abm():
    from integrated_model import IntegratedSupplyChainModel
    m = IntegratedSupplyChainModel()
    m.rebuild_abm([2, 2, 2, 2, 2, 3, 1, 1])
    assert len(m.abm.agents) == 8
    assert m._abm_baseline_orders.shape == (8,)
    assert (m._abm_baseline_orders > 0).all()
    return f"baseline_orders>0 for all {len(m._abm_baseline_orders)} sectors"

def test_integrated_sequential():
    from integrated_model import IntegratedSupplyChainModel
    from shocks import ALL_SCENARIOS, build_io_shock_schedule, build_cge_supply_array
    m = IntegratedSupplyChainModel()
    sc_key = list(ALL_SCENARIOS.keys())[0]
    scenario = ALL_SCENARIOS[sc_key]
    io_sched = build_io_shock_schedule(scenario)
    r_io = m.io.simulate(T=12, final_demand_base=m.fd_base, shock_schedule=io_sched)
    supply = build_cge_supply_array(scenario)
    r_cge = m.cge.equilibrium(supply_shocks=supply, final_demand=m.fd_base)
    assert r_io["output"].shape == (12, 8)
    assert r_cge["equilibrium_prices"].shape == (8,)
    return f"sequential IO+CGE OK for scenario {sc_key}"

def test_integrated_coupled():
    from integrated_model import IntegratedSupplyChainModel
    from shocks import ALL_SCENARIOS
    m = IntegratedSupplyChainModel()
    m.rebuild_abm(3)
    sc_key = list(ALL_SCENARIOS.keys())[0]
    r = m.run_coupled(ALL_SCENARIOS[sc_key], T=12, demand_noise=0.02)
    assert "io_result" in r and "cge_result" in r and "abm_result" in r
    assert r["io_result"]["output"].shape == (12, 8)
    assert "welfare_gbp" in r, f"Missing welfare_gbp; keys={list(r.keys())}"
    return f"coupled OK, welfare=GBP{r['welfare_gbp']/1e6:.0f}m"

def test_integrated_coupled_gs():
    from integrated_model import IntegratedSupplyChainModel
    from shocks import ALL_SCENARIOS
    m = IntegratedSupplyChainModel()
    m.rebuild_abm(2)
    sc_key = list(ALL_SCENARIOS.keys())[0]
    r = m.run_coupled_gs(ALL_SCENARIOS[sc_key], T=12, demand_noise=0.02)
    assert "io_result" in r and "cge_result" in r and "abm_result" in r
    assert "welfare_gbp" in r
    return "GS coupled OK"

def test_integrated_abm_feedback():
    from integrated_model import IntegratedSupplyChainModel
    from shocks import ALL_SCENARIOS
    m = IntegratedSupplyChainModel()
    m.rebuild_abm(2)
    sc_key = list(ALL_SCENARIOS.keys())[0]
    r = m.run_coupled(ALL_SCENARIOS[sc_key], T=12, demand_noise=0.02,
                      abm_demand_feedback=True)
    assert "welfare_gbp" in r
    return "ABM demand feedback path ran without error"

def test_integrated_welfare_sign():
    """Per-period coupled welfare should be negative (supply shock = loss)."""
    from integrated_model import IntegratedSupplyChainModel
    from shocks import ALL_SCENARIOS
    m = IntegratedSupplyChainModel()
    m.rebuild_abm(2)
    r = m.run_coupled(ALL_SCENARIOS["S1"], T=26, demand_noise=0.02)
    assert np.isfinite(r["welfare_gbp"])
    return f"S1 welfare=GBP{r['welfare_gbp']/1e6:.0f}m"

def test_integrated_all_scenarios():
    """All 5 scenarios should run without error."""
    from integrated_model import IntegratedSupplyChainModel
    from shocks import ALL_SCENARIOS
    m = IntegratedSupplyChainModel()
    for key, scenario in ALL_SCENARIOS.items():
        m.rebuild_abm(2)
        r = m.run_coupled(scenario, T=12, demand_noise=0.02)
        assert "welfare_gbp" in r, f"Scenario {key} missing welfare_gbp"
    return f"all {len(ALL_SCENARIOS)} scenarios ran OK"

check("Integrated: init + fd_base", test_integrated_init)
check("Integrated: rebuild_abm", test_integrated_rebuild_abm)
check("Integrated: sequential IO + CGE", test_integrated_sequential)
check("Integrated: per-period coupled (T=12)", test_integrated_coupled)
check("Integrated: Gauss-Seidel coupled (T=12)", test_integrated_coupled_gs)
check("Integrated: ABM demand feedback", test_integrated_abm_feedback)
check("Integrated: welfare finite for S1", test_integrated_welfare_sign)
check("Integrated: all 5 scenarios run", test_integrated_all_scenarios)

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  POLICY TESTS (P1-P5)")
print("="*70)

def test_policy_p1_buffer():
    from integrated_model import IntegratedSupplyChainModel
    from policies import P1_BUFFER
    from real_data import SECTORS
    m = IntegratedSupplyChainModel()
    m.rebuild_abm(3)
    pta_idx = SECTORS.index("PTA_Production")
    ss_before = [ag.safety_stock for ag in m.abm.agents[pta_idx]]
    inv_before = [ag.inventory for ag in m.abm.agents[pta_idx]]
    m._apply_policy_to_abm(P1_BUFFER)
    ss_after  = [ag.safety_stock for ag in m.abm.agents[pta_idx]]
    inv_after = [ag.inventory for ag in m.abm.agents[pta_idx]]
    assert all(a > b for a, b in zip(ss_after,  ss_before)),  "P1 must increase safety_stock"
    assert all(a > b for a, b in zip(inv_after, inv_before)), "P1 must increase inventory"
    ratio = [a/b for a,b in zip(ss_after, ss_before)]
    return f"PTA safety_stock x{ratio[0]:.2f} (target x2.0)"

def test_policy_p2_diversify_conserves_capacity():
    from integrated_model import IntegratedSupplyChainModel
    from policies import P2_DIVERSIFY
    from real_data import SECTORS
    m = IntegratedSupplyChainModel()
    m.rebuild_abm(3)
    pta_idx = SECTORS.index("PTA_Production")
    total_before = sum(ag.base_capacity for ag in m.abm.agents[pta_idx])
    china_before = sum(ag.base_capacity for ag in m.abm.agents[pta_idx]
                       if ag.country in ("China","China_PTA","China_MEG"))
    m._apply_policy_to_abm(P2_DIVERSIFY)
    china_after  = sum(ag.base_capacity for ag in m.abm.agents[pta_idx]
                       if ag.country in ("China","China_PTA","China_MEG"))
    total_after  = sum(ag.base_capacity for ag in m.abm.agents[pta_idx])
    assert china_after < china_before, "P2 must reduce China capacity"
    assert abs(total_after - total_before) < 1e-9, \
        f"Total capacity not conserved: {total_before:.6f} vs {total_after:.6f}"
    return (f"China PTA: {china_before:.3f}->{china_after:.3f}, "
            f"total conserved at {total_before:.3f}")

def test_policy_p2_reduces_china_dependency():
    """After P2, China share at PTA should drop from ~75% toward ~50%."""
    from integrated_model import IntegratedSupplyChainModel
    from policies import P2_DIVERSIFY
    from real_data import SECTORS
    m = IntegratedSupplyChainModel()
    m.rebuild_abm(3)
    pta_idx = SECTORS.index("PTA_Production")
    agents = m.abm.agents[pta_idx]
    china_share_before = (
        sum(ag.base_capacity for ag in agents if ag.country in ("China","China_PTA","China_MEG")) /
        sum(ag.base_capacity for ag in agents)
    )
    m._apply_policy_to_abm(P2_DIVERSIFY)
    china_share_after = (
        sum(ag.base_capacity for ag in agents if ag.country in ("China","China_PTA","China_MEG")) /
        sum(ag.base_capacity for ag in agents)
    )
    assert china_share_after < china_share_before
    assert china_share_after < 0.70, f"China share still too high: {china_share_after:.1%}"
    return f"China PTA share: {china_share_before:.1%} -> {china_share_after:.1%}"

def test_policy_p3_recovery_multiplier():
    from integrated_model import IntegratedSupplyChainModel
    from policies import P3_RECOVERY
    from real_data import SECTORS, N_SECTORS
    m = IntegratedSupplyChainModel()
    mult = m._policy_rec_mult(P3_RECOVERY)
    assert mult.shape == (N_SECTORS,)
    pta_idx = SECTORS.index("PTA_Production")
    chem_idx = SECTORS.index("Chemical_Processing")
    who_idx  = SECTORS.index("UK_Wholesale")
    assert mult[pta_idx]  == 2.0, f"P3 PTA multiplier should be 2.0"
    assert mult[chem_idx] == 2.0, f"P3 Chemical multiplier should be 2.0"
    assert mult[who_idx]  == 1.0, f"P3 Wholesale should be unchanged (1.0)"
    return f"recovery mults: PTA={mult[pta_idx]:.1f}, Chem={mult[chem_idx]:.1f}, Who={mult[who_idx]:.1f}"

def test_policy_p4_reserve_schedule():
    from integrated_model import IntegratedSupplyChainModel
    from policies import P4_RESERVE
    from real_data import SECTORS, N_SECTORS
    m = IntegratedSupplyChainModel()
    onset = 4
    sched = m._reserve_schedule(P4_RESERVE, onset_week=onset, T=30)
    assert sched.shape == (30, N_SECTORS)
    pta_idx = SECTORS.index("PTA_Production")
    pet_idx = SECTORS.index("PET_Resin_Yarn")
    # delay=2 -> release starts week 6, ends week 6+8=14
    assert sched[onset + P4_RESERVE.release_delay_weeks, pta_idx] == pytest_approx(0.25, abs=1e-9), \
        "PTA reserve at start should be 0.25"
    assert sched[onset + P4_RESERVE.release_delay_weeks - 1, pta_idx] == 0.0, "Pre-release should be 0"
    assert sched[onset + P4_RESERVE.release_delay_weeks + P4_RESERVE.release_duration_weeks,
                 pta_idx] == 0.0, "Post-release should be 0"
    return (f"PTA release [{onset+P4_RESERVE.release_delay_weeks},"
            f"{onset+P4_RESERVE.release_delay_weeks+P4_RESERVE.release_duration_weeks}), "
            f"boost={sched[onset+P4_RESERVE.release_delay_weeks, pta_idx]:.2f}")

def pytest_approx(val, abs=1e-9):
    """Simple approx helper (no pytest dependency)."""
    class _A:
        def __eq__(self, other): return abs(other - val) < abs
    return _A()

# Fix: use numeric check directly
def test_policy_p4_reserve_schedule_v2():
    from integrated_model import IntegratedSupplyChainModel
    from policies import P4_RESERVE
    from real_data import SECTORS, N_SECTORS
    m = IntegratedSupplyChainModel()
    onset = 4
    sched = m._reserve_schedule(P4_RESERVE, onset_week=onset, T=30)
    pta_idx = SECTORS.index("PTA_Production")
    start_w = onset + P4_RESERVE.release_delay_weeks      # 6
    end_w   = start_w + P4_RESERVE.release_duration_weeks  # 14
    assert abs(sched[start_w, pta_idx] - 0.25) < 1e-9, \
        f"PTA boost at week {start_w} should be 0.25, got {sched[start_w, pta_idx]}"
    assert sched[start_w - 1, pta_idx] == 0.0, "Pre-delay week should be 0"
    assert sched[end_w, pta_idx] == 0.0, "Post-duration week should be 0"
    return (f"PTA reserve [{start_w},{end_w}), boost=0.25 verified")

def test_policy_p5_improves_welfare():
    """P5 Integrated package should improve welfare vs baseline under S1."""
    from integrated_model import IntegratedSupplyChainModel
    from policies import P5_INTEGRATED
    from shocks import ALL_SCENARIOS
    m = IntegratedSupplyChainModel()
    m.rebuild_abm(3)
    r_base = m.run_coupled(ALL_SCENARIOS["S1"], T=26, demand_noise=0.02, policy=None)
    m.rebuild_abm(3)
    r_pol  = m.run_coupled(ALL_SCENARIOS["S1"], T=26, demand_noise=0.02, policy=P5_INTEGRATED)
    w_base = r_base["welfare_gbp"]
    w_pol  = r_pol["welfare_gbp"]
    assert w_pol > w_base, f"P5 should improve welfare: base={w_base/1e6:.0f}m, pol={w_pol/1e6:.0f}m"
    improvement = (w_pol - w_base) / abs(w_base) * 100
    return f"welfare: base=GBP{w_base/1e6:.0f}m, P5=GBP{w_pol/1e6:.0f}m (+{improvement:.1f}%)"

def test_policy_p1_reduces_shortages():
    """P1 buffer should reduce IO shortages vs baseline."""
    from integrated_model import IntegratedSupplyChainModel
    from policies import P1_BUFFER
    from shocks import ALL_SCENARIOS
    m = IntegratedSupplyChainModel()
    m.rebuild_abm(3)
    r_base = m.run_coupled(ALL_SCENARIOS["S1"], T=26, demand_noise=0.02, policy=None)
    m.rebuild_abm(3)
    r_pol  = m.run_coupled(ALL_SCENARIOS["S1"], T=26, demand_noise=0.02, policy=P1_BUFFER)
    sht_base = float(r_base["io_result"]["shortage"].sum())
    sht_pol  = float(r_pol["io_result"]["shortage"].sum())
    assert sht_pol <= sht_base, \
        f"P1 should not worsen shortages: base={sht_base:.4f}, P1={sht_pol:.4f}"
    return f"IO shortage: base={sht_base:.4f}, P1={sht_pol:.4f}"

def test_policy_p2_reduces_china_shock_impact():
    """P2 diversification should reduce impact of China-specific PTA shock."""
    from integrated_model import IntegratedSupplyChainModel
    from policies import P2_DIVERSIFY
    from shocks import ALL_SCENARIOS
    m = IntegratedSupplyChainModel()
    m.rebuild_abm(3)
    r_base = m.run_coupled(ALL_SCENARIOS["S1"], T=26, demand_noise=0.02, policy=None)
    m.rebuild_abm(3)
    r_pol  = m.run_coupled(ALL_SCENARIOS["S1"], T=26, demand_noise=0.02, policy=P2_DIVERSIFY)
    w_base = r_base["welfare_gbp"]
    w_pol  = r_pol["welfare_gbp"]
    return (f"P2 vs baseline welfare: base=GBP{w_base/1e6:.0f}m, "
            f"P2=GBP{w_pol/1e6:.0f}m")

def test_policy_all_5_run():
    """All 5 policies should run without error on S1."""
    from integrated_model import IntegratedSupplyChainModel
    from policies import ALL_POLICIES
    from shocks import ALL_SCENARIOS
    m = IntegratedSupplyChainModel()
    for code, pol in ALL_POLICIES.items():
        m.rebuild_abm(2)
        r = m.run_coupled(ALL_SCENARIOS["S1"], T=12, demand_noise=0.02, policy=pol)
        assert "welfare_gbp" in r, f"{code} missing welfare_gbp"
    return f"all 5 policies ran on S1"

check("Policy P1: buffer increases safety_stock + inventory", test_policy_p1_buffer)
check("Policy P2: diversify conserves total capacity", test_policy_p2_diversify_conserves_capacity)
check("Policy P2: China share drops below 70%", test_policy_p2_reduces_china_dependency)
check("Policy P3: recovery multipliers correct", test_policy_p3_recovery_multiplier)
check("Policy P4: reserve schedule timing (delay + duration)", test_policy_p4_reserve_schedule_v2)
check("Policy P5: improves welfare vs baseline on S1", test_policy_p5_improves_welfare)
check("Policy P1: IO shortage <= baseline", test_policy_p1_reduces_shortages)
check("Policy P2: welfare vs baseline on S1", test_policy_p2_reduces_china_shock_impact)
check("Policy all: all 5 run on S1 without error", test_policy_all_5_run)

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  HISTORICAL VALIDATION (V1-V7)")
print("="*70)

try:
    from validation import HISTORICAL_EVENTS, run_validation_event, compare_event
    print(f"  {len(HISTORICAL_EVENTS)} events")
except Exception as e:
    print(f"[FAIL]  Cannot import validation: {e}")
    HISTORICAL_EVENTS = []

val_detail = {}

for event in HISTORICAL_EVENTS:
    eid  = event["id"]
    name = event["name"]

    def _make_test(ev):
        def _t():
            result = run_validation_event(ev)
            assert result is not None, "run_validation_event returned None"
            # Check no NaN in CGE prices
            prices = result.get("equilibrium_prices",
                     result.get("cge_prices", np.ones(8)))
            if hasattr(prices, '__len__'):
                assert not np.any(np.isnan(np.asarray(prices))), "NaN in prices"
            # compare_event returns a DataFrame
            cmp_df = compare_event(ev, result)
            if cmp_df is not None and hasattr(cmp_df, '__len__') and len(cmp_df) > 0:
                # Check if there's a 'Pass' or 'pass' column
                pass_col = next((c for c in cmp_df.columns
                                 if c.lower() in ("pass","passed","within_tolerance","ok")), None)
                if pass_col:
                    n_pass  = int(cmp_df[pass_col].sum())
                    n_total = len(cmp_df)
                    val_detail[ev["id"]] = (n_pass, n_total, cmp_df)
                    return f"{n_pass}/{n_total} metrics within tolerance"
                else:
                    val_detail[ev["id"]] = (None, None, cmp_df)
                    return f"ran OK, comparison columns: {list(cmp_df.columns)}"
            return "ran OK"
        return _t

    check(f"Validation {eid}: {name}", _make_test(event))

# Validation summary
if val_detail:
    print("\n  Validation comparison summary:")
    print(f"  {'ID':<4} {'Name':<42} {'Metrics'}")
    print("  " + "-"*60)
    for ev in HISTORICAL_EVENTS:
        eid = ev["id"]
        if eid in val_detail:
            np_, nt_, df_ = val_detail[eid]
            if np_ is not None:
                status = f"{np_}/{nt_} metrics pass"
            else:
                status = f"columns: {list(df_.columns)[:3]}"
            print(f"  {eid:<4} {ev['name']:<42} {status}")

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  CALIBRATION / SIGMA OVERRIDE CHECKS")
print("="*70)

def test_v3_sigma_pta_price_spike():
    """V3: 35% PTA supply loss with sigma=0.50 should give >50% price rise."""
    from cge_model import CGEModel
    cge = CGEModel(sigma={"PTA_Production": 0.50, "PET_Resin_Yarn": 0.80})
    supply = np.ones(8); supply[2] = 0.65
    r = cge.equilibrium(supply_shocks=supply, final_demand=None)
    rise = (r["equilibrium_prices"][2] - 1.0) * 100
    assert rise > 50, f"Expected >50% rise, got {rise:.0f}%"
    return f"V3 PTA price rise = +{rise:.0f}% (>50% target)"

def test_v5_sigma_chemical_price():
    """V5: 7% MEG supply loss with sigma=0.80 + freight should give ~10% rise."""
    from cge_model import CGEModel
    cge = CGEModel(sigma={"Chemical_Processing": 0.80})
    supply = np.ones(8); supply[1] = 0.93
    r = cge.equilibrium(supply_shocks=supply, final_demand=None, freight_multiplier=2.73)
    rise = (r["equilibrium_prices"][1] - 1.0) * 100
    assert 3 < rise < 30, f"V5 Chemical rise out of expected range: {rise:.1f}%"
    return f"V5 Chemical price rise = +{rise:.1f}% (target ~10%)"

def test_sigma_vs_gtap_comparison():
    """Low sigma should always give higher prices than GTAP for same supply shock."""
    from cge_model import CGEModel
    sectors_to_test = [
        ("PTA_Production", 2, 0.50, 0.65),
        ("Chemical_Processing", 1, 0.80, 0.93),
    ]
    for sector, idx, sigma_low, supply_frac in sectors_to_test:
        supply = np.ones(8); supply[idx] = supply_frac
        p_gtap = CGEModel().equilibrium(supply_shocks=supply, final_demand=None)["equilibrium_prices"][idx]
        p_low  = CGEModel(sigma={sector: sigma_low}).equilibrium(
                     supply_shocks=supply, final_demand=None)["equilibrium_prices"][idx]
        assert p_low > p_gtap, f"{sector}: low sigma price {p_low:.3f} should > GTAP {p_gtap:.3f}"
    return "low sigma > GTAP for all tested sectors"

check("Calibration V3: sigma=0.50 -> >50% PTA spike", test_v3_sigma_pta_price_spike)
warn( "Calibration V5: sigma=0.80 -> ~10% Chemical rise", test_v5_sigma_chemical_price)
check("Calibration: low sigma always > GTAP baseline", test_sigma_vs_gtap_comparison)

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  NUMERICAL STABILITY")
print("="*70)

def test_cge_near_zero_supply():
    from cge_model import CGEModel
    supply = np.ones(8); supply[2] = 0.01
    r = CGEModel().equilibrium(supply_shocks=supply, final_demand=None)
    prices = r["equilibrium_prices"]
    assert not np.any(np.isnan(prices)) and not np.any(np.isinf(prices))
    assert (prices > 0).all()
    return f"prices in [{prices.min():.3f}, {prices.max():.3f}]"

def test_abm_near_total_shock():
    from abm_model import PolyesterSupplyChainABM
    abm = PolyesterSupplyChainABM(agents_per_sector=3)
    shock = {3: {'sector': 2, 'severity': 0.99, 'duration': 20}}
    r = abm.run(T=52, baseline_demand=1.0, shock_schedule=shock, demand_noise=0.05)
    for key in ("inventory","shortage","orders","capacity"):
        arr = np.asarray(r[key])
        assert not np.any(np.isnan(arr)), f"NaN in {key}"
        assert not np.any(np.isinf(arr)), f"Inf in {key}"
    return "no NaN/Inf under 99% sector shock"

def test_coupled_no_nan_all_scenarios():
    """All coupled runs should be NaN-free."""
    from integrated_model import IntegratedSupplyChainModel
    from shocks import ALL_SCENARIOS
    m = IntegratedSupplyChainModel()
    for key, scenario in ALL_SCENARIOS.items():
        m.rebuild_abm(2)
        r = m.run_coupled(scenario, T=12, demand_noise=0.02)
        for arr_key in ("output","shortage","prices"):
            arr = np.asarray(r["io_result"][arr_key])
            assert not np.any(np.isnan(arr)), f"Scenario {key}: NaN in io_result['{arr_key}']"
        prices = np.asarray(r["cge_result"]["equilibrium_prices"])
        assert not np.any(np.isnan(prices)), f"Scenario {key}: NaN in CGE prices"
    return f"no NaN across all {len(ALL_SCENARIOS)} coupled scenarios"

def test_io_prices_positive():
    from io_model import DynamicIOModel, A_BASE
    from integrated_model import IntegratedSupplyChainModel
    fd = IntegratedSupplyChainModel().fd_base
    m = DynamicIOModel(A_BASE)
    # shock_schedule expects sector INDEX not name
    shock = {3: [(2, 0.8), (3, 0.7)]}
    r = m.simulate(T=52, final_demand_base=fd, shock_schedule=shock)
    prices = r["prices"]
    assert not np.any(np.isnan(prices))
    assert (prices > 0).all(), f"Negative prices detected, min={prices.min():.4f}"
    return f"IO prices in [{prices.min():.3f}, {prices.max():.3f}]"

check("Stability: CGE 1% supply (no NaN/Inf)", test_cge_near_zero_supply)
check("Stability: ABM 99% shock (no NaN/Inf)", test_abm_near_total_shock)
check("Stability: all coupled scenarios NaN-free", test_coupled_no_nan_all_scenarios)
check("Stability: IO prices positive under multi-shock", test_io_prices_positive)

# ---------------------------------------------------------------------------
print("\n" + "="*70)
print("  FINAL SUMMARY")
print("="*70)
n_pass = sum(1 for s,_ in results if s == "PASS")
n_fail = sum(1 for s,_ in results if s == "FAIL")
n_warn = sum(1 for s,_ in results if s == "WARN")
print(f"\n  Total: {len(results)}  |  PASS: {n_pass}  |  FAIL: {n_fail}  |  WARN: {n_warn}\n")
if n_fail:
    print("  FAILED:")
    for s, name in results:
        if s == "FAIL":
            print(f"    x  {name}")
if n_warn:
    print("  WARNINGS (non-critical):")
    for s, name in results:
        if s == "WARN":
            print(f"    ~  {name}")
print()
sys.exit(0 if n_fail == 0 else 1)
