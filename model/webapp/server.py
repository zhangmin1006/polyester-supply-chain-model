"""
server.py  —  Polyester Supply Chain Web Application
Flask backend serving the full IO × CGE × ABM × MRIO × Ghosh model.

Run:
    cd model/webapp
    python server.py
    → http://localhost:5000
"""

import sys, os, json, threading, subprocess, math
from pathlib import Path
from functools import lru_cache

# Ensure model directory is importable
MODEL_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(MODEL_DIR))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from flask import Flask, render_template, jsonify, request, send_from_directory, abort

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

DATA_DIR = MODEL_DIR / "data"
FIG_DIR  = MODEL_DIR / "results" / "figures"

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
HMRC_SEASONAL = [0.993,0.909,1.026,0.941,0.963,0.963,1.052,1.062,1.099,1.145,0.977,0.871]
MONTHS        = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
DARK          = "plotly_white"
SCENARIO_NAMES = {
    "S1":"PTA Production Shock",
    "S2":"MEG Supply Disruption",
    "S3":"UK–China Trade Restriction",
    "S4":"Zhangjiagang Port Closure",
    "S5":"Multi-Node Pandemic Shock",
}

# ── Thread-safe lazy model instances ──────────────────────────────────────────
_lock      = threading.Lock()
_instances = {}

def _get(name, factory):
    if name not in _instances:
        with _lock:
            if name not in _instances:
                _instances[name] = factory()
    return _instances[name]

def get_model():
    from integrated_model import IntegratedSupplyChainModel
    return _get("model", IntegratedSupplyChainModel)

def get_mrio():
    from mrio_model import MRIOModel
    return _get("mrio", MRIOModel)

def get_ghosh():
    from ghosh_model import GhoshModel
    return _get("ghosh", GhoshModel)

# ── Cached CSV loading ─────────────────────────────────────────────────────────
@lru_cache(maxsize=None)
def _annual():  return pd.read_csv(DATA_DIR / "hmrc_annual_country.csv")
@lru_cache(maxsize=None)
def _monthly(): return pd.read_csv(DATA_DIR / "hmrc_monthly_country.csv")
@lru_cache(maxsize=None)
def _eu_nn():   return pd.read_csv(DATA_DIR / "hmrc_monthly_eu_noneu.csv")

# ── Plotly helpers ─────────────────────────────────────────────────────────────
def _fig_json(fig):
    """Serialize Plotly figure to JSON-serialisable dict."""
    return json.loads(fig.to_json())

def _clean_records(df):
    """Convert DataFrame to JSON-safe list of dicts — NaN/inf become None."""
    def _safe(v):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        if hasattr(v, "item"):          # numpy scalar
            v = v.item()
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                return None
        return v
    return [{k: _safe(v) for k, v in row.items()} for row in df.to_dict(orient="records")]

def _layout(**kw):
    return dict(template=DARK, margin=dict(l=10,r=10,t=40,b=10),
                font=dict(family="Inter,sans-serif"), **kw)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def home():
    annual = _annual()
    latest = int(annual["Year"].max())
    tot    = annual[annual["Year"]==latest]["Value"].sum()
    china  = annual[(annual["Year"]==latest)&(annual["Country"]=="China")]["Value"].sum()
    prev   = annual[annual["Year"]==latest-1]["Value"].sum()
    return render_template("home.html",
        total_imports=f"£{tot/1e9:.2f}bn",
        china_share=f"{china/tot*100:.1f}%",
        yoy=f"{(tot-prev)/prev*100:+.1f}%",
        latest_year=latest,
    )

@app.route("/market")
def market():
    annual = _annual()
    latest = int(annual["Year"].max())
    countries = sorted(annual["Country"].unique().tolist())
    years     = sorted(annual["Year"].unique().tolist())
    return render_template("market.html",
        latest_year=latest, countries=countries, years=years,
    )

@app.route("/structure")
def structure():
    return render_template("structure.html", figdir="/figures")

@app.route("/baseline")
def baseline():
    return render_template("baseline.html", sectors=SECTORS, sector_short=SECTOR_SHORT)

@app.route("/mrio")
def mrio_page():
    from mrio_model import REGIONS, REGION_LABELS
    return render_template("mrio.html",
        regions=REGIONS, region_labels=REGION_LABELS,
        sectors=SECTORS, sector_short=SECTOR_SHORT,
    )

@app.route("/ghosh")
def ghosh_page():
    from ghosh_model import GHOSH_SCENARIOS
    return render_template("ghosh.html",
        ghosh_scenarios=GHOSH_SCENARIOS, sectors=SECTORS, sector_short=SECTOR_SHORT,
    )

@app.route("/scenarios")
def scenarios():
    from shocks import ALL_SCENARIOS
    sc_list = [{"key":k,"name":SCENARIO_NAMES[k],
                "onset":v.onset_week,"duration":v.duration_weeks,
                "desc":v.description[:120]+"…"}
               for k,v in ALL_SCENARIOS.items()]
    return render_template("scenarios.html", scenarios=sc_list)

@app.route("/gallery")
def gallery():
    groups = {
        "Supply Chain Overview": [
            ("fig00_supply_chain_geography.png","Geographic supply chain flow"),
            ("fig01_supply_chain_network.png","I-O network / China dependency"),
            ("fig02_concentration_vulnerability.png","Concentration & vulnerability"),
            ("fig03_resilience_scorecard.png","Resilience scorecard"),
        ],
        "HMRC Import Data": [
            ("fig04_hmrc_import_trends.png","Annual import trends 2002-2024"),
            ("fig05_hmrc_country_breakdown.png","Country breakdown & unit prices"),
            ("fig06_hmrc_seasonal_pattern.png","Monthly seasonal demand pattern"),
            ("fig07_hmrc_validation_events.png","HMRC validation benchmarks"),
        ],
        "MRIO Analysis": [
            ("fig08_mrio_va_heatmap.png","Value-added heatmap"),
            ("fig09_mrio_china_exposure.png","China exposure by stage"),
            ("fig10_mrio_china_shock.png","MRIO China supply shock"),
        ],
        "Ghosh Supply-Push": [
            ("fig11_ghosh_linkage_quadrant.png","Forward vs backward linkage"),
            ("fig12_ghosh_scenarios.png","Ghosh scenario comparison"),
            ("fig13_ghosh_mrio_shock.png","Ghosh-MRIO combined shock"),
        ],
        "Scenario Results": [
            (f"fig{fn}_{sc}_{suf}.png", f"S{sc[-1]} {label}")
            for fn,suf,label in [("14","io_output","I-O output"),
                                  ("15","cge_prices","CGE prices"),
                                  ("16","abm_dynamics","ABM dynamics")]
            for sc in ["S1","S2","S3","S4","S5"]
        ],
        "Cross-Scenario Comparison": [
            ("fig17_scenario_comparison.png","Scenario comparison"),
            ("fig18_recovery_time.png","Recovery time analysis"),
        ],
    }
    # Mark which files exist
    avail = {fn: (FIG_DIR/fn).exists() for g in groups.values() for fn,_ in g}
    return render_template("gallery.html", groups=groups, avail=avail,
                          total=sum(avail.values()))


