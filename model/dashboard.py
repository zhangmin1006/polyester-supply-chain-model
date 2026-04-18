"""
dashboard.py
Interactive Streamlit dashboard for the Polyester Textile Supply Chain Model.

Launch:
    cd model
    streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent / "data"

SECTORS = [
    "Oil_Extraction", "Chemical_Processing", "PTA_Production", "PET_Resin_Yarn",
    "Fabric_Weaving", "Garment_Assembly", "UK_Wholesale", "UK_Retail",
]
SECTOR_SHORT = {
    "Oil_Extraction": "Oil", "Chemical_Processing": "Chemicals",
    "PTA_Production": "PTA", "PET_Resin_Yarn": "PET/Yarn",
    "Fabric_Weaving": "Fabric", "Garment_Assembly": "Garment",
    "UK_Wholesale": "Wholesale", "UK_Retail": "Retail",
}
COUNTRY_COLORS = {
    "China": "#e63946", "Bangladesh": "#2a9d8f", "Turkey": "#e9c46a",
    "India": "#f4a261", "Vietnam": "#264653", "Italy": "#457b9d",
    "Cambodia": "#6d6875", "Sri_Lanka": "#a8dadc", "Other": "#adb5bd",
}
SCENARIO_INFO = {
    "S1": ("PTA Production Shock",      "50% PTA output lost — Eastern China earthquake/policy disruption"),
    "S2": ("MEG Supply Disruption",     "Saudi MEG disruption — Red Sea / Strait of Hormuz"),
    "S3": ("UK–China Trade Restriction","35% tariff on Chinese synthetic apparel imports"),
    "S4": ("Zhangjiagang Port Closure", "418 kt MEG port closed — typhoon or COVID lockdown"),
    "S5": ("Multi-Node Pandemic Shock", "COVID-style simultaneous multi-stage disruption"),
}
HMRC_SEASONAL = [0.993, 0.909, 1.026, 0.941, 0.963, 0.963,
                 1.052, 1.062, 1.099, 1.145, 0.977, 0.871]
MONTH_NAMES   = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Polyester Supply Chain",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
div[data-testid="metric-container"] { background:#1e2a3a; border-radius:8px;
    padding:12px; border-left:4px solid #457b9d; }
</style>
""", unsafe_allow_html=True)

# ── Cached data loaders ───────────────────────────────────────────────────────

@st.cache_data
def load_annual():
    return pd.read_csv(DATA_DIR / "hmrc_annual_country.csv")

@st.cache_data
def load_monthly():
    return pd.read_csv(DATA_DIR / "hmrc_monthly_country.csv")

@st.cache_data
def load_eu_noneu():
    return pd.read_csv(DATA_DIR / "hmrc_monthly_eu_noneu.csv")

@st.cache_resource
def get_model():
    from integrated_model import IntegratedSupplyChainModel
    return IntegratedSupplyChainModel()

