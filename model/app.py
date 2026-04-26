"""
app.py
Full integrated UI for the UK Textile Supply Chain Analysis.

Integrates all analysis and visualisation functions:
  IO × CGE × ABM × MRIO × Ghosh | HMRC 2002-2024 | 5 shock scenarios

Launch:
    cd model
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent / "data"
FIG_DIR  = Path(__file__).parent / "results" / "figures"

SECTORS = [
    "Oil_Extraction","Chemical_Processing","PTA_Production","PET_Resin_Yarn",
    "Fabric_Weaving","Garment_Assembly","UK_Wholesale","UK_Retail",
]
SECTOR_SHORT = {
    "Oil_Extraction":"Oil","Chemical_Processing":"Chemicals","PTA_Production":"PTA",
    "PET_Resin_Yarn":"PET/Yarn","Fabric_Weaving":"Fabric","Garment_Assembly":"Garment",
    "UK_Wholesale":"Wholesale","UK_Retail":"Retail",
}
COUNTRY_COLORS = {
    "China":"#e63946","Bangladesh":"#2a9d8f","Turkey":"#e9c46a",
    "India":"#f4a261","Vietnam":"#264653","Italy":"#457b9d",
    "Cambodia":"#6d6875","Sri_Lanka":"#a8dadc","Other":"#adb5bd",
}
SCENARIO_INFO = {
    "S1":("PTA Production Shock",      "50% PTA output lost — Eastern China earthquake/policy"),
    "S2":("MEG Supply Disruption",     "Saudi MEG disruption — Red Sea / Strait of Hormuz"),
    "S3":("UK–China Trade Restriction","35% tariff on Chinese synthetic apparel imports"),
    "S4":("Zhangjiagang Port Closure", "418 kt MEG port closed — typhoon or COVID lockdown"),
    "S5":("Multi-Node Pandemic Shock", "COVID-style simultaneous multi-stage disruption"),
}
HMRC_SEASONAL = [0.993,0.909,1.026,0.941,0.963,0.963,1.052,1.062,1.099,1.145,0.977,0.871]
MONTHS        = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
DARK          = "plotly_dark"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="UK Textile Supply Chain Analysis",
    page_icon="🧵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
div[data-testid="metric-container"]{background:#1e2a3a;border-radius:8px;
  padding:12px 16px;border-left:4px solid #457b9d;}
.stTabs [data-baseweb="tab"]{font-size:0.85rem;}
</style>
""", unsafe_allow_html=True)

# ── Cached loaders ────────────────────────────────────────────────────────────
@st.cache_data
def _annual():  return pd.read_csv(DATA_DIR/"hmrc_annual_country.csv")
@st.cache_data
def _monthly(): return pd.read_csv(DATA_DIR/"hmrc_monthly_country.csv")
@st.cache_data
def _eu_nn():   return pd.read_csv(DATA_DIR/"hmrc_monthly_eu_noneu.csv")

@st.cache_resource
def _model():
    from integrated_model import IntegratedSupplyChainModel
    return IntegratedSupplyChainModel()

@st.cache_resource
def _mrio():
    from mrio_model import MRIOModel
    return MRIOModel()

@st.cache_resource
def _ghosh():
    from ghosh_model import GhoshModel
    return GhoshModel()

@st.cache_data
def _baseline(_m):
    return _m.baseline_report()