# ══════════════════════════════════════════════════════════════════════════════
# API — HMRC DATA CHARTS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/hmrc/kpis")
def api_hmrc_kpis():
    annual = _annual()
    eu_nn  = _eu_nn()
    latest = int(annual["Year"].max())
    prev   = latest - 1
    tot_l  = annual[annual["Year"]==latest]["Value"].sum()
    tot_p  = annual[annual["Year"]==prev]["Value"].sum()
    china  = annual[(annual["Year"]==latest)&(annual["Country"]=="China")]["Value"].sum()
    noneu_l = eu_nn[(eu_nn["Year"]==latest)&(eu_nn["Flow"]=="NON-EU")]["Value"].sum()
    noneu_p = eu_nn[(eu_nn["Year"]==prev)  &(eu_nn["Flow"]=="NON-EU")]["Value"].sum()
    return jsonify({
        "total":   f"£{tot_l/1e9:.2f}bn",
        "yoy":     f"{(tot_l-tot_p)/tot_p*100:+.1f}%",
        "china":   f"{china/tot_l*100:.1f}%",
        "noneu":   f"£{noneu_l/1e9:.2f}bn",
        "noneu_yoy": f"{(noneu_l-noneu_p)/noneu_p*100:+.1f}%",
        "year":    latest,
    })

@app.route("/api/hmrc/trends")
def api_hmrc_trends():
    annual = _annual()
    top7   = annual.groupby("Country")["Value"].sum().nlargest(7).index.tolist()
    fig    = go.Figure()
    for yr,lbl in [(2008,"GFC"),(2016,"Brexit"),(2020,"COVID"),(2022,"Ukraine"),(2024,"Red Sea")]:
        fig.add_vline(x=yr, line_dash="dot", line_color="#475569", line_width=1,
                     annotation_text=lbl, annotation_font_size=9,
                     annotation_font_color="#94a3b8")
    for c in top7:
        d = annual[annual["Country"]==c].sort_values("Year")
        fig.add_trace(go.Scatter(
            x=d["Year"].tolist(), y=(d["Value"]/1e6).tolist(),
            name=c.replace("_"," "),
            line=dict(color=COUNTRY_COLORS.get(c,"#adb5bd"),width=2),
            mode="lines+markers", marker=dict(size=4),
        ))
    fig.update_layout(**_layout(yaxis_title="£ million", hovermode="x unified",
                                legend=dict(orientation="h",y=-0.18), height=420))
    return jsonify(_fig_json(fig))

@app.route("/api/hmrc/yoy")
def api_hmrc_yoy():
    annual = _annual()
    totals = annual.groupby("Year")["Value"].sum().reset_index()
    totals["YoY_%"] = totals["Value"].pct_change()*100
    fig = go.Figure(go.Bar(
        x=totals["Year"].tolist(), y=totals["YoY_%"].fillna(0).tolist(),
        marker_color=["#e63946" if v<0 else "#2a9d8f" for v in totals["YoY_%"].fillna(0)],
        text=[f"{v:.1f}%" for v in totals["YoY_%"].fillna(0)],
        textposition="outside", textfont=dict(size=9),
    ))
    for yr,lbl in [(2008,"GFC"),(2016,"Brexit"),(2020,"COVID"),(2022,"Ukraine"),(2024,"Red Sea")]:
        fig.add_vline(x=yr, line_dash="dot", line_color="#475569",
                     annotation_text=lbl, annotation_font_size=9,
                     annotation_font_color="#94a3b8", annotation_position="top")
    fig.update_layout(**_layout(yaxis_title="YoY %", height=320))
    return jsonify(_fig_json(fig))

@app.route("/api/hmrc/pie/<int:year>")
def api_hmrc_pie(year):
    annual = _annual()
    yd     = annual[annual["Year"]==year].sort_values("Value",ascending=False)
    tot    = yd["Value"].sum()
    top8   = yd.head(8)
    other  = tot - top8["Value"].sum()
    pie_df = pd.concat([top8[["Country","Value"]],
                        pd.DataFrame([{"Country":"Other","Value":other}])],
                       ignore_index=True)
    fig = go.Figure(go.Pie(
        labels=pie_df["Country"].str.replace("_"," ").tolist(),
        values=pie_df["Value"].tolist(), hole=0.44,
        marker=dict(colors=[COUNTRY_COLORS.get(c,"#adb5bd") for c in pie_df["Country"]]),
        textinfo="label+percent", textfont_size=11,
    ))
    fig.update_layout(**_layout(showlegend=False, height=380,
        annotations=[dict(text=f"<b>{year}</b>",x=0.5,y=0.5,
                          showarrow=False,font=dict(size=20,color="white"))]))
    return jsonify(_fig_json(fig))

@app.route("/api/hmrc/seasonal")
def api_hmrc_seasonal():
    fig = go.Figure(go.Bar(
        x=MONTHS, y=HMRC_SEASONAL,
        marker_color=["#e63946" if v==max(HMRC_SEASONAL) else
                      "#2a9d8f" if v==min(HMRC_SEASONAL) else "#457b9d"
                      for v in HMRC_SEASONAL],
        text=[f"{v:.3f}" for v in HMRC_SEASONAL], textposition="outside",
    ))
    fig.add_hline(y=1.0, line_dash="dash", line_color="#94a3b8", line_width=1,
                 annotation_text="Mean=1.0", annotation_font_color="#94a3b8")
    fig.update_layout(**_layout(yaxis_title="Seasonal factor", yaxis_range=[0.8,1.25],
                                height=320))
    return jsonify(_fig_json(fig))

@app.route("/api/hmrc/eu_noneu")
def api_hmrc_eu_noneu():
    eu_nn = _eu_nn()
    eu_nn = eu_nn.copy()
    eu_nn["Date"] = pd.to_datetime(eu_nn[["Year","Month"]].assign(day=1))
    eu_nn["DateStr"] = eu_nn["Date"].dt.strftime("%Y-%m-%d")
    fig = go.Figure()
    for flow, color, fc in [("EU","#457b9d","rgba(69,123,157,0.15)"),
                             ("NON-EU","#e63946","rgba(230,57,70,0.15)")]:
        d = eu_nn[eu_nn["Flow"]==flow].sort_values("Date")
        fig.add_trace(go.Scatter(
            x=d["DateStr"].tolist(), y=(d["Value"]/1e6).tolist(),
            name=flow, fill="tozeroy", line=dict(color=color,width=1.5),
            fillcolor=fc,
        ))
    fig.update_layout(**_layout(yaxis_title="£ million", hovermode="x unified",
                                height=300))
    return jsonify(_fig_json(fig))

