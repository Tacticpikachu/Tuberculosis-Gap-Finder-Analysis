"""TB Gap Finder — Streamlit app. Reads only data/clean/ and outputs/. Uses streamlit, pandas, plotly."""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
CLEAN, OUT = ROOT / "data" / "clean", ROOT / "outputs"
NO = "No data"

st.set_page_config(page_title="TB Gap Finder · Johor", page_icon="web/assets/logo.svg", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.6rem; max-width: 1300px; }
.hero { background: linear-gradient(120deg,#0f172a 0%,#1e3a8a 55%,#0ea5e9 100%); color:#fff;
        padding: 1.6rem 2rem; border-radius: 20px; margin-bottom: 1.2rem;
        box-shadow: 0 10px 30px rgba(15,23,42,.25); }
.hero h1 { font-size: 2.1rem; font-weight: 800; margin: 0; letter-spacing: -.02em; }
.hero p { opacity: .85; margin: .35rem 0 0; }
.card { background: rgba(255,255,255,.65); backdrop-filter: blur(10px); border: 1px solid #e2e8f0;
        border-radius: 16px; padding: 1rem 1.1rem; height: 100%;
        box-shadow: 0 4px 14px rgba(15,23,42,.06); transition: transform .15s ease; }
.card:hover { transform: translateY(-2px); }
.card .k { font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; color:#64748b; }
.card .v { font-size: 1.45rem; font-weight: 800; color:#0f172a; margin-top:.15rem; }
.card .s { font-size: .75rem; color:#94a3b8; }
.badge { display:inline-block; padding:.2rem .65rem; border-radius:999px; font-size:.72rem;
         font-weight:700; letter-spacing:.04em; margin-bottom:.6rem; }
.real { background:#dcfce7; color:#166534; } .est { background:#fef3c7; color:#92400e; }
.exp { background:#ede9fe; color:#5b21b6; }
.pass { color:#16a34a; font-weight:800; } .fail { color:#dc2626; font-weight:800; }
@media (prefers-color-scheme: dark) {
  .card { background: rgba(30,41,59,.6); border-color:#334155; }
  .card .v { color:#f1f5f9; }
}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load():
    s = pd.read_csv(CLEAN / "district_summary.csv")
    geo = json.loads((CLEAN / "johor_districts.geojson").read_text())
    sit = pd.read_csv(OUT / "siting_results.csv") if (OUT / "siting_results.csv").exists() else pd.DataFrame()
    val = pd.read_csv(OUT / "validation_results.csv") if (OUT / "validation_results.csv").exists() else pd.DataFrame()
    log = (OUT / "validation_log.md").read_text() if (OUT / "validation_log.md").exists() else ""
    return s, geo, sit, val, log


def fmt(v, digits=1, unit=""):
    if v is None or (isinstance(v, float) and pd.isna(v)) or (isinstance(v, str) and v.startswith("not computed")):
        return NO
    return f"{v:,.{digits}f}{unit}" if isinstance(v, (int, float)) else str(v)


def card(col, k, v, s=""):
    col.markdown(f'<div class="card"><div class="k">{k}</div><div class="v">{v}</div>'
                 f'<div class="s">{s}</div></div>', unsafe_allow_html=True)


def badge(kind):
    cls, txt = {"real": ("real", "REAL DATA"), "est": ("est", "ESTIMATED"),
                "exp": ("exp", "EXPLORATORY")}[kind]
    return f'<span class="badge {cls}">{txt}</span>'


s, geo, sit, val, log = load()
_pts = [pt for f in geo["features"] for poly in (f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiPolygon"
        else [f["geometry"]["coordinates"]]) for ring in poly for pt in ring]
CENTER = {"lon": (min(p[0] for p in _pts) + max(p[0] for p in _pts)) / 2,
          "lat": (min(p[1] for p in _pts) + max(p[1] for p in _pts)) / 2}
year = int(s["year"].iloc[0])

st.markdown(f"""<div class="hero"><h1>TB Gap Finder · Johor</h1>
<p>Where is tuberculosis likely hidden, why, and where should portable X-ray units go?
District data, {year}. Pre-registered analysis (tag prereg-v1).</p></div>""", unsafe_allow_html=True)

# ---------------- sidebar
with st.sidebar:
    st.markdown("### District")
    name = st.selectbox("Choose a district", s["district"].tolist(), label_visibility="collapsed")
    r = s.set_index("district").loc[name]
    st.markdown(badge("real") + badge("est") + badge("exp"), unsafe_allow_html=True)
    rows = [("Reported rate (smoothed)", fmt(r["smoothed_rate"], 1, " /100k"), "real"),
            ("Expected rate (Score B)", fmt(r["expected_rate"], 1, " /100k"), "est"),
            ("Hidden gap", fmt(r["gap"], 1, " /100k"), "est"),
            ("Moran quadrant (exploratory)",
             NO if pd.isna(r["moran_quadrant"]) else f"{r['moran_quadrant']} (p = {r['moran_p']:.2f})", "exp"),
            ("Travel to nearest facility (approx.)", fmt(r["travel_min_approx"], 1, " min"), "est"),
            ("Desert points", fmt(r["desert_points"], 0), "est"),
            ("Suggested action", fmt(r["action"]), "est")]
    for k, v, kind in rows:
        st.markdown(f"**{k}**  \n{v}")
    st.caption("Sources: Johor epidemiological bulletins (TB counts), DOSM (population), "
               "WHO (incidence), OpenStreetMap (facilities), WorldPop. "
               f"Score B basis: {r.get('score_b_basis', NO)}.")

tab1, tab2, tab3 = st.tabs(["Map", "Planner", "Validation & method"])

# ---------------- tab 1: map
with tab1:
    st.markdown(badge("real") + " " + badge("est") + " " + badge("exp"), unsafe_allow_html=True)
    c = st.columns(4)
    card(c[0], "Johor TB cases", f"{int(s['cases'].sum()):,}", f"bulletins, {year}")
    card(c[1], "Top district", s.sort_values("smoothed_rate", ascending=False)["district"].iloc[0],
         "highest smoothed rate")
    card(c[2], "Strong deserts", int((s["desert_level"] == "strong").sum()), "3 of 3 desert points")
    card(c[3], "Selected", name, fmt(r["action"]))
    st.write("")
    options = {"Smoothed TB rate (/100k) · real": "smoothed_rate", "Hidden gap (/100k) · estimated": "gap",
               "Desert level · estimated": "desert_level", "Moran quadrant · exploratory": "moran_quadrant"}
    choice = st.segmented_control("Colour map by", list(options), default=list(options)[0]) or list(options)[0]
    col = options[choice]
    hover = {"smoothed_rate": ":.1f", "gap": ":.1f", "travel_min_approx": ":.1f", "code": False}
    common = dict(geojson=geo, locations="code", featureidkey="properties.code", hover_name="district",
                  hover_data=hover, map_style="white-bg", center=CENTER, zoom=7.4, opacity=0.85)
    if pd.api.types.is_numeric_dtype(s[col]) and s[col].notna().any():
        fig = px.choropleth_map(s, color=col, color_continuous_scale="YlOrRd", **common)
    else:
        d = s.assign(**{col: s[col].fillna(NO).astype(str)})
        palette = {"strong": "#dc2626", "possible": "#f59e0b", "none": "#cbd5e1", "HH": "#dc2626",
                   "LH": "#7c3aed", "LL": "#0ea5e9", "HL": "#f59e0b", NO: "#e5e7eb"}
        fig = px.choropleth_map(d, color=col, color_discrete_map=palette, **common)
    sel_geo = {"type": "FeatureCollection",
               "features": [f for f in geo["features"] if f["properties"]["district"] == name]}
    fig.update_layout(map_layers=[{"source": sel_geo, "type": "line", "color": "#0f172a", "line": {"width": 4}}],
                      height=560, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      legend_title_text="")
    st.plotly_chart(fig, width="stretch")
    with st.expander("District table"):
        show = s[["district", "cases", "smoothed_rate", "expected_rate", "gap", "travel_min_approx",
                  "moran_quadrant", "desert_points", "desert_level", "action"]]
        st.dataframe(show.round(1), hide_index=True, width="stretch")

# ---------------- tab 2: planner
with tab2:
    st.markdown(badge("est") + " Straight-line distance at 40 km/h, 60-minute coverage (approximate).",
                unsafe_allow_html=True)
    if sit.empty:
        st.info(NO)
    else:
        n = st.slider("Number of portable X-ray units", 1, 5, 3)
        cur = sit[sit["n_units"] == n].set_index("version")
        c = st.columns(3)
        for i, (v, lab) in enumerate([("expected_tb", "Expected-TB placement"),
                                      ("population_only", "Population-only placement")]):
            card(c[i], lab, fmt(cur["covered_expected_cases"].get(v), 0, " cases") if v in cur.index else NO,
                 f"{fmt(cur['covered_expected_pct'].get(v), 1, '%')} of expected TB covered" if v in cur.index else "")
        if {"expected_tb", "population_only"} <= set(cur.index):
            diff = cur.loc["expected_tb", "covered_expected_cases"] - cur.loc["population_only", "covered_expected_cases"]
            card(c[2], "Difference", f"{diff:+,.0f} cases", "expected-TB minus population-only")
        st.write("")
        left, right = st.columns([3, 2])
        line = px.line(sit, x="n_units", y="covered_expected_pct", color="version", markers=True,
                       labels={"n_units": "Units", "covered_expected_pct": "% expected TB covered", "version": ""},
                       color_discrete_map={"expected_tb": "#2563eb", "population_only": "#f97316"})
        line.add_vline(x=n, line_dash="dot", line_color="#0f172a")
        line.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)")
        left.plotly_chart(line, width="stretch")
        picks = sit[sit["n_units"] <= n]
        mp = px.choropleth_map(s, geojson=geo, locations="code", featureidkey="properties.code",
                               color_discrete_sequence=["#e2e8f0"], hover_name="district",
                               map_style="white-bg", center=CENTER, zoom=6.9, opacity=0.9)
        for v, colr in [("expected_tb", "#2563eb"), ("population_only", "#f97316")]:
            q = picks[picks["version"] == v]
            mp.add_trace(go.Scattermap(lat=q["lat"], lon=q["lon"], text=q["name"], name=v, mode="markers",
                                       marker=dict(size=15, color=colr),
                                       hovertemplate="%{text}<extra>" + v + "</extra>"))
        mp.update_layout(height=380, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                         paper_bgcolor="rgba(0,0,0,0)")
        right.plotly_chart(mp, width="stretch")
        st.dataframe(picks[["version", "n_units", "name", "amenity", "district", "covered_expected_pct"]]
                     .round(1), hide_index=True, width="stretch")

# ---------------- tab 3: validation & method
with tab3:
    st.markdown(badge("real") + " " + badge("exp"), unsafe_allow_html=True)
    if not val.empty:
        verdicts = val[val["pass"].fillna("").astype(str).str.len() > 0]
        c = st.columns(len(verdicts) or 1)
        for i, (_, v) in enumerate(verdicts.iterrows()):
            p = str(v["pass"])
            cls = "pass" if p == "PASS" else "fail" if p == "FAIL" else ""
            card(c[i], v["test"], f'<span class="{cls}">{p}</span>', str(v["metric"])[:40])
        st.write("")
    img = st.columns(3)
    for i, (f, cap) in enumerate([("roc_curve.png", "V2 ROC curve"), ("confusion_matrix.png", "V2 confusion matrix"),
                                  ("funnel.png", "V4 funnel (district level)")]):
        if (OUT / f).exists():
            img[i].image(str(OUT / f), caption=cap, width="stretch")
        else:
            img[i].info(f"{cap}: {NO}")
    if log:
        with st.expander("Validation log", expanded=True):
            st.markdown(log)
    with st.expander("All validation metrics"):
        st.dataframe(val, hide_index=True, width="stretch")
    st.markdown("#### Method")
    st.latex(r"\text{Score A: } \hat r_i = m + C_i (r_i - m),\quad C_i=\frac{s^2}{s^2+m/n_i},\quad "
             r"s^2=\frac{\sum n_i (r_i-m)^2}{\sum n_i}-\frac{m}{\bar n}")
    st.latex(r"\text{Score B: } \text{risk}_i=\prod_k \left(1+p_{ik}(RR_k-1)\right),\quad "
             r"E_i = \text{WHO rate}\times \text{Pop}_{Johor}\times\frac{\text{pop}_i\,\text{risk}_i}{\sum_j \text{pop}_j\,\text{risk}_j}")
    st.latex(r"\text{Gap}_i = \frac{E_i}{\text{pop}_i}\times 10^5-\hat r_i \qquad "
             r"\text{Desert points} = [\text{LH}] + [\text{gap}>\text{median}] + [\text{travel}>\text{median}]")
    a, b = st.columns(2)
    a.markdown("""**Data sources**
- Johor State Health Department epidemiological bulletins (TB counts, deaths)
- DOSM district population (2020+); WorldPop 1 km (2014–2017)
- WHO TB burden estimates (Malaysia incidence 2023)
- Cochrane 2024 / Imtiaz 2017 relative risks
- OpenStreetMap health facilities; geoBoundaries districts""")
    b.markdown("""**Limitations**
- Travel time is **approximate** (straight-line, 40 km/h), not road network
- Local Moran's I is **exploratory** (10 districts)
- Score B currently uses population share only (no district risk-factor data)
- Bulletins 2018–2022 missing; several years partial
- V1 and V5–V10 not completed; V4 run by district instead of state""")