# ── Sidebar navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧵 UK Textile Supply Chain Analysis")
    st.divider()

    page = st.radio("", [
        "🏠 Home",
        "📈 HMRC Market Data",
        "🗺️ Supply Chain Map",
        "📊 Baseline Analysis",
        "⚡ Scenario Simulator",
        "📋 All Scenarios",
        "🏛️ Policy Analysis",
        "✅ Validation",
        "🖼️ Figure Gallery",
    ], label_visibility="collapsed")

    st.divider()
    with st.expander("ℹ️ Model components"):
        st.markdown("""
**Shock simulation**
- Dynamic Leontief I-O (8 sectors)
- CGE Armington price equilibrium
- ABM Beer-Game supply chain agents

**Structural analysis**
- MRIO (8 regions × 8 sectors)
- Ghosh forward propagation

**Policy interventions**
- P1 Strategic Buffer Stockpile
- P2 Import Diversification
- P3 Emergency Recovery Investment
- P4 Critical Reserve Release
- P5 Integrated Resilience Package

**Data sources**
- HMRC OTS API 2002–2024
- ONS IO Tables 2023
- GTAP v10 Armington elasticities
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# HOME
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Home":
    st.title("UK Textile Supply Chain Analysis")
    st.markdown("*UK synthetic apparel imports · 8-stage supply chain · 5 shock scenarios · HMRC 2002-2024*")
    st.divider()

    annual = _annual()
    latest = int(annual["Year"].max())
    tot    = annual[annual["Year"]==latest]["Value"].sum()
    china  = annual[(annual["Year"]==latest)&(annual["Country"]=="China")]["Value"].sum()

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Total UK Imports", f"£{tot/1e9:.2f}bn", f"{latest}")
    c2.metric("China Direct Share", f"{china/tot*100:.1f}%", "HMRC nominal")
    c3.metric("Effective China Exposure", "~60%", "upstream-traced")
    c4.metric("PTA Concentration (HHI)", "0.482", "Critical — China 67%")
    c5.metric("Model Parameters", "208", "37% real HMRC/ONS data")

    st.divider()

    # Quick overview charts
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("UK Imports 2002–2024 (total)")
        totals = annual.groupby("Year")["Value"].sum().reset_index()
        totals["YoY_%"] = totals["Value"].pct_change()*100
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=totals["Year"], y=totals["Value"]/1e9,
                                 fill="tozeroy", fillcolor="rgba(69,123,157,0.2)",
                                 line=dict(color="#457b9d",width=2), name="Total £bn"))
        for yr,label in [(2020,"COVID"),(2022,"Ukraine"),(2024,"Red Sea")]:
            fig.add_vline(x=yr, line_dash="dot", line_color="#475569",
                         annotation_text=label, annotation_font_size=9,
                         annotation_font_color="#94a3b8")
        fig.update_layout(height=300, template=DARK, showlegend=False,
                         yaxis_title="£bn", margin=dict(l=0,r=0,t=10,b=0),
                         hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Scenario Economic Impact")
        sc_names  = ["S1 PTA\nShock", "S2 MEG\nDisrupt.", "S3 Trade\nRestrict.",
                     "S4 Port\nClosure", "S5 Pandemic"]
        sc_welfare = [-3.58, -0.40, -1.04, -0.95, -6.34]
        sc_colors  = ["#e63946","#f4a261","#8e44ad","#457b9d","#c0392b"]
        fig2 = go.Figure(go.Bar(
            x=sc_names, y=sc_welfare,
            marker_color=sc_colors,
            text=[f"£{v:.2f}bn" for v in sc_welfare],
            textposition="outside",
        ))
        fig2.update_layout(height=300, template=DARK,
                          yaxis_title="CGE Welfare Change (£bn)",
                          margin=dict(l=0,r=0,t=10,b=40),
                          yaxis=dict(range=[min(sc_welfare)*1.15, 0.3]))
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Quick Navigation")
    nav_items = [
        ("📈 HMRC Market Data",   "HMRC import trends 2002–2024"),
        ("📊 Baseline Analysis",  "HHI, China exposure, MRIO & Ghosh"),
        ("⚡ Scenario Simulator", "Run S1–S5 with full IO×CGE×ABM"),
        ("🏛️ Policy Analysis",   "Compare P1–P5 interventions"),
        ("✅ Validation",         "Model validation vs HMRC benchmarks"),
        ("📋 All Scenarios",      "Cross-scenario comparison table"),
    ]
    row1, row2 = nav_items[:3], nav_items[3:]
    cols1 = st.columns(3)
    for col, (nav, desc) in zip(cols1, row1):
        col.info(f"**{nav}**\n\n{desc}")
    cols2 = st.columns(3)
    for col, (nav, desc) in zip(cols2, row2):
        col.info(f"**{nav}**\n\n{desc}")


# ═══════════════════════════════════════════════════════════════════════════════
# HMRC MARKET DATA
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📈 HMRC Market Data":
    st.title("HMRC OTS — UK Synthetic Apparel Imports")
    st.caption("29 HS6 codes · synthetic fibre chapters 61+62 · 2002-2024 · all countries")

    annual  = _annual()
    monthly = _monthly()
    eu_nn   = _eu_nn()

    latest = int(annual["Year"].max())
    prev   = latest - 1
    tot_l  = annual[annual["Year"]==latest]["Value"].sum()
    tot_p  = annual[annual["Year"]==prev]["Value"].sum()

    c1,c2,c3,c4 = st.columns(4)
    c1.metric(f"Total {latest}", f"£{tot_l/1e9:.2f}bn", f"{(tot_l-tot_p)/tot_p*100:+.1f}% YoY")
    c2.metric("China share", f"{annual[(annual['Year']==latest)&(annual['Country']=='China')]['Value'].sum()/tot_l*100:.1f}%")
    noneu_l = eu_nn[(eu_nn["Year"]==latest)&(eu_nn["Flow"]=="NON-EU")]["Value"].sum()
    noneu_p = eu_nn[(eu_nn["Year"]==prev)  &(eu_nn["Flow"]=="NON-EU")]["Value"].sum()
    c3.metric("NON-EU imports", f"£{noneu_l/1e9:.2f}bn", f"{(noneu_l-noneu_p)/noneu_p*100:+.1f}% YoY")
    c4.metric("Years of data", "23", "2002–2024")

    tab1,tab2,tab3,tab4 = st.tabs(["📊 Trends","🌍 Country Breakdown","📆 Seasonal","🔍 Explorer"])

    # ── Trends ────────────────────────────────────────────────────────────────
    with tab1:
        top7 = annual.groupby("Country")["Value"].sum().nlargest(7).index.tolist()
        fig = go.Figure()
        for yr,lbl in [(2008,"GFC"),(2016,"Brexit"),(2020,"COVID"),(2022,"Ukraine"),(2024,"Red Sea")]:
            fig.add_vline(x=yr, line_dash="dot", line_color="#475569", line_width=1,
                         annotation_text=lbl, annotation_font_size=9,
                         annotation_font_color="#94a3b8")
        for c in top7:
            d = annual[annual["Country"]==c].sort_values("Year")
            fig.add_trace(go.Scatter(x=d["Year"], y=d["Value"]/1e6,
                                     name=c.replace("_"," "),
                                     line=dict(color=COUNTRY_COLORS.get(c,"#adb5bd"),width=2),
                                     mode="lines+markers", marker=dict(size=4)))
        fig.update_layout(height=400, template=DARK, yaxis_title="£ million",
                         legend=dict(orientation="h",y=-0.2), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # YoY bar
        totals = annual.groupby("Year")["Value"].sum().reset_index()
        totals["YoY_%"] = totals["Value"].pct_change()*100
        fig_yoy = go.Figure(go.Bar(
            x=totals["Year"], y=totals["YoY_%"].fillna(0),
            marker_color=["#e63946" if v<0 else "#2a9d8f" for v in totals["YoY_%"].fillna(0)],
            text=[f"{v:.1f}%" for v in totals["YoY_%"].fillna(0)],
            textposition="outside", textfont=dict(size=8),
        ))
        fig_yoy.update_layout(height=280, template=DARK, yaxis_title="YoY %",
                             margin=dict(l=0,r=0,t=10,b=0))
        st.plotly_chart(fig_yoy, use_container_width=True)

    # ── Country breakdown ────────────────────────────────────────────────────
    with tab2:
        yr_sel = st.slider("Year", 2002, 2024, latest, key="cb_yr")
        yd = annual[annual["Year"]==yr_sel].sort_values("Value", ascending=False)
        tot_yr = yd["Value"].sum()
        top8   = yd.head(8)
        other  = tot_yr - top8["Value"].sum()
        pie_df = pd.concat([top8[["Country","Value"]],
                            pd.DataFrame([{"Country":"Other","Value":other}])],
                           ignore_index=True)

        col_p, col_s = st.columns([2,3])
        with col_p:
            fig_pie = go.Figure(go.Pie(
                labels=pie_df["Country"].str.replace("_"," "),
                values=pie_df["Value"], hole=0.42,
                marker=dict(colors=[COUNTRY_COLORS.get(c,"#adb5bd") for c in pie_df["Country"]]),
                textinfo="label+percent", textfont_size=11,
            ))
            fig_pie.update_layout(height=380, template=DARK, showlegend=False,
                                 annotations=[dict(text=f"<b>{yr_sel}</b>",x=0.5,y=0.5,
                                                   showarrow=False,font=dict(size=18,color="white"))])
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_s:
            # Stacked area over time
            top5 = annual.groupby("Country")["Value"].sum().nlargest(5).index.tolist()
            area_data = annual[annual["Country"].isin(top5)].sort_values(["Year","Country"])
            fig_area = px.area(area_data, x="Year", y="Value", color="Country",
                              template=DARK, height=380,
                              labels={"Value":"£ imports"},
                              color_discrete_map={c:COUNTRY_COLORS.get(c,"#adb5bd") for c in top5})
            fig_area.update_layout(legend=dict(orientation="h",y=-0.2), hovermode="x unified")
            st.plotly_chart(fig_area, use_container_width=True)

        # Unit price trends
        st.subheader("Unit Price Trend (£/kg)")
        sel_up = st.multiselect("Countries", annual["Country"].unique().tolist(),
                                default=["China","Bangladesh","Turkey","India"], key="up_c")
        up_data = annual[annual["Country"].isin(sel_up) & annual["UnitPrice_GBP_per_kg"].notna()]
        fig_up = px.line(up_data.sort_values("Year"), x="Year", y="UnitPrice_GBP_per_kg",
                        color="Country", template=DARK, height=300,
                        labels={"UnitPrice_GBP_per_kg":"£/kg"})
        fig_up.update_layout(hovermode="x unified", legend=dict(orientation="h",y=-0.25))
        st.plotly_chart(fig_up, use_container_width=True)

    # ── Seasonal ─────────────────────────────────────────────────────────────
    with tab3:
        cs1,cs2 = st.columns(2)
        with cs1:
            st.subheader("Monthly Seasonal Factors (avg 2002-2024)")
            bar_c = ["#e63946" if v==max(HMRC_SEASONAL) else
                     "#2a9d8f" if v==min(HMRC_SEASONAL) else "#457b9d"
                     for v in HMRC_SEASONAL]
            fig_s = go.Figure(go.Bar(x=MONTHS, y=HMRC_SEASONAL, marker_color=bar_c,
                                    text=[f"{v:.3f}" for v in HMRC_SEASONAL],
                                    textposition="outside"))
            fig_s.add_hline(y=1.0, line_dash="dash", line_color="#94a3b8")
            fig_s.update_layout(height=320, template=DARK, yaxis_range=[0.8,1.25],
                               yaxis_title="Seasonal factor")
            st.plotly_chart(fig_s, use_container_width=True)

        with cs2:
            st.subheader("Monthly NON-EU by Year")
            rec = eu_nn[eu_nn["Flow"]=="NON-EU"].sort_values(["Year","Month"])
            yr_opts = sorted(rec["Year"].unique().tolist())
            sel_yrs = st.multiselect("Years", yr_opts, default=yr_opts[-3:], key="seas_yrs")
            fig_m = go.Figure()
            for yr in sel_yrs:
                d = rec[rec["Year"]==yr]
                fig_m.add_trace(go.Scatter(x=[MONTHS[m-1] for m in d["Month"]],
                                           y=d["Value"]/1e6, name=str(yr), mode="lines+markers"))
            fig_m.update_layout(height=320, template=DARK, yaxis_title="£ million (NON-EU)",
                               legend=dict(orientation="h",y=-0.28))
            st.plotly_chart(fig_m, use_container_width=True)

    # ── Explorer ─────────────────────────────────────────────────────────────
    with tab4:
        f1,f2,f3 = st.columns(3)
        yr_rng  = f1.slider("Year range", 2002, 2024, (2010,2024), key="ex_yr")
        sel_c   = f2.multiselect("Countries", sorted(annual["Country"].unique()),
                                 default=["China","Bangladesh","Turkey","Vietnam"], key="ex_c")
        chart_t = f3.selectbox("Chart type", ["Line","Bar","Stacked Area"], key="ex_ct")

        filt = annual[(annual["Year"]>=yr_rng[0])&(annual["Year"]<=yr_rng[1])]
        plot_d = filt[filt["Country"].isin(sel_c)] if sel_c else filt

        if chart_t=="Line":
            fig_ex = px.line(plot_d.sort_values("Year"), x="Year", y="Value",
                            color="Country", template=DARK, height=380)
            fig_ex.update_traces(mode="lines+markers")
        elif chart_t=="Bar":
            fig_ex = px.bar(plot_d.sort_values("Year"), x="Year", y="Value",
                           color="Country", barmode="group", template=DARK, height=380)
        else:
            fig_ex = px.area(plot_d.sort_values(["Year","Country"]), x="Year", y="Value",
                            color="Country", template=DARK, height=380)
        fig_ex.update_layout(yaxis_title="£ imports", hovermode="x unified",
                            legend=dict(orientation="h",y=-0.2))
        st.plotly_chart(fig_ex, use_container_width=True)

        # EU vs NON-EU
        eu_f = eu_nn[(eu_nn["Year"]>=yr_rng[0])&(eu_nn["Year"]<=yr_rng[1])].copy()
        eu_f["Date"] = pd.to_datetime(eu_f[["Year","Month"]].assign(day=1))
        fig_eu = px.area(eu_f.sort_values(["Date","Flow"]), x="Date", y="Value",
                        color="Flow", template=DARK, height=280,
                        color_discrete_map={"EU":"#457b9d","NON-EU":"#e63946"})
        fig_eu.update_layout(yaxis_title="£ monthly", hovermode="x unified")
        st.plotly_chart(fig_eu, use_container_width=True)

        st.download_button("⬇ Download CSV", data=plot_d.to_csv(index=False),
                          file_name=f"hmrc_{yr_rng[0]}_{yr_rng[1]}.csv", mime="text/csv")


# ═══════════════════════════════════════════════════════════════════════════════
# SUPPLY CHAIN MAP
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🗺️ Supply Chain Map":
    st.title("Supply Chain Map & Structure")

    tab_geo, tab_sankey, tab_network = st.tabs(["🗺️ Geographic Flow","🔗 Sankey Diagram","🕸️ IO Network"])

    with tab_geo:
        geo_png = FIG_DIR / "fig00_supply_chain_geography.png"
        net_png = FIG_DIR / "fig01_supply_chain_network.png"
        if geo_png.exists():
            st.image(str(geo_png), caption="Geographic supply chain flow — crude oil → UK retail",
                    use_container_width=True)
        else:
            st.warning("Geographic diagram not generated yet. Go to **🖼️ Figure Gallery** and click Generate.")

        if net_png.exists():
            st.image(str(net_png), caption="I-O network — China dependency by stage",
                    use_container_width=True)

    with tab_sankey:
        st.subheader("Supply Chain Flow (interactive Sankey)")
        node_labels = [
            "Oil Extraction","Chemical Processing","PTA Production","PET / Yarn",
            "Fabric Weaving","Garment Assembly","UK Wholesale","UK Retail",
            "China","Bangladesh","Vietnam","Turkey","India","EU",
        ]
        node_colors = [
            "#264653","#2a9d8f","#1d6a9d","#1d3557",
            "#2a9d8f","#1d6a9d","#e9c46a","#2a9d8f",
            "#e63946","#2a9d8f","#264653","#e9c46a","#f4a261","#457b9d",
        ]
        src = [0,1,2,3,4,5,6,  8, 8, 9,10,11,12,13]
        tgt = [1,2,3,4,5,6,7,  5, 4, 5, 5, 5, 5, 6]
        val = [100,90,85,80,75,70,65, 27,15,12,10,9,8,24]
        fig_sk = go.Figure(go.Sankey(
            node=dict(label=node_labels, color=node_colors, pad=14, thickness=20),
            link=dict(source=src, target=tgt, value=val,
                     color=["rgba(180,180,180,0.25)"]*len(src)),
        ))
        fig_sk.update_layout(height=450, template=DARK, font=dict(color="white",size=12),
                            margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig_sk, use_container_width=True)

        with st.expander("Stage descriptions"):
            for i, s in enumerate(SECTORS):
                st.markdown(f"**§{i} {SECTOR_SHORT[s]}** — {s.replace('_',' ')}")

    with tab_network:
        conc_png = FIG_DIR / "fig02_concentration_vulnerability.png"
        net_png2 = FIG_DIR / "fig01_supply_chain_network.png"
        if conc_png.exists():
            st.image(str(conc_png), caption="Sector concentration & vulnerability", use_container_width=True)
        if net_png2.exists():
            st.image(str(net_png2), caption="I-O network — China dependency by stage", use_container_width=True)
        if not conc_png.exists():
            st.info("Go to **🖼️ Figure Gallery** to generate all figures.")


# ═══════════════════════════════════════════════════════════════════════════════
# BASELINE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Baseline Analysis":
    st.title("Baseline Supply Chain Analysis")
    st.caption("HHI concentration · China dependency · I-O multipliers · MRIO value-added · Ghosh supply-push")

    with st.spinner("Loading model (~10 s first load)…"):
        model    = _model()
        baseline = _baseline(model)

    tab_hhi, tab_china, tab_mult, tab_mrio, tab_ghosh = st.tabs([
        "📊 HHI Concentration", "🇨🇳 China Dependency", "⚙️ IO Multipliers",
        "🌍 MRIO Analysis", "🔄 Ghosh Supply-Push",
    ])

    with tab_hhi:
        hhi = baseline["hhi"]
        scvi = baseline["scvi"]
        ca,cb = st.columns(2)
        with ca:
            h = hhi.sort_values("HHI", ascending=True)
            fig = go.Figure(go.Bar(
                x=h["HHI"], y=h["Sector"], orientation="h",
                marker_color=["#e63946" if v>0.25 else "#e9c46a" if v>0.15 else "#2a9d8f"
                              for v in h["HHI"]],
                text=[f"{v:.3f}" for v in h["HHI"]], textposition="outside",
            ))
            fig.add_vline(x=0.25, line_dash="dash", line_color="#e63946",
                         annotation_text="High (>0.25)", annotation_font_color="#e63946",
                         annotation_font_size=9)
            fig.add_vline(x=0.15, line_dash="dash", line_color="#e9c46a",
                         annotation_text="Moderate", annotation_font_color="#e9c46a",
                         annotation_font_size=9)
            fig.update_layout(height=340, template=DARK, title="HHI by Sector",
                             margin=dict(l=0,r=0,t=40,b=0))
            st.plotly_chart(fig, use_container_width=True)
        with cb:
            if isinstance(scvi, pd.DataFrame):
                fig2 = px.bar(scvi.sort_values("SCVI", ascending=False),
                             x="Sector", y="SCVI", color="Risk_Level",
                             color_discrete_map={"Critical":"#e63946","High":"#f4a261",
                                                 "Medium":"#e9c46a","Low":"#2a9d8f"},
                             template=DARK, height=340, title="SCVI by Sector")
                st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(hhi, use_container_width=True, hide_index=True)

    with tab_china:
        eff = baseline["eff_china"]
        if isinstance(eff, pd.DataFrame):
            ec = eff.sort_values("Effective_China_%", ascending=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(x=ec["Nominal_China_%"], y=ec["Sector"],
                                orientation="h", name="Nominal (HMRC)",
                                marker_color="#457b9d", opacity=0.7))
            fig.add_trace(go.Bar(x=ec["Effective_China_%"], y=ec["Sector"],
                                orientation="h", name="Effective (upstream-traced)",
                                marker_color="#e63946", opacity=0.85))
            fig.add_vline(x=27.3, line_dash="dot", line_color="#94a3b8",
                         annotation_text="HMRC direct 27.3%",
                         annotation_font_color="#94a3b8", annotation_font_size=9)
            fig.update_layout(barmode="overlay", height=380, template=DARK,
                             xaxis_title="China dependency %",
                             legend=dict(orientation="h",y=-0.15),
                             title="Nominal vs Effective China Dependency")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(eff, use_container_width=True, hide_index=True)

    with tab_mult:
        mult = baseline["multipliers"]
        if isinstance(mult, pd.DataFrame):
            fig = px.bar(mult.sort_values("Output_Multiplier", ascending=True),
                        x="Output_Multiplier", y="Sector", orientation="h",
                        template=DARK, height=320, text="Output_Multiplier",
                        title="I-O Output Multipliers (£1 final demand → total output)")
            fig.update_traces(texttemplate="%{text:.3f}", textposition="outside",
                             marker_color="#457b9d")
            fig.add_vline(x=1.0, line_dash="dash", line_color="#94a3b8")
            st.plotly_chart(fig, use_container_width=True)

        calibration = baseline.get("calibration")
        if isinstance(calibration, pd.DataFrame):
            st.subheader("Calibration Report")
            st.dataframe(calibration, use_container_width=True, hide_index=True)

    with tab_mrio:
        st.subheader("Multi-Regional Input-Output Analysis")
        st.caption("8 regions × 8 sectors = 64-node system | Calibrated from GTAP v10 + HMRC OTS")
        with st.spinner("Building MRIO model…"):
            mrio = _mrio()
            from mrio_model import REGIONS, REGION_LABELS

        mrio_va, mrio_exp, mrio_link, mrio_shock = st.tabs(
            ["💰 Value-Added", "🇨🇳 China Exposure", "🔗 Linkages", "⚡ Regional Shock"])

        with mrio_va:
            detail, summary = mrio.value_added_decomposition()
            ca,cb = st.columns([2,3])
            with ca:
                st.subheader("VA by Region (UK demand origin)")
                fig_va = go.Figure(go.Pie(
                    labels=summary["Region_Label"], values=summary["VA_GBP_bn"],
                    hole=0.4, textinfo="label+percent",
                    marker_colors=["#e63946","#2a9d8f","#457b9d","#f4a261",
                                   "#264653","#7b1fa2","#1b5e20","#adb5bd"],
                ))
                fig_va.update_layout(height=380, template=DARK, showlegend=False)
                st.plotly_chart(fig_va, use_container_width=True)
            with cb:
                st.subheader("Value-Added Heatmap (Region × Sector)")
                pivot = detail.pivot_table(values="Value_Added_GBP", index="Region_Label",
                                           columns="Sector", aggfunc="sum", fill_value=0)
                fig_hm = px.imshow(pivot/1e9, template=DARK, height=380,
                                   color_continuous_scale="Blues",
                                   labels={"color":"VA £bn"}, text_auto=".2f")
                fig_hm.update_xaxes(tickangle=-45)
                st.plotly_chart(fig_hm, use_container_width=True)
            st.subheader("Region Summary")
            st.dataframe(summary[["Region_Label","VA_GBP_bn","VA_Share_%"]],
                        use_container_width=True, hide_index=True)

        with mrio_exp:
            exp = mrio.effective_china_exposure()
            st.subheader("China Exposure by Supply Chain Stage")
            if isinstance(exp, pd.DataFrame):
                st.dataframe(exp, use_container_width=True, hide_index=True, height=300)
                val_col = "MRIO_China_%" if "MRIO_China_%" in exp.columns else (
                          "Effective_China_%" if "Effective_China_%" in exp.columns else None)
                if val_col:
                    fig_exp = px.bar(exp.sort_values(val_col, ascending=False),
                                   x="Sector", y=val_col, template=DARK, height=300,
                                   color=val_col, color_continuous_scale="Reds",
                                   title="MRIO China Exposure by Stage (%)")
                    fig_exp.update_layout(xaxis_tickangle=-45, coloraxis_showscale=False)
                    st.plotly_chart(fig_exp, use_container_width=True)

        with mrio_link:
            fwd = mrio.forward_linkages()
            bwd = mrio.backward_linkages()
            st.subheader("Top 15 — Forward Linkages (supply-critical region-sectors)")
            st.dataframe(fwd.head(15), use_container_width=True, hide_index=True)
            st.subheader("Top 15 — Backward Linkages (demand-critical)")
            st.dataframe(bwd.head(15), use_container_width=True, hide_index=True)

        with mrio_shock:
            st.subheader("Interactive Regional Shock")
            sc1,sc2,sc3 = st.columns(3)
            shock_region = sc1.selectbox("Shock region", REGIONS,
                                         format_func=lambda r: REGION_LABELS[r],
                                         key="mrio_reg")
            shock_sector = sc2.selectbox("Shock sector", SECTORS,
                                         format_func=lambda s: SECTOR_SHORT.get(s,s),
                                         key="mrio_sec")
            shock_sev    = sc3.slider("Severity (%)", 5, 100, 50, key="mrio_sev")
            if st.button("▶ Run Regional Shock", type="primary", key="mrio_run"):
                with st.spinner("Running MRIO shock…"):
                    from mrio_model import flat, REGION_IDX, SECTOR_IDX
                    x_base    = mrio.gross_output()
                    A_shocked = mrio.A_mrio.copy()
                    r_idx = REGION_IDX[shock_region]
                    s_idx = SECTOR_IDX[shock_sector]
                    for j in range(mrio.A_mrio.shape[1]):
                        A_shocked[r_idx*8+s_idx, j] *= (1 - shock_sev/100)
                    from numpy.linalg import inv
                    L_sh = inv(np.eye(mrio.A_mrio.shape[0]) - A_shocked)
                    x_sh = L_sh @ mrio.uk_final_demand()
                    rows = []
                    for si, sec in enumerate(SECTORS):
                        tb = sum(x_base[ri*8+si] for ri in range(8))
                        ts = sum(x_sh[ri*8+si]   for ri in range(8))
                        rows.append({"Sector":SECTOR_SHORT.get(sec,sec),
                                     "Baseline":tb,"Shocked":ts,
                                     "Change_%":(ts-tb)/(tb+1e-12)*100})
                    df_sh = pd.DataFrame(rows)
                fig_sh = go.Figure()
                fig_sh.add_trace(go.Bar(x=df_sh["Sector"],y=df_sh["Baseline"],
                                       name="Baseline",marker_color="#457b9d"))
                fig_sh.add_trace(go.Bar(x=df_sh["Sector"],y=df_sh["Shocked"],
                                       name="Shocked",marker_color="#e63946",opacity=0.85))
                fig_sh.update_layout(barmode="group", height=360, template=DARK,
                                    yaxis_title="Gross output (normalised)",
                                    title=f"MRIO Shock: {REGION_LABELS[shock_region]} {shock_sector} −{shock_sev}%")
                st.plotly_chart(fig_sh, use_container_width=True)
                fig_chg = go.Figure(go.Bar(
                    x=df_sh["Sector"], y=df_sh["Change_%"],
                    marker_color=["#e63946" if v<0 else "#2a9d8f" for v in df_sh["Change_%"]],
                    text=[f"{v:.1f}%" for v in df_sh["Change_%"]], textposition="outside",
                ))
                fig_chg.update_layout(height=280, template=DARK, yaxis_title="% change")
                st.plotly_chart(fig_chg, use_container_width=True)

    with tab_ghosh:
        st.subheader("Ghosh Supply-Push Analysis")
        st.caption("Forward propagation of primary input constraints through the supply chain")
        with st.spinner("Building Ghosh model…"):
            ghosh = _ghosh()
            from ghosh_model import GHOSH_SCENARIOS

        g_link, g_quad, g_sc = st.tabs(
            ["📊 Forward Linkages", "🎯 4-Quadrant Map", "⚡ Supply Shock Scenarios"])

        with g_link:
            fl = ghosh.forward_linkages()
            ca,cb = st.columns(2)
            with ca:
                fig = px.bar(fl.sort_values("FL_Ghosh_Norm", ascending=True),
                            x="FL_Ghosh_Norm", y="Sector", orientation="h",
                            color="Supply_Critical",
                            color_discrete_map={True:"#e63946", False:"#457b9d"},
                            template=DARK, height=340,
                            title="Ghosh Forward Linkage (normalised)",
                            text="FL_Ghosh_Norm")
                fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
                fig.add_vline(x=1.0, line_dash="dash", line_color="#94a3b8",
                             annotation_text="Mean=1.0")
                fig.update_layout(showlegend=False, margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig, use_container_width=True)
            with cb:
                st.subheader("Value-Added by Stage (primary inputs)")
                fig_gva = px.bar(fl.sort_values("Value_Added_GBP", ascending=False),
                               x="Sector", y="Value_Added_GBP",
                               color="Supply_Critical",
                               color_discrete_map={True:"#e63946",False:"#2a9d8f"},
                               template=DARK, height=340,
                               title="Primary Inputs (£ — ONS GVA rates)")
                fig_gva.update_layout(xaxis_tickangle=-45, showlegend=False)
                st.plotly_chart(fig_gva, use_container_width=True)
            st.dataframe(fl, use_container_width=True, hide_index=True)

        with g_quad:
            lv = ghosh.leontief_vs_ghosh_linkages()
            fig_q = px.scatter(lv, x="BL_Norm", y="FL_Norm",
                              text="Sector", color="Key_Sector",
                              color_discrete_map={True:"#e63946",False:"#457b9d"},
                              template=DARK, height=450,
                              title="Leontief vs Ghosh Linkages — 4-Quadrant Map",
                              labels={"BL_Norm":"Backward Linkage (demand-pull, normalised)",
                                      "FL_Norm":"Forward Linkage (supply-push, normalised)"})
            fig_q.update_traces(textposition="top center", marker=dict(size=14))
            fig_q.add_vline(x=1.0, line_dash="dash", line_color="#475569")
            fig_q.add_hline(y=1.0, line_dash="dash", line_color="#475569")
            for (tx,ty,label) in [(0.3,1.8,"Supply-push dominant"),
                                   (1.8,1.8,"Structurally central"),
                                   (0.3,0.3,"Peripheral"),
                                   (1.8,0.3,"Demand-pull dominant")]:
                fig_q.add_annotation(x=tx, y=ty, text=label, showarrow=False,
                                   font=dict(color="#64748b",size=10))
            st.plotly_chart(fig_q, use_container_width=True)

        with g_sc:
            st.subheader("Ghosh Supply Shock Scenarios")
            gs_sel = st.selectbox("Scenario", list(GHOSH_SCENARIOS.keys()),
                                 format_func=lambda k: f"{k}: {GHOSH_SCENARIOS[k]['name'][:55]}",
                                 key="ghosh_sel")
            gs_sev = st.slider("Shock severity override (%)", 10, 100,
                              int(list(GHOSH_SCENARIOS[gs_sel]["shocks"].values())[0]*100),
                              key="ghosh_sev")
            if st.button("▶ Run Ghosh Scenario", type="primary", key="ghosh_run"):
                with st.spinner("Running Ghosh scenario…"):
                    shocks = {k: gs_sev/100 for k in GHOSH_SCENARIOS[gs_sel]["shocks"]}
                    res_g  = ghosh.supply_shock(shocks)
                pct = res_g["pct_change"]
                fig_g = go.Figure(go.Bar(
                    x=[SECTOR_SHORT.get(s,s) for s in SECTORS], y=pct,
                    marker_color=["#e63946" if v<0 else "#2a9d8f" for v in pct],
                    text=[f"{v:.1f}%" for v in pct], textposition="outside",
                ))
                fig_g.update_layout(height=360, template=DARK,
                                   yaxis_title="% output change",
                                   title=f"{gs_sel}: {GHOSH_SCENARIOS[gs_sel]['name'][:60]}",
                                   margin=dict(l=0,r=0,t=50,b=0))
                st.plotly_chart(fig_g, use_container_width=True)
                st.metric("Total output loss", f"£{res_g['total_output_loss_gbp']/1e9:.3f}bn")
            if st.button("📊 Compare All Ghosh Scenarios", key="ghosh_comp"):
                with st.spinner("Running all Ghosh scenarios…"):
                    comp = ghosh.scenarios_comparison()
                st.dataframe(comp, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Scenario Simulator":
    st.title("Supply Chain Shock Simulator")
    st.caption("5 scenarios · IO × CGE × ABM coupled simulation · Sequential, Per-period or Gauss-Seidel coupling")

    from shocks import ALL_SCENARIOS, build_cge_supply_array, build_io_shock_schedule

    # Maximum agents per sector = number of source countries in STAGE_GEOGRAPHY
    _MAX_AGENTS = [7, 6, 5, 5, 5, 11, 2, 1]   # Oil, Chem, PTA, PET, Fab, Gar, Who, Ret

    with st.sidebar:
        st.divider()
        st.subheader("Simulation Controls")
        sc_key    = st.selectbox("Scenario", list(SCENARIO_INFO.keys()),
                                format_func=lambda k: f"{k}: {SCENARIO_INFO[k][0]}")
        T_weeks   = st.slider("Simulation weeks", 12, 104, 52, step=4,
                              help="Number of weekly periods to simulate.")
        st_month  = st.slider("Start month", 1, 12, 1)
        seas      = st.checkbox("HMRC seasonality", True)
        coupling  = st.selectbox(
            "Coupling mode",
            ["Sequential (IO | CGE | ABM)", "Per-period Coupled", "Gauss-Seidel Coupled"],
            index=1,
            help=(
                "**Sequential**: each model runs independently — fastest.\n\n"
                "**Per-period Coupled**: IO↔CGE↔ABM exchange signals every week; "
                "supply fractions and prices are time-varying.\n\n"
                "**Gauss-Seidel Coupled**: adds inner iterations so IO, CGE, and the "
                "technical coefficient matrix A converge within each period. "
                "Slowest but most internally consistent."
            ),
        )
        abm_fb    = st.checkbox("ABM→CGE demand feedback", False,
                                help="EMA-smooth ABM aggregate orders into CGE demand "
                                     "multipliers (weight 0.10). Captures persistent "
                                     "ordering shifts while damping Beer-Game spikes.")

        st.divider()
        st.subheader("Firms per stage")
        st.caption("Each firm = one sourcing country. Max per stage is set by "
                   "available geographies in the data.")
        agent_counts = []
        for i, sector in enumerate(SECTORS):
            max_ag = _MAX_AGENTS[i]
            default = min(3, max_ag)
            if max_ag > 1:
                n = st.slider(
                    SECTOR_SHORT[sector],
                    min_value=1, max_value=max_ag, value=default,
                    key=f"n_ag_{i}",
                    help=f"{sector}: up to {max_ag} source countries available.",
                )
            else:
                st.caption(f"{SECTOR_SHORT[sector]}: 1 (fixed)")
                n = 1
            agent_counts.append(n)

        run_btn = st.button("▶ Run Simulation", type="primary", use_container_width=True)

    sc_name, sc_desc = SCENARIO_INFO[sc_key]
    coupling_short = coupling.split(" ")[0]
    agents_str = "-".join(str(c) for c in agent_counts)
    st.info(
        f"**{sc_key}: {sc_name}**  \n{sc_desc}  \n"
        f"*Coupling: {coupling} · T={T_weeks} wks · "
        f"Firms: {', '.join(f'{SECTOR_SHORT[s]}={agent_counts[i]}' for i, s in enumerate(SECTORS))}*"
    )

    res_key = f"sim_{sc_key}_{T_weeks}_{st_month}_{seas}_{coupling_short}_{abm_fb}_{agents_str}"

    if run_btn:
        model    = _model()
        scenario = ALL_SCENARIOS[sc_key]

        if coupling_short == "Sequential":
            with st.spinner(f"Running {sc_key} sequentially ({T_weeks} wks)…"):
                from abm_model import PolyesterSupplyChainABM
                from cge_model import CGEModel
                io_sched = build_io_shock_schedule(scenario)
                io_r     = model.io.simulate(T=T_weeks, final_demand_base=model.fd_base,
                                             shock_schedule=io_sched)
                cge_m    = CGEModel(tariff_schedule=scenario.tariffs) if scenario.tariffs else model.cge
                supply   = build_cge_supply_array(scenario)
                cge_r    = cge_m.equilibrium(supply_shocks=supply, final_demand=model.fd_base)
                abm      = PolyesterSupplyChainABM(agents_per_sector=agent_counts)
                abm_r    = abm.run(T=T_weeks, baseline_demand=1.0,
                                   shock_schedule=scenario.abm_schedule,
                                   demand_noise=0.03*float(cge_r["equilibrium_prices"].max()),
                                   start_month=st_month, apply_seasonality=seas)
                bw = abm.bullwhip_ratio(abm_r)
                sl = abm.service_level(abm_r)
                rt = abm.recovery_time(abm_r)
            st.session_state[res_key] = {
                "io":io_r, "cge":cge_r, "abm":abm_r,
                "bw":bw, "sl":sl, "rt":rt,
                "T":T_weeks, "onset":scenario.onset_week,
                "price_series": None, "supply_fracs": None, "a_drift": None,
            }

        elif coupling_short == "Per-period":
            with st.spinner(f"Running {sc_key} per-period coupled ({T_weeks} wks)…"):
                model.rebuild_abm(agent_counts)
                coupled = model.run_coupled(
                    scenario, T=T_weeks,
                    demand_noise=0.03, start_month=st_month,
                    apply_seasonality=seas, abm_demand_feedback=abm_fb,
                )
            st.session_state[res_key] = {
                "io":  coupled["io_result"],
                "cge": coupled["cge_result"],
                "abm": coupled["abm_result"],
                "bw":  coupled["bullwhip"],
                "sl":  coupled["service_level"],
                "rt":  coupled["recovery_time"],
                "T":   T_weeks, "onset": scenario.onset_week,
                "price_series":  coupled["cge_result"].get("price_series"),
                "supply_fracs":  coupled.get("coupled_supply_fracs"),
                "a_drift":       None,
                "welfare_gbp":   coupled.get("welfare_gbp"),
                "total_loss":    coupled.get("total_shortage_gbp"),
            }

        else:  # Gauss-Seidel
            with st.spinner(f"Running {sc_key} GS-coupled ({T_weeks} wks) — this may take ~20 s…"):
                model.rebuild_abm(agent_counts)
                coupled = model.run_coupled_gs(
                    scenario, T=T_weeks,
                    demand_noise=0.03, start_month=st_month,
                    apply_seasonality=seas, abm_demand_feedback=abm_fb,
                )
            st.session_state[res_key] = {
                "io":  coupled["io_result"],
                "cge": coupled["cge_result"],
                "abm": coupled["abm_result"],
                "bw":  coupled["bullwhip"],
                "sl":  coupled["service_level"],
                "rt":  coupled["recovery_time"],
                "T":   T_weeks, "onset": scenario.onset_week,
                "price_series":  coupled["cge_result"].get("price_series"),
                "supply_fracs":  coupled.get("coupled_supply_fracs"),
                "a_drift":       coupled.get("A_drift_final"),
                "gs_iters":      coupled.get("gs_iterations"),
                "a_evolution":   coupled.get("A_evolution"),
                "welfare_gbp":   coupled.get("welfare_gbp"),
                "total_loss":    coupled.get("total_shortage_gbp"),
            }

    res = st.session_state.get(res_key)
    if res is None:
        st.info("Select a scenario and click **▶ Run Simulation** to begin.")
        rows = [{"ID":k,"Name":n,"Description":d,
                 "Onset wk":ALL_SCENARIOS[k].onset_week,
                 "Duration wk":ALL_SCENARIOS[k].duration_weeks}
                for k,(n,d) in SCENARIO_INFO.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.stop()

    io_r, cge_r, abm_r = res["io"], res["cge"], res["abm"]
    bw, sl, rt, T_sim, onset = res["bw"], res["sl"], res["rt"], res["T"], res["onset"]
    price_series = res.get("price_series")
    supply_fracs = res.get("supply_fracs")
    a_drift      = res.get("a_drift")
    weeks = list(range(T_sim))

    welfare  = res.get("welfare_gbp") or cge_r.get("welfare_change_gbp", 0.0)
    max_dp   = cge_r["price_index_change_pct"].max()
    max_dp_s = SECTORS[int(cge_r["price_index_change_pct"].argmax())]
    avg_rec  = rt["Recovery_Week"].dropna()
    avg_rv   = f"{avg_rec.mean():.1f} wks" if len(avg_rec) else "—"
    total_loss = res.get("total_loss") or 0.0

    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Welfare Change", f"£{welfare/1e9:.3f}bn", delta_color="inverse")
    m2.metric("Max Price Rise",  f"{max_dp:.1f}%", SECTOR_SHORT.get(max_dp_s,max_dp_s))
    m3.metric("IO Total Shortage", f"{float(io_r['shortage'].sum()):.3f}")
    m4.metric("Mean Recovery", avg_rv)
    if a_drift is not None:
        m5.metric("A-Matrix Drift", f"{a_drift:.4f}", help="Max abs change in A from baseline (GS mode)")
    else:
        m5.metric("Economic Loss", f"£{total_loss/1e9:.3f}bn")

    # Tabs — add "Coupled Dynamics" when a time-series price/supply signal is available
    tab_labels = ["📊 I-O Output", "💰 CGE Prices", "🤖 ABM Dynamics", "📋 Metrics"]
    if price_series is not None or supply_fracs is not None:
        tab_labels.insert(2, "🔗 Coupled Dynamics")
    tabs = st.tabs(tab_labels)
    tab_map = {lbl: tab for lbl, tab in zip(tab_labels, tabs)}

    with tab_map["📊 I-O Output"]:
        out = io_r.get("output")
        if out is not None and out.ndim==2:
            fig_io = go.Figure()
            for i,s in enumerate(SECTORS):
                fig_io.add_trace(go.Scatter(x=weeks, y=out[:,i],
                                           name=SECTOR_SHORT.get(s,s), mode="lines"))
            fig_io.add_vline(x=onset, line_dash="dash", line_color="#e63946",
                            annotation_text="Shock", annotation_font_color="#e63946")
            fig_io.update_layout(height=380, template=DARK, yaxis_title="Output (norm.)",
                                legend=dict(orientation="h",y=-0.2), hovermode="x unified")
            st.plotly_chart(fig_io, use_container_width=True)

        shr = io_r.get("shortage")
        if shr is not None and shr.ndim==2 and shr.max()>1e-6:
            fig_shr = go.Figure()
            for i,s in enumerate(SECTORS):
                if shr[:,i].max()>1e-6:
                    fig_shr.add_trace(go.Scatter(x=weeks,y=shr[:,i],
                                                name=SECTOR_SHORT.get(s,s),
                                                fill="tozeroy",mode="lines"))
            fig_shr.add_vline(x=onset, line_dash="dash", line_color="#e63946")
            fig_shr.update_layout(height=280, template=DARK,
                                 yaxis_title="Shortage (norm.)", hovermode="x unified")
            st.plotly_chart(fig_shr, use_container_width=True)

    with tab_map["💰 CGE Prices"]:
        pct    = cge_r["price_index_change_pct"]
        prices = cge_r["equilibrium_prices"]
        cp1,cp2 = st.columns(2)
        with cp1:
            price_label = "Avg price change %" if price_series is not None else "Price change %"
            fig_p = go.Figure(go.Bar(
                x=[SECTOR_SHORT.get(s,s) for s in SECTORS], y=pct,
                marker_color=["#e63946" if v>5 else "#e9c46a" if v>0 else "#2a9d8f" for v in pct],
                text=[f"{v:.1f}%" for v in pct], textposition="outside",
            ))
            fig_p.update_layout(height=360, template=DARK,
                               yaxis_title=price_label,
                               title="Price Changes by Sector")
            st.plotly_chart(fig_p, use_container_width=True)
        with cp2:
            df_p = pd.DataFrame({"Sector":[SECTOR_SHORT.get(s,s) for s in SECTORS],
                                 "Eq. Price":prices.round(4),"Change %":pct.round(2)})
            st.dataframe(df_p.style.background_gradient(cmap="RdYlGn_r",subset=["Change %"]),
                        use_container_width=True, height=360)
            st.caption(f"{'✅' if cge_r.get('converged',True) else '⚠️'} "
                      f"Converged in {cge_r.get('iterations','?')} iterations")
            if price_series is not None:
                st.caption("ℹ️ Prices above are **time-averages** from the coupled simulation. "
                           "See the **🔗 Coupled Dynamics** tab for the full time series.")

    if "🔗 Coupled Dynamics" in tab_map:
        with tab_map["🔗 Coupled Dynamics"]:
            st.markdown("**IO supply fractions and CGE prices evolve together each period — "
                        "feedback loops are active.**")
            cd1, cd2 = st.columns(2)

            if price_series is not None:
                with cd1:
                    fig_pt = go.Figure()
                    for i,s in enumerate(SECTORS):
                        fig_pt.add_trace(go.Scatter(x=weeks, y=price_series[:,i],
                                                   name=SECTOR_SHORT.get(s,s), mode="lines"))
                    fig_pt.add_vline(x=onset, line_dash="dash", line_color="#e63946",
                                    annotation_text="Shock", annotation_font_color="#e63946")
                    fig_pt.add_hline(y=1.0, line_dash="dot", line_color="#94a3b8")
                    fig_pt.update_layout(height=360, template=DARK,
                                        yaxis_title="Price index (1 = baseline)",
                                        title="CGE Price Path (coupled)",
                                        legend=dict(orientation="h",y=-0.25),
                                        hovermode="x unified")
                    st.plotly_chart(fig_pt, use_container_width=True)

            if supply_fracs is not None:
                with cd2:
                    fig_sf = go.Figure()
                    for i,s in enumerate(SECTORS):
                        fig_sf.add_trace(go.Scatter(x=weeks, y=supply_fracs[:,i],
                                                   name=SECTOR_SHORT.get(s,s), mode="lines"))
                    fig_sf.add_vline(x=onset, line_dash="dash", line_color="#e63946",
                                    annotation_text="Shock", annotation_font_color="#e63946")
                    fig_sf.add_hline(y=1.0, line_dash="dot", line_color="#94a3b8")
                    fig_sf.update_layout(height=360, template=DARK,
                                        yaxis_range=[0, 1.05],
                                        yaxis_title="Supply fraction (1 = full capacity)",
                                        title="IO Supply Fractions (coupled)",
                                        legend=dict(orientation="h",y=-0.25),
                                        hovermode="x unified")
                    st.plotly_chart(fig_sf, use_container_width=True)

            # GS-specific: A-matrix evolution heatmap
            a_evol = res.get("a_evolution")
            gs_iters = res.get("gs_iters")
            if a_evol is not None:
                st.subheader("Technical Coefficient Matrix (A) Evolution")
                col_ae, col_gi = st.columns([3,2])
                with col_ae:
                    # Show A at t=0, t=T/2, t=T-1 side by side
                    t_checkpoints = [0, T_sim//2, T_sim-1]
                    fig_ae = make_subplots(rows=1, cols=3,
                                          subplot_titles=[f"t={t}" for t in t_checkpoints])
                    for ci, t_c in enumerate(t_checkpoints):
                        A_t = a_evol[t_c]
                        fig_ae.add_trace(
                            go.Heatmap(z=A_t, colorscale="Blues",
                                      showscale=(ci==2),
                                      zmin=0, zmax=float(a_evol[0].max())*1.1),
                            row=1, col=ci+1
                        )
                    fig_ae.update_layout(height=300, template=DARK,
                                        title="A-matrix snapshots (rows=inputs, cols=outputs)")
                    st.plotly_chart(fig_ae, use_container_width=True)
                with col_gi:
                    if gs_iters is not None:
                        fig_gi = go.Figure(go.Bar(
                            x=weeks, y=gs_iters,
                            marker_color="#457b9d",
                        ))
                        fig_gi.update_layout(height=300, template=DARK,
                                            yaxis_title="GS iterations",
                                            title="GS iterations to convergence")
                        st.plotly_chart(fig_gi, use_container_width=True)

    with tab_map["🤖 ABM Dynamics"]:
        inv  = abm_r["inventory"]
        ordr = abm_r["orders"]
        fig_inv = go.Figure()
        fig_ord = go.Figure()
        for i,s in enumerate(SECTORS):
            lbl = SECTOR_SHORT.get(s,s)
            fig_inv.add_trace(go.Scatter(x=weeks,y=inv[:,i], name=lbl,mode="lines"))
            fig_ord.add_trace(go.Scatter(x=weeks,y=ordr[:,i],name=lbl,mode="lines"))
        for fig_ in [fig_inv,fig_ord]:
            fig_.add_vline(x=onset,line_dash="dash",line_color="#e63946",
                          annotation_text="Shock",annotation_font_color="#e63946")
            fig_.update_layout(height=320,template=DARK,
                               legend=dict(orientation="h",y=-0.25),
                               hovermode="x unified")
        fig_inv.update_layout(yaxis_title="Inventory level",title="Inventory Dynamics")
        fig_ord.update_layout(yaxis_title="Order quantity",title="Orders (Bullwhip effect)")
        st.plotly_chart(fig_inv, use_container_width=True)
        st.plotly_chart(fig_ord, use_container_width=True)

    with tab_map["📋 Metrics"]:
        mc1,mc2,mc3 = st.columns(3)
        mc1.subheader("Bullwhip")
        mc1.dataframe(bw.style.background_gradient(cmap="Reds",subset=["Bullwhip_Ratio"]),
                     use_container_width=True)
        mc2.subheader("Service Level")
        mc2.dataframe(sl.style.background_gradient(cmap="RdYlGn",subset=["Service_Level_%"]),
                     use_container_width=True)
        mc3.subheader("Recovery Time")
        mc3.dataframe(rt, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# ALL SCENARIOS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋 All Scenarios":
    st.title("All Scenarios — Comparison & Analysis")
    st.caption("Run all 5 shock scenarios and compare welfare, price, shortage and recovery metrics side-by-side")

    from shocks import ALL_SCENARIOS

    with st.sidebar:
        st.divider()
        T_all   = st.slider("Simulation weeks", 12, 78, 52, step=4, key="all_T_slider")
        run_all = st.button("▶ Run All Scenarios", type="primary", use_container_width=True)

    if run_all:
        model = _model()
        prog  = st.progress(0, text="Running scenarios…")
        all_results = {}
        for i,(key,scenario) in enumerate(ALL_SCENARIOS.items()):
            prog.progress((i)/5, text=f"Running {key}: {scenario.name}…")
            all_results[key] = model.run_scenario(scenario, T=T_all, verbose=False)
        prog.progress(1.0, text="Done.")
        st.session_state["all_results"] = all_results
        st.session_state["all_T_result"] = T_all

    results = st.session_state.get("all_results")
    if results is None:
        st.info("Click **▶ Run All Scenarios** to run all five scenarios and compare results.")
        # Static preview table
        rows = [{"ID":k,"Name":n,"Onset wk":ALL_SCENARIOS[k].onset_week,
                 "Duration wk":ALL_SCENARIOS[k].duration_weeks,"Description":d}
                for k,(n,d) in SCENARIO_INFO.items()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.stop()

    # Build comparison table
    model = _model()
    comp  = model.comparison_table(results)

    st.subheader("Cross-Scenario Comparison Table")
    st.dataframe(
        comp.style.background_gradient(cmap="RdYlGn_r", subset=["Max_Price_Rise_%","Economic_Loss_£bn"]),
        use_container_width=True, hide_index=True,
    )
    st.download_button("⬇ Download comparison CSV", data=comp.to_csv(index=False),
                      file_name="scenario_comparison.csv", mime="text/csv")

    st.divider()

    # Economic loss comparison bar
    fig_loss = go.Figure(go.Bar(
        x=comp["Scenario"],
        y=comp["Economic_Loss_£bn"],
        marker_color=["#e63946","#f4a261","#e9c46a","#2a9d8f","#457b9d"],
        text=[f"£{v:.3f}bn" for v in comp["Economic_Loss_£bn"]],
        textposition="outside",
    ))
    fig_loss.update_layout(height=320, template=DARK, yaxis_title="Economic Loss (£bn)",
                          title="Economic Loss by Scenario",
                          margin=dict(l=0,r=0,t=50,b=0))
    st.plotly_chart(fig_loss, use_container_width=True)

    # Price × welfare heatmap
    col_a, col_b = st.columns(2)
    with col_a:
        fig_p = go.Figure(go.Bar(
            x=comp["Scenario"], y=comp["Max_Price_Rise_%"],
            marker_color="#e63946", text=[f"{v:.1f}%" for v in comp["Max_Price_Rise_%"]],
            textposition="outside",
        ))
        fig_p.update_layout(height=300, template=DARK, yaxis_title="Max Price Rise %",
                           title="Max CGE Price Rise")
        st.plotly_chart(fig_p, use_container_width=True)

    with col_b:
        fig_w = go.Figure(go.Bar(
            x=comp["Scenario"], y=comp["Welfare_Change_£bn"],
            marker_color="#457b9d", text=[f"£{v:.3f}bn" for v in comp["Welfare_Change_£bn"]],
            textposition="outside",
        ))
        fig_w.update_layout(height=300, template=DARK, yaxis_title="Welfare Change £bn",
                           title="CGE Welfare Change")
        st.plotly_chart(fig_w, use_container_width=True)

    # Recovery time
    fig_rec = go.Figure(go.Bar(
        x=comp["Scenario"],
        y=[float(v) if str(v).replace(".","").isdigit() else 0
           for v in comp["Avg_Recovery_Weeks"]],
        marker_color="#e9c46a",
        text=comp["Avg_Recovery_Weeks"].astype(str), textposition="outside",
    ))
    fig_rec.update_layout(height=300, template=DARK, yaxis_title="Weeks",
                         title="Average Recovery Time (ABM)")
    st.plotly_chart(fig_rec, use_container_width=True)

    # Per-scenario ABM inventory overlays
    st.subheader("ABM Inventory Dynamics — All Scenarios")
    sector_sel = st.selectbox("Sector to plot", SECTORS,
                              format_func=lambda s: SECTOR_SHORT.get(s,s),
                              key="all_sector")
    s_idx = SECTORS.index(sector_sel)
    fig_all = go.Figure()
    for key, res in results.items():
        inv = res["abm_result"]["inventory"]
        onset = ALL_SCENARIOS[key].onset_week
        fig_all.add_trace(go.Scatter(
            x=list(range(len(inv))), y=inv[:,s_idx],
            name=f"{key}: {SCENARIO_INFO[key][0][:25]}", mode="lines",
        ))
    fig_all.update_layout(height=380, template=DARK,
                         yaxis_title=f"Inventory — {SECTOR_SHORT.get(sector_sel,sector_sel)}",
                         legend=dict(orientation="h",y=-0.2), hovermode="x unified")
    st.plotly_chart(fig_all, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# POLICY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🏛️ Policy Analysis":
    st.title("UK Government Policy Analysis")
    st.caption(
        "Compare five resilience interventions against a baseline shock scenario. "
        "Policies are applied pre-shock; results show IO output, CGE prices, "
        "ABM shortages and welfare metrics."
    )

    from shocks import ALL_SCENARIOS
    from policies import ALL_POLICIES

    _POL_COLORS = {
        "Baseline": "#94a3b8",
        "P1": "#2a9d8f",
        "P2": "#457b9d",
        "P3": "#e9c46a",
        "P4": "#f4a261",
        "P5": "#e63946",
    }

    with st.sidebar:
        st.divider()
        st.subheader("Policy Controls")
        pol_sc_key = st.selectbox(
            "Shock scenario", list(SCENARIO_INFO.keys()),
            format_func=lambda k: f"{k}: {SCENARIO_INFO[k][0]}",
            key="pol_sc",
        )
        pol_policies = st.multiselect(
            "Policies to test",
            options=list(ALL_POLICIES.keys()),
            default=["P1", "P2", "P5"],
            format_func=lambda k: f"{k}: {ALL_POLICIES[k].name}",
            key="pol_sel",
        )
        pol_T = st.slider("Simulation weeks", 12, 104, 52, step=4, key="pol_T")
        pol_run = st.button("▶ Run Policy Analysis", type="primary", use_container_width=True)

    pol_key = f"pol_{pol_sc_key}_{'_'.join(sorted(pol_policies))}_{pol_T}"

    # ── Policy description cards ──────────────────────────────────────────────
    with st.expander("📖 Policy Descriptions", expanded=False):
        for code, pol in ALL_POLICIES.items():
            st.markdown(f"**{pol.code} — {pol.name}** &nbsp; `£{pol.cost_estimate_gbp_m:.0f}m/yr`")
            st.markdown(pol.description)
            st.divider()

    if pol_run:
        model    = _model()
        scenario = ALL_SCENARIOS[pol_sc_key]
        results_pol = {}

        prog = st.progress(0, text="Running baseline…")
        model.rebuild_abm(3)
        baseline = model.run_coupled(scenario, T=pol_T, demand_noise=0.03, policy=None)
        results_pol["Baseline"] = baseline
        prog.progress(1 / (len(pol_policies) + 1), text="Baseline done.")

        for i, pc in enumerate(pol_policies):
            prog.progress((i + 1) / (len(pol_policies) + 1),
                          text=f"Running {pc}: {ALL_POLICIES[pc].name}…")
            model.rebuild_abm(3)
            res = model.run_coupled(
                scenario, T=pol_T, demand_noise=0.03,
                policy=ALL_POLICIES[pc],
            )
            results_pol[pc] = res

        prog.progress(1.0, text="Done.")
        st.session_state[pol_key] = results_pol

    pol_results = st.session_state.get(pol_key)
    if pol_results is None:
        st.info("Select a scenario and policies, then click **▶ Run Policy Analysis**.")
        rows = [{
            "Code": p.code, "Name": p.name,
            "Buffer": "✓" if p.buffer_sectors else "—",
            "Diversify": "✓" if p.diversify_sectors else "—",
            "Recovery": "✓" if p.recovery_boost else "—",
            "Reserve": "✓" if p.reserve_release else "—",
            "Cost £m/yr": p.cost_estimate_gbp_m,
        } for p in ALL_POLICIES.values()]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.stop()

    baseline_r = pol_results["Baseline"]
    weeks_pol  = list(range(pol_T))
    onset_pol  = ALL_SCENARIOS[pol_sc_key].onset_week

    # ── Summary metrics table ─────────────────────────────────────────────────
    st.subheader("Policy Effectiveness Summary")
    base_welfare  = baseline_r.get("welfare_gbp", 0.0)
    base_loss     = baseline_r.get("total_shortage_gbp", 0.0)
    base_io_short = float(baseline_r["io_result"]["shortage"].sum())
    base_rt       = baseline_r["recovery_time"]["Recovery_Week"].dropna()
    base_rt_mean  = float(base_rt.mean()) if len(base_rt) else None

    metric_rows = []
    for run_key, res in pol_results.items():
        welfare  = res.get("welfare_gbp", 0.0)
        loss     = res.get("total_shortage_gbp", 0.0)
        io_short = float(res["io_result"]["shortage"].sum())
        rt       = res["recovery_time"]["Recovery_Week"].dropna()
        rt_mean  = float(rt.mean()) if len(rt) else None

        if run_key == "Baseline":
            cost_m = 0.0
            welfare_imp = "—"
            loss_red    = "—"
            rt_imp      = "—"
            cost_eff    = "—"
        else:
            pol      = ALL_POLICIES[run_key]
            cost_m   = pol.cost_estimate_gbp_m
            welfare_imp = f"£{(welfare - base_welfare)/1e9:+.3f}bn"
            loss_red_pct = (base_loss - loss) / (abs(base_loss) + 1e-9) * 100
            loss_red = f"{loss_red_pct:+.1f}%"
            if base_rt_mean and rt_mean:
                rt_imp = f"{base_rt_mean - rt_mean:+.1f} wks"
            else:
                rt_imp = "—"
            if cost_m > 0 and base_loss > loss:
                cost_eff = f"£{(base_loss - loss)/1e6/cost_m:.1f}m saved per £1m spent"
            else:
                cost_eff = "—"

        price_ts_r = res["io_result"]["prices"]
        max_price  = float(price_ts_r.max()) if price_ts_r is not None else 1.0

        metric_rows.append({
            "Run":               run_key,
            "Welfare Change":    f"£{welfare/1e9:.3f}bn",
            "Welfare Improvement": welfare_imp,
            "IO Shortage":       f"{io_short:.4f}",
            "Loss Reduction":    loss_red,
            "Max Price (×)":     f"{max_price:.3f}",
            "Mean Recovery (wk)": f"{rt_mean:.1f}" if rt_mean else "—",
            "Recovery Improvement": rt_imp,
            "Policy Cost £m/yr": f"{cost_m:.0f}" if cost_m else "—",
            "Cost Effectiveness": cost_eff,
        })
    st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)

    tab_io, tab_price, tab_abm, tab_detail = st.tabs([
        "📊 IO Output", "💰 CGE Prices", "🤖 ABM Shortage", "📋 Sector Detail",
    ])

    # ── IO Output ─────────────────────────────────────────────────────────────
    with tab_io:
        st.markdown("**Upstream output paths — PTA, PET/Yarn, Fabric, Garment**")
        focus_sectors = ["PTA_Production", "PET_Resin_Yarn", "Fabric_Weaving", "Garment_Assembly"]
        fig_io = make_subplots(rows=2, cols=2, shared_xaxes=True,
                               subplot_titles=[SECTOR_SHORT[s] for s in focus_sectors])
        for si, sec in enumerate(focus_sectors):
            row, col = divmod(si, 2)
            sec_idx  = SECTORS.index(sec)
            for run_key, res in pol_results.items():
                out = res["io_result"]["output"]
                color = _POL_COLORS.get(run_key, "#adb5bd")
                dash  = "solid" if run_key == "Baseline" else "dash"
                fig_io.add_trace(
                    go.Scatter(x=weeks_pol, y=out[:, sec_idx],
                               name=run_key, line=dict(color=color, dash=dash, width=2),
                               legendgroup=run_key,
                               showlegend=(si == 0)),
                    row=row+1, col=col+1,
                )
            fig_io.add_vline(x=onset_pol, line_dash="dot", line_color="#e63946",
                             row=row+1, col=col+1)
        fig_io.update_layout(height=480, template=DARK, hovermode="x unified",
                             legend=dict(orientation="h", y=-0.12))
        st.plotly_chart(fig_io, use_container_width=True)

    # ── CGE Prices ────────────────────────────────────────────────────────────
    with tab_price:
        st.markdown("**CGE equilibrium price paths — most affected sectors**")
        price_focus = ["PTA_Production", "PET_Resin_Yarn", "Fabric_Weaving", "UK_Retail"]
        fig_p = make_subplots(rows=2, cols=2, shared_xaxes=True,
                              subplot_titles=[SECTOR_SHORT[s] for s in price_focus])
        for si, sec in enumerate(price_focus):
            row, col = divmod(si, 2)
            sec_idx  = SECTORS.index(sec)
            for run_key, res in pol_results.items():
                pts = res["cge_result"].get("price_series")
                if pts is None:
                    pts = np.ones((pol_T, len(SECTORS)))
                    pts *= res["cge_result"]["equilibrium_prices"]
                color = _POL_COLORS.get(run_key, "#adb5bd")
                dash  = "solid" if run_key == "Baseline" else "dash"
                fig_p.add_trace(
                    go.Scatter(x=weeks_pol, y=pts[:, sec_idx],
                               name=run_key, line=dict(color=color, dash=dash, width=2),
                               legendgroup=run_key,
                               showlegend=(si == 0)),
                    row=row+1, col=col+1,
                )
            fig_p.add_vline(x=onset_pol, line_dash="dot", line_color="#e63946",
                            row=row+1, col=col+1)
        fig_p.update_layout(height=480, template=DARK, hovermode="x unified",
                            legend=dict(orientation="h", y=-0.12))
        st.plotly_chart(fig_p, use_container_width=True)

    # ── ABM Shortage ──────────────────────────────────────────────────────────
    with tab_abm:
        st.markdown("**ABM aggregate shortage by sector (total across all agents)**")
        fig_sht = go.Figure()
        for run_key, res in pol_results.items():
            abm_sht_sum = res["abm_result"]["shortage"].sum(axis=1)
            color = _POL_COLORS.get(run_key, "#adb5bd")
            dash  = "solid" if run_key == "Baseline" else "dash"
            fig_sht.add_trace(go.Scatter(
                x=weeks_pol, y=abm_sht_sum,
                name=run_key, line=dict(color=color, dash=dash, width=2),
                fill="tozeroy" if run_key == "Baseline" else None,
                fillcolor="rgba(148,163,184,0.1)" if run_key == "Baseline" else None,
            ))
        fig_sht.add_vline(x=onset_pol, line_dash="dot", line_color="#e63946",
                          annotation_text="Shock")
        fig_sht.update_layout(height=380, template=DARK, yaxis_title="Aggregate shortage",
                              hovermode="x unified",
                              legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig_sht, use_container_width=True)

        # Per-sector shortage heatmap (total over T)
        st.markdown("**Total shortage per sector per policy**")
        sht_data = {}
        for run_key, res in pol_results.items():
            sht_data[run_key] = res["abm_result"]["shortage"].sum(axis=0)
        df_sht = pd.DataFrame(sht_data, index=[SECTOR_SHORT[s] for s in SECTORS])
        fig_heat = px.imshow(
            df_sht,
            color_continuous_scale="RdYlGn_r",
            aspect="auto", text_auto=".3f",
            title="Sector × Policy shortage (lower is better)",
        )
        fig_heat.update_layout(height=350, template=DARK,
                               coloraxis_colorbar=dict(title="Shortage"))
        st.plotly_chart(fig_heat, use_container_width=True)

    # ── Sector Detail ─────────────────────────────────────────────────────────
    with tab_detail:
        detail_sec = st.selectbox(
            "Select sector",
            SECTORS,
            format_func=lambda s: SECTOR_SHORT.get(s, s),
            key="pol_detail_sec",
        )
        sec_idx = SECTORS.index(detail_sec)
        c1, c2 = st.columns(2)

        with c1:
            st.markdown(f"**IO output — {SECTOR_SHORT[detail_sec]}**")
            fig_d1 = go.Figure()
            for run_key, res in pol_results.items():
                out   = res["io_result"]["output"]
                color = _POL_COLORS.get(run_key, "#adb5bd")
                dash  = "solid" if run_key == "Baseline" else "dash"
                fig_d1.add_trace(go.Scatter(
                    x=weeks_pol, y=out[:, sec_idx],
                    name=run_key, line=dict(color=color, dash=dash, width=2),
                ))
            fig_d1.add_vline(x=onset_pol, line_dash="dot", line_color="#e63946")
            fig_d1.update_layout(height=300, template=DARK, yaxis_title="Output (norm.)",
                                 hovermode="x unified", showlegend=True)
            st.plotly_chart(fig_d1, use_container_width=True)

        with c2:
            st.markdown(f"**ABM inventory — {SECTOR_SHORT[detail_sec]}**")
            fig_d2 = go.Figure()
            for run_key, res in pol_results.items():
                inv   = res["abm_result"]["inventory"]
                color = _POL_COLORS.get(run_key, "#adb5bd")
                dash  = "solid" if run_key == "Baseline" else "dash"
                fig_d2.add_trace(go.Scatter(
                    x=weeks_pol, y=inv[:, sec_idx],
                    name=run_key, line=dict(color=color, dash=dash, width=2),
                ))
            fig_d2.add_vline(x=onset_pol, line_dash="dot", line_color="#e63946")
            fig_d2.update_layout(height=300, template=DARK, yaxis_title="Inventory (norm.)",
                                 hovermode="x unified", showlegend=True)
            st.plotly_chart(fig_d2, use_container_width=True)

        # Bullwhip comparison
        st.markdown("**Bullwhip Ratio by Sector**")
        bw_data = {}
        for run_key, res in pol_results.items():
            bw_data[run_key] = res["bullwhip"].set_index("Sector")["Bullwhip_Ratio"]
        df_bw = pd.DataFrame(bw_data)
        df_bw.index = [SECTOR_SHORT.get(s, s) for s in df_bw.index]
        fig_bw = px.bar(df_bw.reset_index().melt(id_vars="index"),
                        x="index", y="value", color="variable",
                        barmode="group",
                        color_discrete_map=_POL_COLORS,
                        labels={"index": "Sector", "value": "Bullwhip Ratio",
                                "variable": "Run"},
                        template=DARK)
        fig_bw.update_layout(height=320, legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig_bw, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "✅ Validation":
    st.title("Model Validation Against Historical Events")
    st.caption(
        "Seven calibration events (V1–V7) — each modelled with event-specific "
        "parameters and compared against HMRC OTS, ICIS, ONS, and Bloomberg benchmarks."
    )

    from validation import HISTORICAL_EVENTS, run_validation_event, compare_event

    # ── Run validation suite ──────────────────────────────────────────────────
    with st.sidebar:
        st.divider()
        st.subheader("Validation Controls")
        run_val = st.button("▶ Run All 7 Events", type="primary",
                            use_container_width=True,
                            help="Runs CGE + IO + ABM for each historical event (~10 s)")
        val_event_sel = st.selectbox(
            "Inspect event",
            options=[e["id"] for e in HISTORICAL_EVENTS],
            format_func=lambda eid: f"{eid}: {next(e['name'] for e in HISTORICAL_EVENTS if e['id']==eid)}",
            key="val_event",
        )

    val_cache_key = "val_results_v2"

    if run_val:
        prog = st.progress(0, text="Running validation events…")
        val_results = {}
        for i, ev in enumerate(HISTORICAL_EVENTS):
            prog.progress(i / len(HISTORICAL_EVENTS), text=f"Running {ev['id']}: {ev['name']}…")
            try:
                result = run_validation_event(ev)
                cmp_df = compare_event(ev, result)
                val_results[ev["id"]] = {"result": result, "cmp": cmp_df, "event": ev}
            except Exception as e:
                val_results[ev["id"]] = {"error": str(e), "event": ev}
        prog.progress(1.0, text="Done.")
        st.session_state[val_cache_key] = val_results

    val_data = st.session_state.get(val_cache_key)

    # ── Summary scorecard (runs or not) ───────────────────────────────────────
    st.subheader("Validation Scorecard — All Events")

    if val_data:
        summary_rows = []
        for ev in HISTORICAL_EVENTS:
            eid = ev["id"]
            if eid not in val_data:
                continue
            entry = val_data[eid]
            if "error" in entry:
                summary_rows.append({"ID": eid, "Event": ev["name"],
                                     "Direction OK": "—", "Metrics": "ERROR",
                                     "Error %": "—", "Status": "❌ Error"})
                continue
            df = entry["cmp"]
            dir_ok = int(df["Direction_OK"].sum()) if "Direction_OK" in df.columns else "—"
            n_total = len(df)
            err_pct = df["Error_%"].abs() if "Error_%" in df.columns else pd.Series([])
            within30 = int((err_pct < 30).sum()) if len(err_pct) else "—"
            mean_err = f"{err_pct.mean():.0f}%" if len(err_pct) else "—"
            status = ("✅ Good" if isinstance(within30, int) and within30 == n_total
                      else "⚠️ Partial" if isinstance(within30, int) and within30 >= n_total // 2
                      else "❌ Poor")
            summary_rows.append({
                "ID": eid, "Event": ev["name"],
                "Direction OK": f"{dir_ok}/{n_total}" if dir_ok != "—" else "—",
                "Within ±30%": f"{within30}/{n_total}" if within30 != "—" else "—",
                "Mean |Error %|": mean_err,
                "Status": status,
            })
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

        # Error % bar chart
        fig_err = go.Figure()
        for ev in HISTORICAL_EVENTS:
            eid = ev["id"]
            if eid not in val_data or "error" in val_data[eid]:
                continue
            df = val_data[eid]["cmp"]
            if "Error_%" not in df.columns:
                continue
            for _, row in df.iterrows():
                err = row["Error_%"]
                fig_err.add_trace(go.Bar(
                    x=[f"{eid}: {str(row['Observable'])[:30]}"],
                    y=[abs(err) if isinstance(err, (int, float)) else 0],
                    marker_color="#2a9d8f" if abs(err) < 30 else "#e9c46a" if abs(err) < 60 else "#e63946",
                    showlegend=False,
                    text=[f"{err:.0f}%" if isinstance(err, (int, float)) else str(err)],
                    textposition="outside",
                ))
        fig_err.add_hline(y=30, line_dash="dot", line_color="#e9c46a",
                          annotation_text="±30% tolerance", annotation_font_color="#e9c46a")
        fig_err.update_layout(height=400, template=DARK, barmode="stack",
                              title="Absolute Error % by Event × Metric",
                              yaxis_title="|Error %|",
                              xaxis_tickangle=-35, margin=dict(b=120))
        st.plotly_chart(fig_err, use_container_width=True)

    else:
        st.info("Click **▶ Run All 7 Events** in the sidebar to run the model validation.")
        # Static event overview
        overview = [{"ID": e["id"], "Name": e["name"],
                     "Shock type": e.get("shock_type", "—"),
                     "Sigma override": "✓" if e.get("sigma_override") else "—",
                     "Metrics": len(e.get("observed", {}))}
                    for e in HISTORICAL_EVENTS]
        st.dataframe(pd.DataFrame(overview), use_container_width=True, hide_index=True)

    # ── Per-event detail ──────────────────────────────────────────────────────
    st.divider()
    st.subheader(f"Event Detail — {val_event_sel}")

    if val_data and val_event_sel in val_data:
        entry = val_data[val_event_sel]
        ev_obj = entry["event"]

        if "error" in entry:
            st.error(f"Error running {val_event_sel}: {entry['error']}")
        else:
            df = entry["cmp"]
            res = entry["result"]

            # Colour Direction_OK and Error_%
            def _style_row(row):
                styles = [""] * len(row)
                if "Direction_OK" in row.index:
                    styles[list(row.index).index("Direction_OK")] = (
                        "color: #2a9d8f" if row["Direction_OK"] else "color: #e63946"
                    )
                if "Error_%" in row.index:
                    err = row["Error_%"]
                    if isinstance(err, (int, float)):
                        idx = list(row.index).index("Error_%")
                        styles[idx] = (
                            "color: #2a9d8f" if abs(err) < 30
                            else "color: #e9c46a" if abs(err) < 60
                            else "color: #e63946"
                        )
                return styles

            st.dataframe(
                df.style.apply(_style_row, axis=1),
                use_container_width=True, hide_index=True,
            )

            # CGE price bar for this event
            # run_validation_event returns cge_price_pct (already in % form)
            pct = list(res.get("cge_price_pct", np.zeros(8)))
            fig_ev = go.Figure(go.Bar(
                x=[SECTOR_SHORT.get(s, s) for s in SECTORS], y=pct,
                marker_color=["#e63946" if v > 5 else "#e9c46a" if v > 0 else "#2a9d8f"
                              for v in pct],
                text=[f"{v:+.1f}%" for v in pct], textposition="outside",
            ))
            # Mark sigma-override sectors
            if ev_obj.get("sigma_override"):
                y_ann = max(pct) * 0.7 if max(pct) > 0 else 5.0
                for sec, sigma in ev_obj["sigma_override"].items():
                    if sec in SECTORS:
                        fig_ev.add_annotation(
                            x=SECTOR_SHORT.get(sec, sec),
                            y=y_ann,
                            text=f"σ={sigma}",
                            showarrow=False,
                            font=dict(color="#e9c46a", size=10),
                        )
            fig_ev.update_layout(
                height=320, template=DARK,
                title=f"{val_event_sel} — CGE equilibrium price changes",
                yaxis_title="% vs baseline",
            )
            st.plotly_chart(fig_ev, use_container_width=True)

            # ABM metrics
            bw = res.get("abm_bullwhip")
            sl = res.get("abm_service")
            rt = res.get("abm_recovery")
            if bw is not None and sl is not None:
                m1, m2, m3 = st.columns(3)
                m1.markdown("**Bullwhip Ratios**")
                m1.dataframe(bw, use_container_width=True, hide_index=True, height=200)
                m2.markdown("**Service Levels**")
                m2.dataframe(sl, use_container_width=True, hide_index=True, height=200)
                if rt is not None:
                    m3.markdown("**Recovery Weeks**")
                    m3.dataframe(rt, use_container_width=True, hide_index=True, height=200)
    elif val_data:
        st.info(f"Select an event in the sidebar after running the validation suite.")
    else:
        ev_obj = next((e for e in HISTORICAL_EVENTS if e["id"] == val_event_sel), None)
        if ev_obj:
            st.markdown(f"**{ev_obj['name']}**")
            if ev_obj.get("sigma_override"):
                st.info(
                    f"This event uses Armington σ overrides: "
                    + ", ".join(f"{k}=σ{v}" for k, v in ev_obj["sigma_override"].items())
                )
            obs = ev_obj.get("observed", {})
            if obs:
                obs_rows = [{"Metric": k, "Observed": str(v.get("value","")) + (
                    f" ({v.get('note','')})" if v.get("note") else "")}
                    for k, v in obs.items() if isinstance(v, dict) and "value" in v]
                if obs_rows:
                    st.dataframe(pd.DataFrame(obs_rows), use_container_width=True,
                                 hide_index=True)

    # ── HMRC benchmarks (always visible) ─────────────────────────────────────
    st.divider()
    st.subheader("HMRC OTS Benchmark Data")
    st.caption("Direct observed values from HMRC OTS API — 2026-04-17")

    from real_data import HMRC_VALIDATION_BENCHMARKS as VB
    bench = [
        {"Event":"V1 COVID-19 (2020)","Metric":"China import value",
         "HMRC":f"{VB['V1_COVID_china_value_pct']:+.1f}%","Category":"Volume shock",
         "Note":"Factory shutdowns Q1 2020"},
        {"Event":"V1 COVID-19 (2020)","Metric":"Total UK synthetic apparel",
         "HMRC":f"{VB['V1_COVID_total_value_pct']:+.1f}%","Category":"Volume shock","Note":"2019→2020"},
        {"Event":"V5 Red Sea (Jan 2024)","Metric":"NON-EU imports",
         "HMRC":f"{VB['V5_RedSea_jan_value_pct']:+.1f}%","Category":"Shipping","Note":"vs Jan 2023"},
        {"Event":"V5 Red Sea (Feb 2024)","Metric":"NON-EU imports",
         "HMRC":f"{VB['V5_RedSea_feb_value_pct']:+.1f}%","Category":"Shipping","Note":"vs Feb 2023"},
        {"Event":"V5 Red Sea (Mar 2024)","Metric":"NON-EU imports",
         "HMRC":f"{VB['V5_RedSea_mar_value_pct']:+.1f}%","Category":"Shipping","Note":"vs Mar 2023"},
        {"Event":"V5 Red Sea (H1 2024)","Metric":"NON-EU H1",
         "HMRC":f"{VB['V5_RedSea_H1_value_pct']:+.1f}%","Category":"Shipping","Note":"H1 2024 vs H1 2023"},
        {"Event":"V6 Shanghai (2022 Q2)","Metric":"China import value",
         "HMRC":f"{VB['V6_Shanghai_Q2_china_value_pct']:+.1f}%","Category":"Price/energy",
         "Note":"Price-driven; energy crisis dominated"},
        {"Event":"V7 Ukraine (2022)","Metric":"Annual import value",
         "HMRC":f"{VB['V7_Ukraine_annual_value_pct']:+.1f}%","Category":"Price shock","Note":"2022 vs 2021"},
    ]
    st.dataframe(pd.DataFrame(bench), use_container_width=True, hide_index=True, height=300)

    st.divider()
    annual = _annual()
    totals = annual.groupby("Year")["Value"].sum().reset_index()
    totals["YoY_%"] = totals["Value"].pct_change() * 100

    fig_yoy = go.Figure(go.Bar(
        x=totals["Year"], y=totals["YoY_%"].fillna(0),
        marker_color=["#e63946" if v < 0 else "#2a9d8f" for v in totals["YoY_%"].fillna(0)],
        text=[f"{v:.1f}%" for v in totals["YoY_%"].fillna(0)],
        textposition="outside", textfont=dict(size=8),
    ))
    for yr, lbl in [(2008,"GFC"),(2016,"Brexit"),(2020,"COVID"),(2022,"Ukraine"),(2024,"Red Sea")]:
        fig_yoy.add_vline(x=yr, line_dash="dot", line_color="#475569",
                         annotation_text=lbl, annotation_font_size=9,
                         annotation_font_color="#94a3b8", annotation_position="top")
    fig_yoy.update_layout(height=360, template=DARK,
                         title="YoY Change — UK Synthetic Apparel Imports (%)",
                         yaxis_title="% YoY")
    st.plotly_chart(fig_yoy, use_container_width=True)

    dq1, dq2 = st.columns([1, 2])
    with dq1:
        st.subheader("Data Quality (208 params)")
        dq = pd.DataFrame({"Category": ["REAL","DERIVED","ESTIMATED","EXTERNAL","ASSUMED"],
                           "Count": [77, 42, 61, 13, 15]})
        dq["Share%"] = (dq["Count"] / 208 * 100).round(1)
        st.dataframe(dq, use_container_width=True, hide_index=True)
    with dq2:
        fig_dq = go.Figure(go.Pie(
            labels=dq["Category"], values=dq["Count"], hole=0.4,
            marker_colors=["#2a9d8f","#457b9d","#e9c46a","#264653","#e63946"],
            textinfo="label+percent",
        ))
        fig_dq.update_layout(height=280, template=DARK, showlegend=False,
                            margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_dq, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# FIGURE GALLERY
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🖼️ Figure Gallery":
    st.title("Figure Gallery")
    st.caption("Static publication-quality figures generated by visualise.py")

    col_run, col_info = st.columns([1,3])
    with col_run:
        gen_btn = st.button("⚙️ Generate All 49 Figures", type="primary",
                           help="Runs visualise.py — takes ~60 seconds")
    with col_info:
        existing = list(FIG_DIR.glob("*.png")) if FIG_DIR.exists() else []
        st.info(f"**{len(existing)} figures** currently in `results/figures/`")

    if gen_btn:
        prog = st.progress(0, text="Running visualise.py pipeline…")
        placeholder = st.empty()
        try:
            proc = subprocess.Popen(
                [sys.executable, str(Path(__file__).parent / "visualise.py")],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace",
                cwd=str(Path(__file__).parent),
            )
            lines = []
            for line in proc.stdout:
                lines.append(line.rstrip())
                placeholder.code("\n".join(lines[-20:]))
                if "fig" in line.lower():
                    done = sum(1 for l in lines if "png" in l)
                    prog.progress(min(done/49, 0.99), text=f"Generated {done}/49 figures…")
            proc.wait()
            prog.progress(1.0, text="Done.")
            if proc.returncode == 0:
                st.success("All figures generated successfully.")
            else:
                st.error(f"Pipeline exited with code {proc.returncode}.")
        except Exception as e:
            st.error(f"Error running pipeline: {e}")

    # ── Gallery viewer ────────────────────────────────────────────────────────
    FIGURE_GROUPS = {
        "Supply Chain Overview": [
            ("fig00_supply_chain_geography.png", "Geographic supply chain flow"),
            ("fig01_supply_chain_network.png",   "I-O network / China dependency"),
            ("fig02_concentration_vulnerability.png","Concentration & vulnerability"),
        ],
        "HMRC Import Data": [
            ("fig04_hmrc_import_trends.png",     "Annual import trends 2002-2024"),
            ("fig05_hmrc_country_breakdown.png", "Country breakdown & unit prices"),
            ("fig06_hmrc_seasonal_pattern.png",  "Monthly seasonal demand pattern"),
            ("fig07_hmrc_validation_events.png", "HMRC validation benchmarks"),
        ],
        "MRIO Analysis": [
            ("fig08_mrio_va_heatmap.png",        "Value-added heatmap (region × sector)"),
            ("fig09_mrio_china_exposure.png",    "China exposure by stage"),
            ("fig10_mrio_china_shock.png",       "MRIO China supply shock"),
        ],
        "Ghosh Supply-Push": [
            ("fig11_ghosh_linkage_quadrant.png", "Forward vs backward linkage quadrant"),
            ("fig12_ghosh_scenarios.png",        "Ghosh scenario comparison"),
            ("fig13_ghosh_mrio_shock.png",       "Ghosh-MRIO combined shock"),
        ],
        "Scenario S1 — PTA Shock": [
            ("fig14_S1_io_output.png",  "I-O output path"),
            ("fig15_S1_cge_prices.png", "CGE price changes"),
            ("fig16_S1_abm_dynamics.png","ABM inventory dynamics"),
        ],
        "Scenario S2 — MEG Disruption": [
            ("fig14_S2_io_output.png",  "I-O output path"),
            ("fig15_S2_cge_prices.png", "CGE price changes"),
            ("fig16_S2_abm_dynamics.png","ABM inventory dynamics"),
        ],
        "Scenario S3 — UK-China Tariff": [
            ("fig14_S3_io_output.png",  "I-O output path"),
            ("fig15_S3_cge_prices.png", "CGE price changes"),
            ("fig16_S3_abm_dynamics.png","ABM inventory dynamics"),
        ],
        "Scenario S4 — Port Closure": [
            ("fig14_S4_io_output.png",  "I-O output path"),
            ("fig15_S4_cge_prices.png", "CGE price changes"),
            ("fig16_S4_abm_dynamics.png","ABM inventory dynamics"),
        ],
        "Scenario S5 — Pandemic": [
            ("fig14_S5_io_output.png",  "I-O output path"),
            ("fig15_S5_cge_prices.png", "CGE price changes"),
            ("fig16_S5_abm_dynamics.png","ABM inventory dynamics"),
        ],
        "Cross-Scenario Comparison": [
            ("fig17_scenario_comparison.png","Scenario comparison"),
            ("fig18_recovery_time.png",      "Recovery time analysis"),
        ],
    }

    if FIG_DIR.exists():
        for group, figures in FIGURE_GROUPS.items():
            available = [(fn,cap) for fn,cap in figures if (FIG_DIR/fn).exists()]
            if not available:
                continue
            with st.expander(f"**{group}** ({len(available)}/{len(figures)} figures)", expanded=False):
                ncols = min(len(available), 3)
                cols  = st.columns(ncols)
                for j,(fn,cap) in enumerate(available):
                    cols[j % ncols].image(str(FIG_DIR/fn), caption=cap,
                                         use_container_width=True)
    else:
        st.warning("No figures found. Click **Generate All 49 Figures** to create them.")