@app.route("/api/hmrc/unitprice")
def api_hmrc_unitprice():
    annual = _annual()
    countries = request.args.getlist("c") or ["China","Bangladesh","Turkey","India"]
    d = annual[annual["Country"].isin(countries) & annual["UnitPrice_GBP_per_kg"].notna()]
    fig = go.Figure()
    for c in countries:
        dc = d[d["Country"]==c].sort_values("Year")
        if len(dc):
            fig.add_trace(go.Scatter(
                x=dc["Year"].tolist(), y=dc["UnitPrice_GBP_per_kg"].tolist(),
                name=c.replace("_"," "),
                line=dict(color=COUNTRY_COLORS.get(c,"#adb5bd"),width=2),
                mode="lines+markers",
            ))
    fig.update_layout(**_layout(yaxis_title="£/kg", hovermode="x unified",
                                height=320))
    return jsonify(_fig_json(fig))


# ══════════════════════════════════════════════════════════════════════════════
# API — BASELINE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/baseline/hhi")
def api_baseline_hhi():
    model    = get_model()
    baseline = model.baseline_report()
    hhi      = baseline["hhi"]
    h = hhi.sort_values("HHI", ascending=True)
    fig = go.Figure(go.Bar(
        x=h["HHI"].tolist(), y=h["Sector"].tolist(), orientation="h",
        marker_color=["#e63946" if v>0.25 else "#e9c46a" if v>0.15 else "#2a9d8f"
                      for v in h["HHI"]],
        text=[f"{v:.3f}" for v in h["HHI"]], textposition="outside",
    ))
    fig.add_vline(x=0.25, line_dash="dash", line_color="#e63946",
                 annotation_text="High >0.25", annotation_font_color="#e63946",
                 annotation_font_size=9)
    fig.add_vline(x=0.15, line_dash="dash", line_color="#e9c46a",
                 annotation_text="Moderate", annotation_font_color="#e9c46a",
                 annotation_font_size=9)
    fig.update_layout(**_layout(title="Supplier Concentration (HHI)", height=380))
    return jsonify({"figure": _fig_json(fig),
                    "table": hhi.to_dict(orient="records")})

@app.route("/api/baseline/china")
def api_baseline_china():
    model    = get_model()
    baseline = model.baseline_report()
    eff      = baseline["eff_china"]
    if not isinstance(eff, pd.DataFrame):
        return jsonify({"error": "no data"})
    ec = eff.sort_values("Effective_China_%", ascending=True)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ec["Nominal_China_%"].tolist(), y=ec["Sector"].tolist(),
                        orientation="h", name="Nominal (HMRC)", marker_color="#457b9d", opacity=0.7))
    fig.add_trace(go.Bar(x=ec["Effective_China_%"].tolist(), y=ec["Sector"].tolist(),
                        orientation="h", name="Effective (upstream-traced)",
                        marker_color="#e63946", opacity=0.85))
    fig.add_vline(x=27.3, line_dash="dot", line_color="#94a3b8",
                 annotation_text="HMRC direct 27.3%",
                 annotation_font_color="#94a3b8", annotation_font_size=9)
    fig.update_layout(**_layout(barmode="overlay", height=380,
                                xaxis_title="China dependency %",
                                title="Nominal vs Effective China Dependency",
                                legend=dict(orientation="h",y=-0.15)))
    return jsonify({"figure": _fig_json(fig),
                    "table": eff.to_dict(orient="records")})

@app.route("/api/baseline/scorecard")
def api_baseline_scorecard():
    model    = get_model()
    baseline = model.baseline_report()
    sc       = baseline["scorecard"]
    if not isinstance(sc, pd.DataFrame):
        return jsonify({"error": "no data"})
    cats = ["HHI_Score","Redundancy_Score","Substitution_Score","Buffer_Score","China_Dep_Score"]
    fig  = go.Figure()
    colors = ["#e63946","#f4a261","#e9c46a","#2a9d8f","#457b9d","#264653","#7b1fa2","#adb5bd"]
    for i, (_, row) in enumerate(sc.iterrows()):
        vals = [row.get(c,0) for c in cats] + [row.get(cats[0],0)]
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=cats+[cats[0]],
            name=SECTOR_SHORT.get(row["Sector"],row["Sector"]),
            fill="toself", opacity=0.55,
            line=dict(color=colors[i % len(colors)]),
        ))
    fig.update_layout(**_layout(
        title="Resilience Scorecard — Radar",
        polar=dict(radialaxis=dict(range=[0,1],tickfont=dict(size=9))),
        legend=dict(orientation="h",y=-0.15), height=450,
    ))
    return jsonify({"figure": _fig_json(fig),
                    "table": sc.to_dict(orient="records")})


# ══════════════════════════════════════════════════════════════════════════════
# API — MRIO
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/mrio/va")
def api_mrio_va():
    from mrio_model import REGION_LABELS
    mrio   = get_mrio()
    detail, summary = mrio.value_added_decomposition()
    pivot  = detail.pivot_table(values="Value_Added_GBP",
                                index="Region_Label", columns="Sector",
                                aggfunc="sum", fill_value=0)
    fig_hm = px.imshow(pivot/1e9, template=DARK, height=400,
                       color_continuous_scale="Blues",
                       labels={"color":"VA £bn"},
                       text_auto=".2f")
    fig_hm.update_xaxes(tickangle=-40)
    fig_hm.update_layout(**_layout(title="Value-Added by Region × Sector (£bn)"))
    fig_pie = go.Figure(go.Pie(
        labels=summary["Region_Label"].tolist(),
        values=summary["VA_GBP_bn"].tolist(), hole=0.42,
        textinfo="label+percent",
        marker=dict(colors=["#e63946","#2a9d8f","#457b9d","#f4a261",
                            "#264653","#7b1fa2","#1b5e20","#adb5bd"]),
    ))
    fig_pie.update_layout(**_layout(showlegend=False, height=380,
                                    title="VA Share by Region"))
    return jsonify({
        "heatmap": _fig_json(fig_hm),
        "pie":     _fig_json(fig_pie),
        "summary": summary[["Region_Label","VA_GBP_bn","VA_Share_%"]].to_dict(orient="records"),
    })