@st.cache_data
def get_baseline(_model):
    return _model.baseline_report()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧵 Polyester Supply Chain")
    st.caption("UK Import Risk | HMRC OTS 2002-2024\nIO × CGE × ABM Model")
    st.divider()

    page = st.radio(
        "Navigate",
        options=[
            "📈 Market Overview",
            "🏭 Supply Chain Structure",
            "⚡ Scenario Simulator",
            "🔍 HMRC Explorer",
            "✅ Model Validation",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    with st.expander("ℹ️ About this model"):
        st.markdown("""
**Components**
- Dynamic Input-Output (Leontief)
- CGE price equilibrium
- ABM Beer-Game dynamics
- MRIO (8 regions × 8 sectors)
- Ghosh supply-push

**Data**
- HMRC OTS API — 2002-2024
- ONS IO Tables — 2023
- GTAP v10 trade elasticities
        """)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — MARKET OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════════
if page == "📈 Market Overview":
    st.title("UK Synthetic Apparel Imports — Market Overview")
    st.caption("HMRC OTS API · 29 HS6 codes · synthetic fibre chapters 61+62 · 2002-2024")

    annual   = load_annual()
    eu_noneu = load_eu_noneu()

    latest = int(annual["Year"].max())
    prev   = latest - 1
    tot_latest = annual[annual["Year"] == latest]["Value"].sum()
    tot_prev   = annual[annual["Year"] == prev]["Value"].sum()
    yoy        = (tot_latest - tot_prev) / tot_prev * 100

    china_sh = (
        annual[(annual["Year"] == latest) & (annual["Country"] == "China")]["Value"].sum()
        / tot_latest * 100
    )
    bv_sh = (
        annual[(annual["Year"] == latest) & (annual["Country"].isin(["Bangladesh", "Vietnam"]))]["Value"].sum()
        / tot_latest * 100
    )
    noneu_latest = eu_noneu[(eu_noneu["Year"] == latest) & (eu_noneu["Flow"] == "NON-EU")]["Value"].sum()
    noneu_prev   = eu_noneu[(eu_noneu["Year"] == prev)   & (eu_noneu["Flow"] == "NON-EU")]["Value"].sum()
    noneu_yoy    = (noneu_latest - noneu_prev) / noneu_prev * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Total Imports {latest}", f"£{tot_latest/1e9:.2f}bn", f"{yoy:+.1f}% YoY")
    c2.metric(f"China Direct Share", f"{china_sh:.1f}%", "Effective ~60% upstream")
    c3.metric("Bangladesh + Vietnam", f"{bv_sh:.1f}%", "Indirect China fabric exposure")
    c4.metric(f"NON-EU {latest}", f"£{noneu_latest/1e9:.2f}bn", f"{noneu_yoy:+.1f}% YoY")

    st.divider()

    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.subheader("Annual Import Trends by Country")
        top_c = annual.groupby("Country")["Value"].sum().nlargest(7).index.tolist()
        fig = go.Figure()
        for yr, label in [(2008,"GFC"),(2016,"Brexit"),(2020,"COVID"),(2022,"Ukraine"),(2024,"Red Sea")]:
            fig.add_vline(x=yr, line_dash="dot", line_color="#475569", line_width=1,
                         annotation_text=label, annotation_font_size=9,
                         annotation_font_color="#94a3b8")
        for country in top_c:
            d = annual[annual["Country"] == country].sort_values("Year")
            fig.add_trace(go.Scatter(
                x=d["Year"], y=d["Value"] / 1e6,
                name=country.replace("_", " "),
                mode="lines+markers",
                line=dict(color=COUNTRY_COLORS.get(country, "#adb5bd"), width=2),
                marker=dict(size=4),
            ))
        fig.update_layout(height=360, template="plotly_dark",
                         yaxis_title="£ million", xaxis_title="Year",
                         legend=dict(orientation="h", y=-0.22),
                         hovermode="x unified", margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader(f"Import Share {latest}")
        yd = annual[annual["Year"] == latest].copy()
        top7 = yd.nlargest(7, "Value")
        other_v = yd[~yd["Country"].isin(top7["Country"])]["Value"].sum()
        pie_df = pd.concat(
            [top7[["Country","Value"]],
             pd.DataFrame([{"Country":"Other","Value":other_v}])],
            ignore_index=True,
        )
        fig2 = go.Figure(go.Pie(
            labels=pie_df["Country"].str.replace("_"," "),
            values=pie_df["Value"],
            hole=0.45,
            marker=dict(colors=[COUNTRY_COLORS.get(c,"#adb5bd") for c in pie_df["Country"]]),
            textinfo="label+percent", textfont_size=11,
        ))
        fig2.update_layout(height=360, template="plotly_dark", showlegend=False,
                          margin=dict(l=0,r=0,t=20,b=0),
                          annotations=[dict(text=f"<b>{latest}</b>", x=0.5, y=0.5,
                                            showarrow=False, font=dict(size=16,color="white"))])
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Monthly Seasonal Demand Pattern  (HMRC NON-EU average 2002-2024)")
    cs1, cs2 = st.columns([2, 3])

    with cs1:
        bar_colors = ["#e63946" if v == max(HMRC_SEASONAL) else
                      "#2a9d8f" if v == min(HMRC_SEASONAL) else "#457b9d"
                      for v in HMRC_SEASONAL]
        fig_s = go.Figure(go.Bar(
            x=MONTH_NAMES, y=HMRC_SEASONAL, marker_color=bar_colors,
            text=[f"{v:.3f}" for v in HMRC_SEASONAL], textposition="outside",
            textfont=dict(size=9),
        ))
        fig_s.add_hline(y=1.0, line_dash="dash", line_color="#94a3b8", line_width=1)
        fig_s.update_layout(height=280, template="plotly_dark",
                           yaxis_title="Seasonal factor", yaxis_range=[0.8, 1.25],
                           margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig_s, use_container_width=True)

    with cs2:
        eu_nn = load_eu_noneu()
        recent = eu_nn[eu_nn["Flow"] == "NON-EU"].sort_values(["Year","Month"])
        all_years = sorted(recent["Year"].unique().tolist())
        default_yrs = all_years[-3:]
        yrs_sel = st.multiselect("Compare years (monthly NON-EU)",
                                  options=all_years, default=default_yrs, key="seasonal_yrs")
        fig_m = go.Figure()
        for yr in yrs_sel:
            d = recent[recent["Year"] == yr]
            fig_m.add_trace(go.Scatter(
                x=[MONTH_NAMES[m-1] for m in d["Month"]],
                y=d["Value"] / 1e6, name=str(yr), mode="lines+markers",
            ))
        fig_m.update_layout(height=280, template="plotly_dark",
                           yaxis_title="£ million (NON-EU)",
                           legend=dict(orientation="h", y=-0.28),
                           margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig_m, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — SUPPLY CHAIN STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🏭 Supply Chain Structure":
    st.title("Supply Chain Structure & Vulnerability Analysis")

    with st.spinner("Initialising model (first load may take ~10 s)..."):
        model    = get_model()
        baseline = get_baseline(model)

    # ── KPI strip ────────────────────────────────────────────────────────────
    hhi_df  = baseline["hhi"]
    scvi_df = baseline["scvi"]

    high_hhi = int((hhi_df["HHI"] > 0.25).sum()) if isinstance(hhi_df, pd.DataFrame) else "—"
    eff_ch   = baseline.get("eff_china")
    max_dep  = f'{eff_ch["Effective_China_%"].max():.1f}%' if isinstance(eff_ch, pd.DataFrame) else "—"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Highly concentrated stages", str(high_hhi), "HHI > 0.25")
    k2.metric("Max China dependency", max_dep, "upstream-traced")
    k3.metric("HMRC nominal China share", "27.3%", "direct import only")
    k4.metric("Effective upstream exposure", "~60%", "Bangladesh/Vietnam fabric sourcing")

    st.divider()

    # ── Two column charts ────────────────────────────────────────────────────
    ca, cb = st.columns(2)

    with ca:
        st.subheader("Effective China Dependency by Stage")
        if isinstance(eff_ch, pd.DataFrame):
            sorted_ch = eff_ch.sort_values("Effective_China_%", ascending=True)
            fig_ch = px.bar(
                sorted_ch,
                x="Effective_China_%", y="Sector", orientation="h",
                color="Effective_China_%", color_continuous_scale="Reds",
                text="Effective_China_%",
                labels={"Effective_China_%": "China Dependency %"},
                template="plotly_dark", height=340,
            )
            fig_ch.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_ch.add_vline(x=27.3, line_dash="dot", line_color="#94a3b8",
                            annotation_text="HMRC nominal 27.3%",
                            annotation_font_color="#94a3b8", annotation_font_size=9)
            fig_ch.update_layout(coloraxis_showscale=False, margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig_ch, use_container_width=True)

    with cb:
        st.subheader("Supplier Concentration (HHI)")
        if isinstance(hhi_df, pd.DataFrame):
            h_sorted = hhi_df.sort_values("HHI", ascending=True)
            bar_c = ["#e63946" if h > 0.25 else "#e9c46a" if h > 0.15 else "#2a9d8f"
                     for h in h_sorted["HHI"]]
            fig_hhi = go.Figure(go.Bar(
                x=h_sorted["HHI"], y=h_sorted["Sector"],
                orientation="h", marker_color=bar_c,
                text=[f"{h:.3f}" for h in h_sorted["HHI"]],
                textposition="outside",
            ))
            fig_hhi.add_vline(x=0.25, line_dash="dash", line_color="#e63946", line_width=1,
                             annotation_text="High (>0.25)",
                             annotation_font_color="#e63946", annotation_font_size=9)
            fig_hhi.add_vline(x=0.15, line_dash="dash", line_color="#e9c46a", line_width=1,
                             annotation_text="Moderate (>0.15)",
                             annotation_font_color="#e9c46a", annotation_font_size=9)
            fig_hhi.update_layout(height=340, template="plotly_dark",
                                 margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig_hhi, use_container_width=True)

    # ── Sankey diagram ────────────────────────────────────────────────────────
    st.subheader("Supply Chain Flow  (Sankey)")
    node_labels = [
        # 0-7: supply chain stages
        "Oil Extraction","Chemical Processing","PTA Production","PET / Yarn",
        "Fabric Weaving","Garment Assembly","UK Wholesale","UK Retail",
        # 8-13: geographic sources
        "China","Bangladesh","Vietnam","Turkey","India","EU",
    ]
    node_colors = [
        "#264653","#2a9d8f","#1d6a9d","#1d3557",
        "#2a9d8f","#1d6a9d","#e9c46a","#2a9d8f",
        "#e63946","#2a9d8f","#264653","#e9c46a","#f4a261","#457b9d",
    ]
    # source → target, approximate value weights
    src = [0,1,2,3,4,5,6,  8, 8, 9,10,11,12,13]
    tgt = [1,2,3,4,5,6,7,  5, 4, 5, 5, 5, 5, 6]
    val = [100,90,85,80,75,70,65, 27,15,12,10, 9, 8,24]

    fig_sk = go.Figure(go.Sankey(
        node=dict(label=node_labels, color=node_colors, pad=14, thickness=20),
        link=dict(source=src, target=tgt, value=val,
                  color=["rgba(180,180,180,0.25)"] * len(src)),
    ))
    fig_sk.update_layout(height=380, template="plotly_dark",
                        font=dict(color="white", size=11),
                        margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig_sk, use_container_width=True)

    # ── Resilience scorecard ──────────────────────────────────────────────────
    st.subheader("Resilience Scorecard")
    scorecard = baseline.get("scorecard")
    if isinstance(scorecard, pd.DataFrame):
        num_cols = [c for c in scorecard.columns if scorecard[c].dtype in [float, np.float64]]
        st.dataframe(
            scorecard.style.background_gradient(cmap="RdYlGn", subset=num_cols),
            use_container_width=True, height=300,
        )
    else:
        st.write(scorecard)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — SCENARIO SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Scenario Simulator":
    st.title("Supply Chain Shock Simulator")

    from shocks import ALL_SCENARIOS, build_cge_supply_array, build_io_shock_schedule

    # ── Sidebar controls ──────────────────────────────────────────────────────
    with st.sidebar:
        st.divider()
        st.subheader("Simulation Parameters")

        sc_key = st.selectbox(
            "Scenario",
            list(SCENARIO_INFO.keys()),
            format_func=lambda k: f"{k}: {SCENARIO_INFO[k][0]}",
        )
        T_weeks    = st.slider("Simulation weeks", 12, 78, 52, step=4)
        st_month   = st.slider("Start month (1=Jan)", 1, 12, 1)
        seasonality = st.checkbox("Apply HMRC seasonality", value=True)
        run_btn    = st.button("▶  Run Simulation", type="primary", use_container_width=True)

    sc_name, sc_desc = SCENARIO_INFO[sc_key]
    st.info(f"**{sc_key}: {sc_name}**  \n{sc_desc}")

    res_key = f"sim_{sc_key}_{T_weeks}_{st_month}_{seasonality}"

    if run_btn:
        with st.spinner(f"Running {sc_key} ({T_weeks} weeks)…"):
            from abm_model import PolyesterSupplyChainABM
            from cge_model import CGEModel

            model    = get_model()
            scenario = ALL_SCENARIOS[sc_key]

            io_sched  = build_io_shock_schedule(scenario)
            io_result = model.io.simulate(
                T=T_weeks, final_demand_base=model.fd_base, shock_schedule=io_sched
            )

            cge_m = CGEModel(tariff_schedule=scenario.tariffs) if scenario.tariffs else model.cge
            supply_arr = build_cge_supply_array(scenario)
            cge_result = cge_m.equilibrium(supply_shocks=supply_arr, final_demand=model.fd_base)

            max_p_sig = float(cge_result["equilibrium_prices"].max())
            abm = PolyesterSupplyChainABM(agents_per_sector=3)
            abm_result = abm.run(
                T=T_weeks, baseline_demand=1.0,
                shock_schedule=scenario.abm_schedule,
                demand_noise=0.03 * max_p_sig,
                start_month=st_month,
                apply_seasonality=seasonality,
            )
            bw = abm.bullwhip_ratio(abm_result)
            sl = abm.service_level(abm_result)
            rt = abm.recovery_time(abm_result)

            st.session_state[res_key] = {
                "io": io_result, "cge": cge_result, "abm": abm_result,
                "bw": bw, "sl": sl, "rt": rt, "T": T_weeks, "scenario": scenario,
            }

    res = st.session_state.get(res_key)

    if res is None:
        st.info("Select a scenario and click **▶ Run Simulation** to begin.")
        st.subheader("Scenario Quick Reference")
        rows = [{"ID": k, "Name": n, "Description": d,
                 "Onset (wk)": ALL_SCENARIOS[k].onset_week,
                 "Duration (wk)": ALL_SCENARIOS[k].duration_weeks}
                for k, (n, d) in SCENARIO_INFO.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.stop()

    io_r, cge_r, abm_r = res["io"], res["cge"], res["abm"]
    bw,   sl,    rt    = res["bw"],  res["sl"],  res["rt"]
    T_sim              = res["T"]
    scenario_obj       = res["scenario"]
    weeks = list(range(T_sim))

    # ── KPI strip ─────────────────────────────────────────────────────────────
    welfare   = cge_r["welfare_change_gbp"]
    max_dp    = cge_r["price_index_change_pct"].max()
    max_dp_s  = SECTORS[int(cge_r["price_index_change_pct"].argmax())]
    io_short  = float(io_r["shortage"].sum())
    avg_rec   = rt["Recovery_Week"].dropna()
    avg_rec_v = f"{avg_rec.mean():.1f} wks" if len(avg_rec) else "No recovery"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Welfare Change", f"£{welfare/1e9:.3f}bn", delta_color="inverse")
    m2.metric("Max Price Rise",  f"{max_dp:.1f}%", f"at {SECTOR_SHORT.get(max_dp_s, max_dp_s)}")
    m3.metric("IO Total Shortage", f"{io_short:.3f}")
    m4.metric("Mean Recovery", avg_rec_v)

    st.divider()

    tab_io, tab_cge, tab_abm, tab_metrics = st.tabs(
        ["📊 I-O Output", "💰 CGE Prices", "🤖 ABM Dynamics", "📋 Metrics Tables"]
    )

    # ── I-O Output ────────────────────────────────────────────────────────────
    with tab_io:
        output = io_r.get("output")
        if output is not None and output.ndim == 2:
            fig_io = go.Figure()
            for i, s in enumerate(SECTORS):
                fig_io.add_trace(go.Scatter(
                    x=weeks, y=output[:, i],
                    name=SECTOR_SHORT.get(s, s), mode="lines",
                ))
            fig_io.add_vline(x=scenario_obj.onset_week, line_dash="dash",
                            line_color="#e63946",
                            annotation_text="Shock onset",
                            annotation_font_color="#e63946")
            fig_io.update_layout(height=400, template="plotly_dark",
                                yaxis_title="Output (normalised)", xaxis_title="Week",
                                legend=dict(orientation="h", y=-0.2),
                                hovermode="x unified")
            st.plotly_chart(fig_io, use_container_width=True)

        short = io_r.get("shortage")
        if short is not None and short.ndim == 2:
            st.subheader("Shortage by Sector over Time")
            fig_sh = go.Figure()
            for i, s in enumerate(SECTORS):
                if short[:, i].max() > 1e-6:
                    fig_sh.add_trace(go.Scatter(
                        x=weeks, y=short[:, i],
                        name=SECTOR_SHORT.get(s, s), mode="lines", fill="tozeroy",
                    ))
            fig_sh.update_layout(height=300, template="plotly_dark",
                                yaxis_title="Shortage (normalised)", xaxis_title="Week",
                                hovermode="x unified")
            st.plotly_chart(fig_sh, use_container_width=True)

    # ── CGE Prices ────────────────────────────────────────────────────────────
    with tab_cge:
        pct   = cge_r["price_index_change_pct"]
        prices = cge_r["equilibrium_prices"]

        cp1, cp2 = st.columns(2)
        with cp1:
            fig_p = go.Figure(go.Bar(
                x=[SECTOR_SHORT.get(s, s) for s in SECTORS],
                y=pct,
                marker_color=["#e63946" if v > 5 else "#e9c46a" if v > 0 else "#2a9d8f"
                              for v in pct],
                text=[f"{v:.1f}%" for v in pct], textposition="outside",
            ))
            fig_p.update_layout(title="Price Change by Sector (%)",
                               height=360, template="plotly_dark",
                               yaxis_title="% vs baseline",
                               margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig_p, use_container_width=True)

        with cp2:
            df_price = pd.DataFrame({
                "Sector": [SECTOR_SHORT.get(s, s) for s in SECTORS],
                "Eq. Price": prices.round(4),
                "Change %":  pct.round(2),
            })
            st.dataframe(
                df_price.style.background_gradient(cmap="RdYlGn_r", subset=["Change %"]),
                use_container_width=True, height=360,
            )
            conv = "✅ Converged" if cge_r.get("converged", True) else "⚠️ Not converged"
            st.caption(f"{conv} · {cge_r.get('iterations','?')} iterations")

    # ── ABM Dynamics ─────────────────────────────────────────────────────────
    with tab_abm:
        inv = abm_r["inventory"]   # (T, N_SECTORS)
        ord_ = abm_r["orders"]

        fig_inv = go.Figure()
        fig_ord = go.Figure()
        for i, s in enumerate(SECTORS):
            lbl = SECTOR_SHORT.get(s, s)
            fig_inv.add_trace(go.Scatter(x=weeks, y=inv[:, i],  name=lbl, mode="lines"))
            fig_ord.add_trace(go.Scatter(x=weeks, y=ord_[:, i], name=lbl, mode="lines"))

        for fig_ in [fig_inv, fig_ord]:
            fig_.add_vline(x=scenario_obj.onset_week, line_dash="dash",
                          line_color="#e63946",
                          annotation_text="Shock",
                          annotation_font_color="#e63946")
            fig_.update_layout(height=320, template="plotly_dark",
                               legend=dict(orientation="h", y=-0.25),
                               hovermode="x unified")

        fig_inv.update_layout(yaxis_title="Inventory level", xaxis_title="Week",
                             title="Inventory Dynamics by Stage")
        fig_ord.update_layout(yaxis_title="Order quantity", xaxis_title="Week",
                             title="Order Dynamics (Bullwhip effect)")

        st.plotly_chart(fig_inv, use_container_width=True)
        st.plotly_chart(fig_ord, use_container_width=True)

    # ── Metrics tables ────────────────────────────────────────────────────────
    with tab_metrics:
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.subheader("Bullwhip Ratio")
            st.dataframe(bw.style.background_gradient(cmap="Reds", subset=["Bullwhip_Ratio"]),
                        use_container_width=True)
        with mc2:
            st.subheader("Service Level")
            st.dataframe(sl.style.background_gradient(cmap="RdYlGn", subset=["Service_Level_%"]),
                        use_container_width=True)
        with mc3:
            st.subheader("Recovery Time")
            st.dataframe(rt, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 4 — HMRC EXPLORER
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 HMRC Explorer":
    st.title("HMRC OTS Data Explorer")
    st.caption("UK synthetic apparel imports · 29 HS6 codes · 2002-2024 · all countries")

    annual  = load_annual()
    monthly = load_monthly()
    eu_nn   = load_eu_noneu()

    # ── Filters ───────────────────────────────────────────────────────────────
    f1, f2, f3 = st.columns(3)
    with f1:
        yr_rng = st.slider("Year range", 2002, 2024, (2010, 2024))
    with f2:
        all_cntrs = sorted(annual["Country"].unique().tolist())
        sel_c = st.multiselect("Countries", all_cntrs,
                               default=["China","Bangladesh","Turkey","Vietnam","India"])
    with f3:
        chart_t = st.selectbox("Chart type", ["Line","Bar","Stacked Area"])

    st.divider()

    ann_f = annual[(annual["Year"] >= yr_rng[0]) & (annual["Year"] <= yr_rng[1])]
    plot_d = ann_f[ann_f["Country"].isin(sel_c)] if sel_c else ann_f

    # ── Main chart ────────────────────────────────────────────────────────────
    col_m, col_s = st.columns([3, 1])
    with col_m:
        if chart_t == "Line":
            fig = px.line(plot_d.sort_values("Year"), x="Year", y="Value",
                         color="Country", template="plotly_dark", height=400)
            fig.update_traces(mode="lines+markers")
        elif chart_t == "Bar":
            fig = px.bar(plot_d.sort_values("Year"), x="Year", y="Value",
                        color="Country", barmode="group",
                        template="plotly_dark", height=400)
        else:
            fig = px.area(plot_d.sort_values(["Year","Country"]),
                         x="Year", y="Value", color="Country",
                         template="plotly_dark", height=400)
        fig.update_layout(yaxis_title="Import Value (£)", hovermode="x unified",
                         legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)

    with col_s:
        st.subheader("Summary (£m)")
        summ = (plot_d.groupby("Country")["Value"]
                .agg(Total="sum", Avg="mean", Peak="max")
                .div(1e6).round(1)
                .sort_values("Total", ascending=False))
        st.dataframe(summ, use_container_width=True,
                    column_config={
                        "Total": st.column_config.NumberColumn("Total £m", format="%.1f"),
                        "Avg":   st.column_config.NumberColumn("Avg £m/yr", format="%.1f"),
                        "Peak":  st.column_config.NumberColumn("Peak £m", format="%.1f"),
                    })

    # ── Unit price trend ──────────────────────────────────────────────────────
    if sel_c:
        st.subheader("Unit Price Trend (£/kg)")
        up_d = ann_f[(ann_f["Country"].isin(sel_c)) & ann_f["UnitPrice_GBP_per_kg"].notna()]
        fig_up = px.line(up_d.sort_values("Year"), x="Year",
                        y="UnitPrice_GBP_per_kg", color="Country",
                        labels={"UnitPrice_GBP_per_kg": "£/kg"},
                        template="plotly_dark", height=300)
        fig_up.update_layout(yaxis_title="£ per kg", hovermode="x unified",
                            legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig_up, use_container_width=True)

    # ── EU vs NON-EU monthly ──────────────────────────────────────────────────
    st.subheader("EU vs NON-EU Monthly Imports")
    eu_f = eu_nn[(eu_nn["Year"] >= yr_rng[0]) & (eu_nn["Year"] <= yr_rng[1])].copy()
    eu_f["Date"] = pd.to_datetime(eu_f[["Year","Month"]].assign(day=1))
    fig_eu = px.area(eu_f.sort_values(["Date","Flow"]), x="Date", y="Value",
                    color="Flow", template="plotly_dark", height=300,
                    color_discrete_map={"EU":"#457b9d","NON-EU":"#e63946"},
                    labels={"Value":"£ imports"})
    fig_eu.update_layout(yaxis_title="£ monthly", hovermode="x unified")
    st.plotly_chart(fig_eu, use_container_width=True)

    # ── Download ──────────────────────────────────────────────────────────────
    st.subheader("Export Data")
    dl_choice = st.radio("Dataset", ["Filtered selection","Full annual","Full monthly"],
                        horizontal=True)
    dl_df = plot_d if dl_choice == "Filtered selection" else (
            annual if dl_choice == "Full annual" else monthly)
    st.download_button("⬇ Download CSV",
                       data=dl_df.to_csv(index=False),
                       file_name=f"hmrc_{yr_rng[0]}_{yr_rng[1]}.csv",
                       mime="text/csv")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE 5 — MODEL VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "✅ Model Validation":
    st.title("Model Validation Against HMRC Benchmarks")
    st.caption("All benchmarks derived from HMRC OTS API download — 2026-04-17")

    from real_data import HMRC_VALIDATION_BENCHMARKS as VB

    benchmarks = [
        {"Event":"V1 COVID-19 (2020)","Metric":"China import value",
         "HMRC":f"{VB['V1_COVID_china_value_pct']:+.1f}%","Category":"Volume shock",
         "Note":"Factory shutdowns Q1 2020"},
        {"Event":"V1 COVID-19 (2020)","Metric":"Total UK synthetic apparel",
         "HMRC":f"{VB['V1_COVID_total_value_pct']:+.1f}%","Category":"Volume shock",
         "Note":"2019→2020"},
        {"Event":"V5 Red Sea (Jan 2024)","Metric":"NON-EU imports Jan",
         "HMRC":f"{VB['V5_RedSea_jan_value_pct']:+.1f}%","Category":"Shipping disruption",
         "Note":"vs Jan 2023"},
        {"Event":"V5 Red Sea (Feb 2024)","Metric":"NON-EU imports Feb",
         "HMRC":f"{VB['V5_RedSea_feb_value_pct']:+.1f}%","Category":"Shipping disruption",
         "Note":"vs Feb 2023"},
        {"Event":"V5 Red Sea (Mar 2024)","Metric":"NON-EU imports Mar",
         "HMRC":f"{VB['V5_RedSea_mar_value_pct']:+.1f}%","Category":"Shipping disruption",
         "Note":"vs Mar 2023"},
        {"Event":"V5 Red Sea (H1 2024)","Metric":"NON-EU imports H1",
         "HMRC":f"{VB['V5_RedSea_H1_value_pct']:+.1f}%","Category":"Shipping disruption",
         "Note":"H1 2024 vs H1 2023"},
        {"Event":"V6 Shanghai lockdown (2022)","Metric":"China value Q2",
         "HMRC":f"{VB['V6_Shanghai_Q2_china_value_pct']:+.1f}%","Category":"Price/energy shock",
         "Note":"Price-driven; energy crisis dominated"},
        {"Event":"V7 Ukraine energy (2022)","Metric":"Annual import value",
         "HMRC":f"{VB['V7_Ukraine_annual_value_pct']:+.1f}%","Category":"Price shock",
         "Note":"2022 vs 2021"},
    ]

    df_val = pd.DataFrame(benchmarks)
    st.dataframe(df_val, use_container_width=True, hide_index=True,
                column_config={
                    "Event":    st.column_config.TextColumn(width="medium"),
                    "Metric":   st.column_config.TextColumn(width="large"),
                    "HMRC":     st.column_config.TextColumn(width="small"),
                    "Category": st.column_config.TextColumn(width="medium"),
                    "Note":     st.column_config.TextColumn(width="large"),
                }, height=330)

    st.divider()

    # YoY bar chart
    annual = load_annual()
    totals = annual.groupby("Year")["Value"].sum().reset_index()
    totals["YoY_%"] = totals["Value"].pct_change() * 100

    fig_yoy = go.Figure(go.Bar(
        x=totals["Year"],
        y=totals["YoY_%"].fillna(0),
        marker_color=["#e63946" if v < 0 else "#2a9d8f" for v in totals["YoY_%"].fillna(0)],
        text=[f"{v:.1f}%" for v in totals["YoY_%"].fillna(0)],
        textposition="outside", textfont=dict(size=8),
    ))
    for yr, label in [(2008,"GFC"),(2016,"Brexit"),(2020,"COVID"),(2022,"Ukraine"),(2024,"Red Sea")]:
        fig_yoy.add_vline(x=yr, line_dash="dot", line_color="#475569",
                         annotation_text=label, annotation_font_size=9,
                         annotation_font_color="#94a3b8", annotation_position="top")
    fig_yoy.update_layout(
        title="Year-on-Year Change — UK Synthetic Apparel Imports (%)",
        height=380, template="plotly_dark",
        yaxis_title="% YoY change", margin=dict(l=0,r=0,t=50,b=0),
    )
    st.plotly_chart(fig_yoy, use_container_width=True)

    # Data quality pie
    st.subheader("Parameter Data Quality (208 total parameters)")
    dq = {"Category":["REAL","DERIVED","ESTIMATED","EXTERNAL","ASSUMED"],
          "Count":[77,42,61,13,15]}
    dq_df = pd.DataFrame(dq)
    dq_df["Share %"] = (dq_df["Count"] / dq_df["Count"].sum() * 100).round(1)

    dq1, dq2 = st.columns([1, 2])
    with dq1:
        st.dataframe(dq_df, use_container_width=True, hide_index=True)
    with dq2:
        fig_dq = go.Figure(go.Pie(
            labels=dq_df["Category"], values=dq_df["Count"], hole=0.4,
            marker_color=["#2a9d8f","#457b9d","#e9c46a","#264653","#e63946"],
            textinfo="label+percent",
        ))
        fig_dq.update_layout(height=280, template="plotly_dark",
                            showlegend=False, margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig_dq, use_container_width=True)