@app.route("/api/mrio/china")
def api_mrio_china():
    mrio = get_mrio()
    exp  = mrio.effective_china_exposure()
    val_col = "MRIO_China_%" if "MRIO_China_%" in exp.columns else "Effective_China_%"
    fig = px.bar(exp.sort_values(val_col, ascending=False),
                x="Sector", y=val_col,
                color=val_col, color_continuous_scale="Reds",
                template=DARK, height=360,
                title="MRIO China Exposure by Stage (%)")
    fig.update_layout(**_layout(xaxis_tickangle=-40, coloraxis_showscale=False))
    return jsonify({"figure": _fig_json(fig),
                    "table": exp.to_dict(orient="records")})

@app.route("/api/mrio/shock", methods=["POST"])
def api_mrio_shock():
    data          = request.json
    shock_region  = data.get("region", "CHN")
    shock_sector  = data.get("sector", "PTA_Production")
    severity_pct  = float(data.get("severity", 50))

    mrio = get_mrio()
    from mrio_model import REGION_IDX, SECTOR_IDX, REGION_LABELS
    from numpy.linalg import inv

    x_base    = mrio.gross_output()
    A_shocked = mrio.A_mrio.copy()
    r_idx     = REGION_IDX[shock_region]
    s_idx     = SECTOR_IDX[shock_sector]
    A_shocked[r_idx*8+s_idx, :] *= (1 - severity_pct/100)
    L_sh = inv(np.eye(A_shocked.shape[0]) - A_shocked)
    x_sh = L_sh @ mrio.uk_final_demand()

    rows = []
    for si, sec in enumerate(SECTORS):
        base = sum(x_base[ri*8+si] for ri in range(8))
        shk  = sum(x_sh[ri*8+si]  for ri in range(8))
        rows.append({"Sector":SECTOR_SHORT.get(sec,sec),
                     "Baseline":round(base,2),"Shocked":round(shk,2),
                     "Change_%":round((shk-base)/(base+1e-12)*100,2)})
    df = pd.DataFrame(rows)

    fig = make_subplots(rows=1, cols=2, subplot_titles=["Output Comparison","% Change"])
    fig.add_trace(go.Bar(x=df["Sector"].tolist(), y=df["Baseline"].tolist(),
                        name="Baseline", marker_color="#457b9d"), row=1, col=1)
    fig.add_trace(go.Bar(x=df["Sector"].tolist(), y=df["Shocked"].tolist(),
                        name="Shocked", marker_color="#e63946"), row=1, col=1)
    fig.add_trace(go.Bar(
        x=df["Sector"].tolist(), y=df["Change_%"].tolist(),
        marker_color=["#e63946" if v<0 else "#2a9d8f" for v in df["Change_%"]],
        showlegend=False,
    ), row=1, col=2)
    fig.update_layout(**_layout(
        barmode="group", height=380,
        title=f"MRIO Shock: {REGION_LABELS.get(shock_region,shock_region)} "
              f"{SECTOR_SHORT.get(shock_sector,shock_sector)} −{severity_pct:.0f}%",
    ))
    return jsonify({"figure": _fig_json(fig), "table": df.to_dict(orient="records")})


# ══════════════════════════════════════════════════════════════════════════════
# API — GHOSH
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/ghosh/linkages")
def api_ghosh_linkages():
    ghosh = get_ghosh()
    fl    = ghosh.forward_linkages()
    fig   = go.Figure(go.Bar(
        x=fl["FL_Ghosh_Norm"].tolist(),
        y=fl.sort_values("FL_Ghosh_Norm",ascending=True)["Sector"].tolist(),
        orientation="h",
        marker_color=["#e63946" if v else "#457b9d" for v in
                      fl.sort_values("FL_Ghosh_Norm",ascending=True)["Supply_Critical"]],
        text=[f"{v:.2f}" for v in fl.sort_values("FL_Ghosh_Norm",ascending=True)["FL_Ghosh_Norm"]],
        textposition="outside",
    ))
    fig.add_vline(x=1.0, line_dash="dash", line_color="#94a3b8",
                 annotation_text="Mean=1.0")
    fig.update_layout(**_layout(title="Ghosh Forward Linkage (normalised)", height=360))
    return jsonify({"figure": _fig_json(fig),
                    "table": fl.to_dict(orient="records")})

@app.route("/api/ghosh/quadrant")
def api_ghosh_quadrant():
    ghosh = get_ghosh()
    lv    = ghosh.leontief_vs_ghosh_linkages()
    fig   = px.scatter(lv, x="BL_Norm", y="FL_Norm", text="Sector",
                       color="Key_Sector",
                       color_discrete_map={True:"#e63946",False:"#457b9d"},
                       template=DARK, height=480,
                       title="Leontief vs Ghosh — 4-Quadrant Map",
                       labels={"BL_Norm":"Backward Linkage (demand-pull)",
                               "FL_Norm":"Forward Linkage (supply-push)"})
    fig.update_traces(textposition="top center", marker=dict(size=14))
    fig.add_vline(x=1.0, line_dash="dash", line_color="#475569")
    fig.add_hline(y=1.0, line_dash="dash", line_color="#475569")
    for tx,ty,label in [(0.3,1.85,"Supply-push dominant"),(1.55,1.85,"Structurally central"),
                        (0.3,0.2,"Peripheral"),(1.55,0.2,"Demand-pull dominant")]:
        fig.add_annotation(x=tx,y=ty,text=label,showarrow=False,
                          font=dict(color="#64748b",size=10))
    fig.update_layout(**_layout())
    return jsonify({"figure": _fig_json(fig)})

@app.route("/api/ghosh/shock", methods=["POST"])
def api_ghosh_shock():
    from ghosh_model import GHOSH_SCENARIOS
    data      = request.json
    sc_key    = data.get("scenario", "GS1")
    severity  = float(data.get("severity", 50)) / 100
    ghosh     = get_ghosh()
    shocks    = {k: severity for k in GHOSH_SCENARIOS[sc_key]["shocks"]}
    res       = ghosh.supply_shock(shocks)
    pct       = res["pct_change"]
    fig = go.Figure(go.Bar(
        x=[SECTOR_SHORT.get(s,s) for s in SECTORS], y=pct.tolist(),
        marker_color=["#e63946" if v<0 else "#2a9d8f" for v in pct],
        text=[f"{v:.1f}%" for v in pct], textposition="outside",
    ))
    fig.update_layout(**_layout(
        yaxis_title="% output change",
        title=f"{sc_key}: {GHOSH_SCENARIOS[sc_key]['name'][:60]}",
        height=380,
    ))
    return jsonify({
        "figure": _fig_json(fig),
        "loss_gbp": float(res["total_output_loss_gbp"]),
        "welfare_gbp": float(res["welfare_proxy_gbp"]),
    })


# ══════════════════════════════════════════════════════════════════════════════
# API — SCENARIOS
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/scenario/run", methods=["POST"])
def api_scenario_run():
    from shocks import ALL_SCENARIOS, build_cge_supply_array, build_io_shock_schedule
    from abm_model import PolyesterSupplyChainABM
    from cge_model import CGEModel

    data      = request.json
    sc_key    = data.get("scenario", "S1")
    T         = int(data.get("weeks", 52))
    st_month  = int(data.get("start_month", 1))
    seasonal  = bool(data.get("seasonality", True))

    model    = get_model()
    scenario = ALL_SCENARIOS[sc_key]
    io_sched = build_io_shock_schedule(scenario)
    io_r     = model.io.simulate(T=T, final_demand_base=model.fd_base, shock_schedule=io_sched)
    cge_m    = CGEModel(tariff_schedule=scenario.tariffs) if scenario.tariffs else model.cge
    cge_r    = cge_m.equilibrium(supply_shocks=build_cge_supply_array(scenario),
                                 final_demand=model.fd_base)
    abm      = PolyesterSupplyChainABM(agents_per_sector=3)
    abm_r    = abm.run(T=T, baseline_demand=1.0,
                      shock_schedule=scenario.abm_schedule,
                      demand_noise=0.03*float(cge_r["equilibrium_prices"].max()),
                      start_month=st_month, apply_seasonality=seasonal)
    bw = abm.bullwhip_ratio(abm_r)
    sl = abm.service_level(abm_r)
    rt = abm.recovery_time(abm_r)
    weeks = list(range(T))
    onset = scenario.onset_week

    # IO output chart
    out = io_r["output"]
    fig_io = go.Figure()
    for i,s in enumerate(SECTORS):
        fig_io.add_trace(go.Scatter(x=weeks, y=out[:,i].tolist(),
                                   name=SECTOR_SHORT.get(s,s), mode="lines"))
    fig_io.add_vline(x=onset, line_dash="dash", line_color="#e63946",
                    annotation_text="Shock", annotation_font_color="#e63946")
    fig_io.update_layout(**_layout(yaxis_title="Output (norm.)", hovermode="x unified",
                                   legend=dict(orientation="h",y=-0.2), height=380))

    # CGE price chart
    pct = cge_r["price_index_change_pct"]
    fig_cge = go.Figure(go.Bar(
        x=[SECTOR_SHORT.get(s,s) for s in SECTORS], y=pct.tolist(),
        marker_color=["#e63946" if v>5 else "#e9c46a" if v>0 else "#2a9d8f" for v in pct],
        text=[f"{v:.1f}%" for v in pct], textposition="outside",
    ))
    fig_cge.update_layout(**_layout(yaxis_title="% vs baseline",
                                    title="CGE Price Changes", height=360))

    # ABM inventory chart
    inv  = abm_r["inventory"]
    ordr = abm_r["orders"]
    fig_abm = make_subplots(rows=2, cols=1, subplot_titles=["Inventory","Orders"],
                            shared_xaxes=True)
    for i,s in enumerate(SECTORS):
        lbl = SECTOR_SHORT.get(s,s)
        fig_abm.add_trace(go.Scatter(x=weeks, y=inv[:,i].tolist(),  name=lbl, mode="lines"),
                         row=1, col=1)
        fig_abm.add_trace(go.Scatter(x=weeks, y=ordr[:,i].tolist(), name=lbl,
                                     showlegend=False, mode="lines"), row=2, col=1)
    for fig_ in [fig_abm]:
        for r in [1,2]:
            fig_.add_vline(x=onset, line_dash="dash", line_color="#e63946", row=r, col=1)
    fig_abm.update_layout(**_layout(height=500, hovermode="x unified",
                                    legend=dict(orientation="h",y=-0.08)))

    avg_rec = rt["Recovery_Week"].dropna()
    return jsonify({
        "io_chart":    _fig_json(fig_io),
        "cge_chart":   _fig_json(fig_cge),
        "abm_chart":   _fig_json(fig_abm),
        "kpis": {
            "welfare":   f"£{cge_r['welfare_change_gbp']/1e9:.3f}bn",
            "max_price": f"{pct.max():.1f}%",
            "max_price_sector": SECTOR_SHORT.get(SECTORS[int(pct.argmax())], ""),
            "io_shortage": f"{float(io_r['shortage'].sum()):.3f}",
            "avg_recovery": f"{avg_rec.mean():.1f} wks" if len(avg_rec) else "—",
        },
        "bullwhip":     bw.to_dict(orient="records"),
        "service_level":sl.to_dict(orient="records"),
        "recovery_time":rt.to_dict(orient="records"),
    })

@app.route("/api/scenarios/all", methods=["POST"])
def api_scenarios_all():
    from shocks import ALL_SCENARIOS
    T     = int((request.json or {}).get("weeks", 52))
    model = get_model()
    all_r = model.run_all_scenarios(ALL_SCENARIOS, T=T)
    comp  = model.comparison_table(all_r)

    fig_loss = go.Figure(go.Bar(
        x=comp["Scenario"].tolist(), y=comp["Economic_Loss_£bn"].tolist(),
        marker_color=["#e63946","#f4a261","#e9c46a","#2a9d8f","#457b9d"],
        text=[f"£{v:.3f}bn" for v in comp["Economic_Loss_£bn"]],
        textposition="outside",
    ))
    fig_loss.update_layout(**_layout(yaxis_title="£bn", title="Economic Loss by Scenario",
                                     height=320))

    fig_price = go.Figure(go.Bar(
        x=comp["Scenario"].tolist(), y=comp["Max_Price_Rise_%"].tolist(),
        marker_color="#e63946",
        text=[f"{v:.1f}%" for v in comp["Max_Price_Rise_%"]], textposition="outside",
    ))
    fig_price.update_layout(**_layout(yaxis_title="%", title="Max Price Rise", height=320))

    rec_vals = [float(v) if str(v).replace(".","").isdigit() else 0
                for v in comp["Avg_Recovery_Weeks"]]
    fig_rec = go.Figure(go.Bar(
        x=comp["Scenario"].tolist(), y=rec_vals,
        marker_color="#e9c46a",
        text=comp["Avg_Recovery_Weeks"].astype(str).tolist(), textposition="outside",
    ))
    fig_rec.update_layout(**_layout(yaxis_title="weeks", title="Average Recovery Time",
                                    height=320))

    return jsonify({
        "comparison": comp.to_dict(orient="records"),
        "loss_chart":  _fig_json(fig_loss),
        "price_chart": _fig_json(fig_price),
        "rec_chart":   _fig_json(fig_rec),
    })


# ══════════════════════════════════════════════════════════════════════════════
# API — VALIDATION
# ══════════════════════════════════════════════════════════════════════════════



# ══════════════════════════════════════════════════════════════════════════════
# API — FIGURE GALLERY
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES — IO / CGE / ABM
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/io")
def io_page():
    return render_template("io.html", sectors=SECTORS, sector_short=SECTOR_SHORT)

@app.route("/cge")
def cge_page():
    return render_template("cge.html", sectors=SECTORS, sector_short=SECTOR_SHORT)

@app.route("/abm")
def abm_page():
    return render_template("abm.html", sectors=SECTORS, sector_short=SECTOR_SHORT)


# ══════════════════════════════════════════════════════════════════════════════
# API — INPUT-OUTPUT MODEL
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/io/analysis")
def api_io_analysis():
    io    = get_model().io
    mults = io.multipliers()
    links = io.linkages()
    calib = io.calibration_report()
    mean_m = float(mults["Output_Multiplier"].mean())

    fig_mult = go.Figure(go.Bar(
        x=[SECTOR_SHORT.get(s, s) for s in mults["Sector"].tolist()],
        y=mults["Output_Multiplier"].tolist(),
        marker_color=["#e63946" if v > mean_m else "#457b9d"
                      for v in mults["Output_Multiplier"]],
        text=[f"{v:.3f}" for v in mults["Output_Multiplier"]],
        textposition="outside",
    ))
    fig_mult.update_layout(**_layout(yaxis_title="Output Multiplier",
                                     title="Leontief Output Multipliers (red = above mean)",
                                     height=360))

    fig_link = go.Figure()
    COLORS = {"#e63946": [], "#457b9d": []}
    for _, row in links.iterrows():
        col = "#e63946" if row.get("Key_Sector", False) else "#457b9d"
        fig_link.add_trace(go.Scatter(
            x=[row["BL_Normalised"]], y=[row["FL_Normalised"]],
            mode="markers+text",
            text=[SECTOR_SHORT.get(row["Sector"], row["Sector"])],
            textposition="top center",
            marker=dict(size=14, color=col),
            name=SECTOR_SHORT.get(row["Sector"], row["Sector"]),
            showlegend=False,
        ))
    fig_link.add_hline(y=1, line_dash="dash", line_color="gray", opacity=0.5)
    fig_link.add_vline(x=1, line_dash="dash", line_color="gray", opacity=0.5)
    fig_link.update_layout(**_layout(
        xaxis_title="Backward Linkage (normalised)",
        yaxis_title="Forward Linkage (normalised)",
        title="Leontief Linkage Quadrant — red = key sectors (BL & FL > 1)",
        height=480,
    ))

    return jsonify({
        "multipliers_chart": _fig_json(fig_mult),
        "linkages_chart":    _fig_json(fig_link),
        "multipliers_table": mults.to_dict(orient="records"),
        "linkages_table":    links.to_dict(orient="records"),
        "calibration_table": calib.to_dict(orient="records"),
    })


@app.route("/api/io/shock-impact", methods=["POST"])
def api_io_shock_impact():
    data     = request.json or {}
    sec_idx  = int(data.get("sector_idx", 2))
    fraction = float(data.get("shock_fraction", 0.5))

    io  = get_model().io
    fd  = get_model().fd_base
    res = io.shock_impact(sec_idx, fraction, fd)

    pct = res["pct_change"]
    fig = go.Figure(go.Bar(
        x=[SECTOR_SHORT.get(s, s) for s in SECTORS],
        y=pct.tolist(),
        marker_color=["#e63946" if v < 0 else "#2a9d8f" for v in pct],
        text=[f"{v:+.2f}%" for v in pct], textposition="outside",
    ))
    fig.update_layout(**_layout(
        yaxis_title="% change in gross output",
        title=f"IO Shock Impact: {SECTOR_SHORT.get(SECTORS[sec_idx], SECTORS[sec_idx])}"
              f" capacity -{fraction*100:.0f}%",
        height=380,
    ))

    return jsonify({
        "figure": _fig_json(fig),
        "disruption_gbp": float(res["disruption_value_gbp"]),
        "sector_shocked": res["sector_shocked"],
        "table": [{"Sector": SECTOR_SHORT.get(s, s), "Pct_Change_%": round(float(p), 3)}
                  for s, p in zip(SECTORS, pct)],
    })


@app.route("/api/io/simulate", methods=["POST"])
def api_io_simulate():
    data     = request.json or {}
    sec_idx  = int(data.get("sector_idx", 2))
    fraction = float(data.get("shock_fraction", 0.5))
    onset    = int(data.get("onset_week", 4))
    duration = int(data.get("duration_weeks", 12))
    T        = int(data.get("T", 52))

    io = get_model().io
    fd = get_model().fd_base

    shock_schedule = {w: [(sec_idx, fraction)]
                      for w in range(onset, min(onset + duration, T))}
    r = io.simulate(T=T, final_demand_base=fd, shock_schedule=shock_schedule)

    weeks  = list(range(T))
    output = r["output"]
    short  = r["shortage"]
    prices = r["prices"]
    COLORS = ["#e63946", "#2a9d8f", "#457b9d", "#f4a261",
              "#264653", "#7b1fa2", "#e9c46a", "#adb5bd"]

    def _ts(arr, title, ylab):
        fig = go.Figure()
        for i, s in enumerate(SECTORS):
            fig.add_trace(go.Scatter(
                x=weeks, y=arr[:, i].tolist(),
                name=SECTOR_SHORT.get(s, s), mode="lines",
                line=dict(color=COLORS[i], width=1.8),
            ))
        fig.add_vline(x=onset, line_dash="dash", line_color="#e63946",
                      annotation_text="Shock onset", annotation_font_color="#e63946")
        if onset + duration < T:
            fig.add_vline(x=onset + duration, line_dash="dot", line_color="#e9c46a",
                          annotation_text="Shock end")
        fig.update_layout(**_layout(yaxis_title=ylab, hovermode="x unified",
                                    legend=dict(orientation="h", y=-0.22),
                                    title=title, height=360))
        return fig

    return jsonify({
        "output_chart":   _fig_json(_ts(output, "Gross Output by Sector", "Output (norm.)")),
        "shortage_chart": _fig_json(_ts(short,  "Supply Shortage by Sector", "Shortage (norm.)")),
        "prices_chart":   _fig_json(_ts(prices, "IO Price Index by Sector", "Price (norm.)")),
        "summary": {
            "total_shortage":  float(short.sum()),
            "max_output_drop": float((1 - output.min(axis=0)).max()),
            "most_affected":   SECTOR_SHORT.get(
                SECTORS[int((1 - output.min(axis=0)).argmax())], ""),
        },
    })


# ══════════════════════════════════════════════════════════════════════════════
# API — CGE MODEL
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/cge/risk")
def api_cge_risk():
    from cge_model import CGEModel
    cge  = CGEModel()
    hhi  = cge.herfindahl_index()
    risk = cge.geographic_risk_score()

    fig_hhi = go.Figure(go.Bar(
        x=[SECTOR_SHORT.get(s, s) for s in hhi["Sector"].tolist()],
        y=hhi["HHI"].tolist(),
        marker_color=["#e63946" if v > 2500 else "#e9c46a" if v > 1500 else "#2a9d8f"
                      for v in hhi["HHI"]],
        text=hhi["HHI"].round(0).astype(int).astype(str).tolist(),
        textposition="outside",
    ))
    fig_hhi.add_hline(y=2500, line_dash="dash", line_color="#e63946",
                      annotation_text="High (2500)")
    fig_hhi.add_hline(y=1500, line_dash="dash", line_color="#e9c46a",
                      annotation_text="Moderate (1500)")
    fig_hhi.update_layout(**_layout(yaxis_title="HHI",
                                     title="Herfindahl-Hirschman Concentration Index",
                                     height=360))

    fig_risk = go.Figure(go.Bar(
        x=[SECTOR_SHORT.get(s, s) for s in risk["Sector"].tolist()],
        y=risk["Geographic_Risk"].tolist(),
        marker_color=["#e63946" if c == "High" else "#e9c46a" if c == "Medium" else "#2a9d8f"
                      for c in risk["Risk_Category"].tolist()],
        text=risk["Risk_Category"].tolist(), textposition="outside",
    ))
    fig_risk.update_layout(**_layout(yaxis_title="Risk Score",
                                      title="Geographic Concentration Risk by Stage",
                                      height=340))

    return jsonify({
        "hhi_chart":  _fig_json(fig_hhi),
        "risk_chart": _fig_json(fig_risk),
        "hhi_table":  hhi.to_dict(orient="records"),
        "risk_table": risk.to_dict(orient="records"),
    })


@app.route("/api/cge/equilibrium", methods=["POST"])
def api_cge_equilibrium():
    from cge_model import CGEModel
    data          = request.json or {}
    shocks        = data.get("shocks", [])
    tariff_sector = data.get("tariff_sector", "")
    tariff_rate   = float(data.get("tariff_rate", 0.0))

    supply_shocks = np.zeros(8)
    for sh in shocks:
        supply_shocks[int(sh["sector_idx"])] = float(sh["magnitude"])

    tariff_schedule = {}
    if tariff_sector and tariff_rate:
        tariff_schedule[tariff_sector] = tariff_rate

    cge = CGEModel(tariff_schedule=tariff_schedule or None)
    fd  = get_model().fd_base
    r   = cge.equilibrium(supply_shocks=supply_shocks, final_demand=fd)

    pct = r["price_index_change_pct"]
    ph  = r["price_history"]        # (iters, 8)
    tf  = r["trade_flows"]          # DataFrame: Sector, Country, Baseline_Share, ...

    fig_price = go.Figure(go.Bar(
        x=[SECTOR_SHORT.get(s, s) for s in SECTORS],
        y=pct.tolist(),
        marker_color=["#e63946" if v > 5 else "#e9c46a" if v > 0 else "#2a9d8f" for v in pct],
        text=[f"{v:+.2f}%" for v in pct], textposition="outside",
    ))
    fig_price.update_layout(**_layout(yaxis_title="% vs baseline",
                                       title="CGE Equilibrium Price Changes by Stage",
                                       height=360))

    COLORS = ["#e63946", "#2a9d8f", "#457b9d", "#f4a261",
              "#264653", "#7b1fa2", "#e9c46a", "#adb5bd"]
    iters = list(range(ph.shape[0]))
    fig_ph = go.Figure()
    for i, s in enumerate(SECTORS):
        fig_ph.add_trace(go.Scatter(
            x=iters, y=ph[:, i].tolist(),
            name=SECTOR_SHORT.get(s, s), mode="lines",
            line=dict(color=COLORS[i], width=1.8),
        ))
    fig_ph.update_layout(**_layout(yaxis_title="Price (norm.)", hovermode="x unified",
                                    xaxis_title="Iteration",
                                    title="Price Convergence Path (CGE iterations)",
                                    height=320))

    pivot = tf.pivot_table(values="Share_Change_%", index="Country", columns="Sector",
                            aggfunc="first", fill_value=0)
    pivot.columns = [SECTOR_SHORT.get(c, c) for c in pivot.columns]
    fig_tf = px.imshow(pivot, template=DARK, height=380,
                       color_continuous_scale="RdYlGn",
                       labels={"color": "Share Δ%"},
                       text_auto=".1f")
    fig_tf.update_layout(**_layout(title="Trade Share Shift by Country × Stage (Δ%)"))

    return jsonify({
        "price_chart":       _fig_json(fig_price),
        "convergence_chart": _fig_json(fig_ph),
        "trade_chart":       _fig_json(fig_tf),
        "welfare_gbp":       float(r["welfare_change_gbp"]),
        "iterations":        int(r["iterations"]),
        "converged":         bool(r["converged"]),
        "trade_table":       tf.to_dict(orient="records"),
    })


@app.route("/api/cge/substitution", methods=["POST"])
def api_cge_substitution():
    from cge_model import CGEModel
    data       = request.json or {}
    sector_idx = int(data.get("sector_idx", 2))
    country    = data.get("country", "China")
    price_chg  = float(data.get("price_change_pct", 20.0))

    cge    = CGEModel()
    prices = {country: 1 + price_chg / 100}
    result = cge.substitution_matrix(sector_idx, prices)

    rows = [{"Country": c,
             "Base_Demand": round(float(v.get("base_demand", 0)), 4),
             "New_Demand":  round(float(v.get("new_demand", 0)), 4),
             "Change_%":    round(float(v.get("change_%", 0)), 2)}
            for c, v in result.items()]

    fig = go.Figure(go.Bar(
        x=[r["Country"] for r in rows],
        y=[r["Change_%"] for r in rows],
        marker_color=["#e63946" if r["Change_%"] < 0 else "#2a9d8f" for r in rows],
        text=[f"{r['Change_%']:+.1f}%" for r in rows], textposition="outside",
    ))
    fig.update_layout(**_layout(
        yaxis_title="Demand change %",
        title=(f"Armington Substitution: {SECTOR_SHORT.get(SECTORS[sector_idx], SECTORS[sector_idx])}"
               f" — {country} price +{price_chg:.0f}%"),
        height=340,
    ))
    return jsonify({"figure": _fig_json(fig), "table": rows})


# ══════════════════════════════════════════════════════════════════════════════
# API — AGENT-BASED MODEL
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/abm/run", methods=["POST"])
def api_abm_run():
    from abm_model import PolyesterSupplyChainABM
    data     = request.json or {}
    sec_idx  = int(data.get("sector_idx", 2))
    fraction = float(data.get("shock_fraction", 0.5))
    onset    = int(data.get("onset_week", 4))
    duration = int(data.get("duration_weeks", 12))
    T        = int(data.get("T", 52))
    st_month = int(data.get("start_month", 1))
    seasonal = bool(data.get("seasonal", True))

    abm_schedule = {onset: [{"sector": sec_idx, "country": "China",
                              "severity": fraction, "duration": duration}]}

    abm = PolyesterSupplyChainABM(agents_per_sector=3)
    r   = abm.run(T=T, baseline_demand=1.0, shock_schedule=abm_schedule,
                  demand_noise=0.03, start_month=st_month, apply_seasonality=seasonal)
    bw  = abm.bullwhip_ratio(r)
    sl  = abm.service_level(r)
    rt  = abm.recovery_time(r)

    weeks  = list(range(T))
    inv    = r["inventory"]
    short  = r["shortage"]
    orders = r["orders"]
    cap    = r["capacity"]
    prices = r["prices"]
    COLORS = ["#e63946", "#2a9d8f", "#457b9d", "#f4a261",
              "#264653", "#7b1fa2", "#e9c46a", "#adb5bd"]

    def _ts(arr, title, ylab):
        fig = go.Figure()
        for i, s in enumerate(SECTORS):
            fig.add_trace(go.Scatter(
                x=weeks, y=arr[:, i].tolist(),
                name=SECTOR_SHORT.get(s, s), mode="lines",
                line=dict(color=COLORS[i], width=1.6),
            ))
        fig.add_vline(x=onset, line_dash="dash", line_color="#e63946",
                      annotation_text="Shock onset", annotation_font_color="#e63946")
        fig.update_layout(**_layout(yaxis_title=ylab, hovermode="x unified",
                                    legend=dict(orientation="h", y=-0.22),
                                    title=title, height=360))
        return fig

    fig_bw = go.Figure(go.Bar(
        x=[SECTOR_SHORT.get(s, s) for s in bw["Sector"].tolist()],
        y=bw["Bullwhip_Ratio"].tolist(),
        marker_color=["#e63946" if v > 2 else "#e9c46a" if v > 1 else "#2a9d8f"
                      for v in bw["Bullwhip_Ratio"]],
        text=[f"{v:.2f}x" for v in bw["Bullwhip_Ratio"]], textposition="outside",
    ))
    fig_bw.add_hline(y=1, line_dash="dash", line_color="gray",
                     annotation_text="1x (no amplification)")
    fig_bw.update_layout(**_layout(yaxis_title="Bullwhip Ratio",
                                    title="Bullwhip Effect by Supply Chain Stage",
                                    height=340))

    fig_sl = go.Figure(go.Bar(
        x=[SECTOR_SHORT.get(s, s) for s in sl["Sector"].tolist()],
        y=sl["Service_Level_%"].tolist(),
        marker_color=["#2a9d8f" if v >= 95 else "#e9c46a" if v >= 80 else "#e63946"
                      for v in sl["Service_Level_%"]],
        text=[f"{v:.1f}%" for v in sl["Service_Level_%"]], textposition="outside",
    ))
    fig_sl.add_hline(y=95, line_dash="dash", line_color="#2a9d8f",
                     annotation_text="95% target")
    fig_sl.update_layout(**_layout(yaxis_title="Service Level %",
                                    title="Agent Service Levels by Stage", height=320))

    rt_plot = rt.copy()
    rt_plot["Recovery_Week_Plot"] = rt_plot["Recovery_Week"].fillna(T + 2)
    fig_rt = go.Figure(go.Bar(
        x=[SECTOR_SHORT.get(s, s) for s in rt_plot["Sector"].tolist()],
        y=rt_plot["Recovery_Week_Plot"].tolist(),
        marker_color=["#e63946" if v > T else "#e9c46a" if v > T * 0.5 else "#2a9d8f"
                      for v in rt_plot["Recovery_Week_Plot"]],
        text=["not recovered" if v > T else f"wk {int(v)}"
              for v in rt_plot["Recovery_Week_Plot"]],
        textposition="outside",
    ))
    fig_rt.update_layout(**_layout(yaxis_title="Recovery Week",
                                    title="Recovery Time by Stage (weeks from simulation start)",
                                    height=320))

    avg_rec = rt["Recovery_Week"].dropna()
    return jsonify({
        "inventory_chart": _fig_json(_ts(inv,    "Inventory Levels (ABM)",     "Inventory (norm.)")),
        "shortage_chart":  _fig_json(_ts(short,  "Supply Shortages (ABM)",     "Shortage (norm.)")),
        "orders_chart":    _fig_json(_ts(orders, "Order Volumes (ABM)",        "Orders (norm.)")),
        "capacity_chart":  _fig_json(_ts(cap,    "Capacity Utilisation (ABM)", "Capacity (norm.)")),
        "prices_chart":    _fig_json(_ts(prices, "Agent Price Dynamics (ABM)", "Price (norm.)")),
        "bullwhip_chart":  _fig_json(fig_bw),
        "service_chart":   _fig_json(fig_sl),
        "recovery_chart":  _fig_json(fig_rt),
        "bullwhip_table":  _clean_records(bw),
        "service_table":   _clean_records(sl),
        "recovery_table":  _clean_records(rt),
        "summary": {
            "total_shortage": float(short.sum()),
            "avg_service":    float(sl["Service_Level_%"].mean()),
            "avg_recovery":   f"{avg_rec.mean():.1f} wks" if len(avg_rec) and not math.isnan(avg_rec.mean()) else "—",
            "max_bullwhip":   float(bw["Bullwhip_Ratio"].max()) if not bw.empty else 0.0,
        },
    })


@app.route("/figures/<path:filename>")
def serve_figure(filename):
    if not FIG_DIR.exists():
        abort(404)
    return send_from_directory(str(FIG_DIR), filename)

@app.route("/api/gallery/generate", methods=["POST"])
def api_gallery_generate():
    def run():
        subprocess.run(
            [sys.executable, str(MODEL_DIR/"visualise.py")],
            cwd=str(MODEL_DIR), capture_output=True,
        )
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return jsonify({"status": "started", "message": "Generation started. Refresh gallery in ~60 s."})

@app.route("/api/gallery/list")
def api_gallery_list():
    if not FIG_DIR.exists():
        return jsonify({"figures": []})
    figs = sorted(f.name for f in FIG_DIR.glob("*.png"))
    return jsonify({"figures": figs, "count": len(figs)})


# ══════════════════════════════════════════════════════════════════════════════
# STARTUP
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Polyester Supply Chain Web Application")
    print("  http://localhost:5000")
    print("=" * 60)
    app.run(debug=False, port=5000, threaded=True)
