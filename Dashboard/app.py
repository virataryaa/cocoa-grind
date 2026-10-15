import base64
import io
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Cocoa Grind", layout="wide", initial_sidebar_state="expanded")

NAVY = "#0a2463"
TEAL = "#1f8a9c"
GREEN = "#1f9d6f"
RED = "#c94a4a"
AMBER = "#c98a1f"
GREY = "#8a94a8"
PURPLE = "#7a4fa0"

DATA = Path(__file__).resolve().parent.parent / "Database" / "cocoa_grind.csv"
ORIGINS = ["ECA", "CAA", "NCA", "IVC", "BR"]                 # Total = sum of these five
EXTRA = ["Malaysia", "German"]                               # sub-sets of CAA and ECA
COLS = ORIGINS + EXTRA                                       # every data column in the CSV
SERIES = ["Total"] + ORIGINS + EXTRA + ["CAA ex-Malaysia", "ECA ex-German"]
COLOR = {"Total": NAVY, "ECA": NAVY, "CAA": TEAL, "NCA": AMBER, "IVC": GREEN, "BR": RED, "Malaysia": PURPLE, "German": "#5a6688",
         "CAA ex-Malaysia": TEAL, "ECA ex-German": NAVY}
PARENT = {"ECA": "Total", "CAA": "Total", "NCA": "Total", "IVC": "Total", "BR": "Total",
          "Malaysia": "CAA", "German": "ECA", "CAA ex-Malaysia": "CAA", "ECA ex-German": "ECA"}
YEAR_COLORS = ["#8a94a8", "#c98a1f", "#1f9d6f", "#1f8a9c", "#7a4fa0", "#c94a4a", "#0a2463"]   # oldest shown -> latest
SHOW_YEARS = 7                                               # crop years visible by default in the line charts
BAND_LO, BAND_MID, BAND_HI = (244, 182, 176), (255, 242, 204), (185, 224, 195)           # red - yellow - green

st.markdown(
    """
<style>
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main { background: #fafafa !important; }
[data-testid="stHeader"] { background: #fafafa !important; }
[data-testid="stSidebar"] { background: #f0f2f8 !important; border-right: 1px solid #dfe3ee; }
h1, h2, h3, h4, h5, h6 { color: #0a2463 !important; }
body, .main { color: #1a1a2e; }
[data-testid="stSidebar"] { color: #1a1a2e; }
.block-container { padding-top: 2.6rem; padding-bottom: 1rem; }

div[role="radiogroup"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 2px; display: inline-flex; flex-wrap: wrap; }
div[role="radiogroup"] label { background: transparent !important; border-radius: 999px !important; padding: 4px 12px !important; margin: 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none; }
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: #5a6688; }
div[role="radiogroup"] label:has(input:checked) { background: #0a2463 !important; }
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; font-weight: 600; }

[data-baseweb="popover"] [data-baseweb="menu"] { background: #ffffff !important; }
[data-baseweb="popover"] [data-baseweb="menu"] li,
[data-baseweb="popover"] [data-baseweb="menu"] li * { color: #1a1a2e !important; }
[data-baseweb="select"] { background: #ffffff !important; }
[data-baseweb="select"] > div { background: #ffffff !important; color: #1a1a2e !important; }

.card-desc { color: #5a6688; font-size: 0.82rem; margin-top: -6px; margin-bottom: 10px; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
    background: #ffffff; border: 1px solid #e3e7f0 !important; border-radius: 12px;
    box-shadow: 0 1px 3px rgba(10,36,99,0.06); }
.st-key-nav div[role="radiogroup"] label { padding: 7px 16px !important; }
.st-key-nav div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 14px !important; }
.st-key-cysel, .st-key-qsel { display: flex; justify-content: flex-end; }
.st-key-cysel [data-baseweb="select"] { min-width: 190px; max-width: 230px; margin-left: auto; }
.st-key-cysel [data-baseweb="select"] > div { border-radius: 999px !important; border: 1.5px solid #0a2463 !important;
    background: #ffffff !important; box-shadow: 0 1px 5px rgba(10,36,99,0.14); min-height: 40px; padding-left: 8px; }
.st-key-cysel [data-baseweb="select"] div, .st-key-cysel [data-baseweb="select"] span { color: #0a2463 !important; font-weight: 600; }
.st-key-cysel [data-baseweb="select"] svg { fill: #0a2463 !important; }
.page-title { color: #0a2463; font-weight: 700; font-size: 1.25rem; margin: 0 0 6px 0; }
.card-title { color: #0a2463; font-weight: 700; font-size: 1rem; margin-bottom: 2px; }
.pill { display: inline-block; background: #e6e9f2; color: #0a2463; font-size: 11px; font-weight: 600;
        padding: 1px 8px; border-radius: 999px; margin-left: 6px; vertical-align: middle; }

.sb-title { font-family: 'Fraunces', Georgia, serif; font-size: 1.5rem; font-weight: 600; color: #0a2463; margin-bottom: 2px; }
.sb-caption { font-size: 11px; color: #7a86a8; margin-bottom: 16px; line-height: 1.4; }
.filter-stat { font-size: 12px; color: #5a6688 !important; line-height: 1.7; margin-bottom: 14px; }
.filter-stat b { color: #0a2463 !important; font-size: 13px; }

.dtab { width: auto; border-collapse: collapse; font-size: 11px; line-height: 1.1; background: #ffffff; }
.dtab th { text-align: center; padding: 2px 6px; font-weight: 600; white-space: nowrap; background: #0a2463; color: #ffffff; }
.dtab td { text-align: right; padding: 1px 6px; border-bottom: 1px solid #eef0f6; white-space: nowrap; color: #1a1a2e; }
.dtab td.dt { text-align: left; font-weight: 700; background: #f0f2f8; }
.dtab td.b { font-weight: 700; }
.dtab td.ts { font-size: 10.5px; font-style: italic; color: #7a86a8; text-align: left; }
.dtab tr.yr td { border-top: 1.5px solid #c9d0e2; }
.dtab-sm { font-size: 10px; }
.dtab-sm th { padding: 2px 3px; }
.dtab-sm td { padding: 1px 3px; }
.tab-note { font-size: 11px; color: #7a86a8; margin-top: 4px; }
.stTabs [data-baseweb="tab-list"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 4px; display: inline-flex; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #5a6688 !important; border-radius: 999px !important;
                               padding: 6px 18px !important; font-weight: 600; border: none !important; }
.stTabs [aria-selected="true"] { background: #0a2463 !important; color: #ffffff !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none !important; }
[data-testid="stSidebarUserContent"] { padding-top: 1rem !important; }
[data-testid="stSidebar"] div[role="radiogroup"] { display: flex; flex-direction: column; align-items: stretch; width: 100%; border-radius: 22px; padding: 5px; gap: 3px; }
[data-testid="stSidebar"] div[role="radiogroup"] label { padding: 8px 18px !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 15px !important; }
.sb-label { font-size: 11px; color: #7a86a8; text-transform: uppercase; letter-spacing: .06em; margin: 14px 0 4px; }
[data-testid="stHorizontalBlock"] { margin-bottom: 0.2rem; }
.kpi { margin-bottom: 4px; background: #ffffff; border: 1px solid #e3e7f0; border-radius: 12px; padding: 12px 16px; box-shadow: 0 1px 3px rgba(10,36,99,0.06); }
.kpi .l { font-size: 11px; color: #7a86a8; text-transform: uppercase; letter-spacing: .06em; }
.kpi .v { font-size: 1.6rem; font-weight: 700; color: #0a2463; line-height: 1.25; }
.kpi .s { font-size: 12px; color: #5a6688; }
.kpi .up { color: #1f9d6f; font-weight: 600; } .kpi .dn { color: #c94a4a; font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------------------------
# data helpers
# ---------------------------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load():
    d = pd.read_csv(DATA, dtype={"crop_year": str, "quarter": str})
    d["cy0"] = d.crop_year.str[:2].astype(int)
    d["q"] = d.quarter.str[1].astype(int)
    d = d.sort_values(["cy0", "q"]).reset_index(drop=True)
    d["label"] = d.quarter + " | " + d.crop_year
    allfive = d[ORIGINS].notna().all(axis=1)
    d["Total"] = d[ORIGINS].sum(axis=1).where(allfive)
    d["CAA ex-Malaysia"] = d["CAA"] - d["Malaysia"]
    d["ECA ex-German"] = d["ECA"] - d["German"]
    return d


def matrix(d, col):
    """Crop years (rows, oldest first) x Q1..Q4."""
    m = d.pivot(index="crop_year", columns="q", values=col)
    m = m.reindex(columns=[1, 2, 3, 4])
    return m.loc[sorted(m.index, key=lambda s: int(s[:2]))]


def fmt(v):
    return "-" if v is None or pd.isna(v) else f"{v:,.0f}"


def pct(v, d=1):
    return "-" if v is None or pd.isna(v) else f"{v * 100:.{d}f}%"


def heat(v, lo, hi):
    """Excel-style red - yellow - green background for v between lo and hi."""
    if v is None or pd.isna(v) or hi <= lo:
        return ""
    t = min(max((v - lo) / (hi - lo), 0), 1)
    a, b, u = (BAND_LO, BAND_MID, t * 2) if t < 0.5 else (BAND_MID, BAND_HI, (t - 0.5) * 2)
    r, g, bl = (round(a[i] + (b[i] - a[i]) * u) for i in range(3))
    return f"background:rgb({r},{g},{bl});"


def heat_div(v, scale):
    """Diverging for changes: negative red, positive green, size by |v| relative to scale."""
    if v is None or pd.isna(v) or scale <= 0:
        return ""
    t = min(abs(v) / scale, 1) * 0.85
    base = (201, 74, 74) if v < 0 else (31, 157, 111)
    r, g, b = (round(255 + (base[i] - 255) * t) for i in range(3))
    return f"background:rgb({r},{g},{b});"


def chart_layout(fig, **extra):
    xaxis = dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578")
    yaxis = dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578", tickformat=",", hoverformat=",.0f")
    xaxis.update(extra.pop("xaxis", {}))
    yaxis.update(extra.pop("yaxis", {}))
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#1a1a2e"), hovermode=extra.pop("hovermode", "x unified"), xaxis=xaxis, yaxis=yaxis,
                      margin=dict(t=20, b=10, l=10, r=10),
                      legend=extra.pop("legend", dict(orientation="h", x=0, y=-0.12, xanchor="left", yanchor="top",
                                                      font=dict(size=11), bgcolor="rgba(0,0,0,0)")),
                      **extra)
    return fig


def card_head(title, pill=None):
    st.markdown(f"<div class='card-title'>{title}" + (f" <span class='pill'>{pill}</span>" if pill else "") + "</div>",
                unsafe_allow_html=True)


# ---------------------------------------------------------------------------------------------
# views
# ---------------------------------------------------------------------------------------------
def quarter_table(d, series):
    """Quarter list: values (all origins on the Total page) and the share column."""
    parent = PARENT.get(series)
    if series == "Total":
        cols, share, share_name = ["Total"] + ORIGINS, d["CAA"] / d["ECA"], "CAA / ECA"
    else:
        cols, share, share_name = [series], d[series] / d[parent], f"% of {parent}"
    lo, hi = share.min(), share.max()
    rows = ""
    for i, r in d.iterrows():
        if r[cols].isna().all():
            continue
        cls = " class='yr'" if r.q == 1 and i > 0 else ""
        rows += f"<tr{cls}><td class='dt'>{r.label}</td>" + "".join(
            f"<td{' class=b' if c in ('Total', series) else ''}>{fmt(r[c])}</td>" for c in cols)
        rows += f"<td style='{heat(share[i], lo, hi)}'>{pct(share[i], 0)}</td></tr>"
    st.markdown("<table class='dtab'><tr><th>Quarter</th>" + "".join(f"<th>{c}</th>" for c in cols)
                + f"<th>{share_name}</th></tr>{rows}</table>", unsafe_allow_html=True)


def area_chart(d, series, h=200):
    x = d["label"]
    fig = go.Figure()
    if series == "Total":
        rows = d[d.Total.notna()]
        for c in ORIGINS:
            fig.add_scatter(x=rows["label"], y=rows[c], name=c, stackgroup="one", mode="lines",
                            line=dict(width=0.5, color=COLOR[c]), fillcolor=COLOR[c])
    else:
        rows = d[d[series].notna()]
        fig.add_bar(x=rows["label"], y=rows[series], name=series, marker_color=COLOR[series])
        fig.add_scatter(x=rows["label"], y=rows[series].rolling(4).mean(), name="4Q average", mode="lines",
                        line=dict(color=AMBER, width=2))
    chart_layout(fig, height=h, xaxis=dict(tickangle=-90, tickfont=dict(size=8)),
                 legend=dict(orientation="h", x=0, y=1.12, yanchor="bottom", font=dict(size=11), bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig, width="stretch", key=f"area_{series}")


def seasonality_chart(mat, series, n_years=SHOW_YEARS, h=250):
    fig = go.Figure()
    shown = list(mat.index[-n_years:])
    n = len(YEAR_COLORS)
    for cy in mat.index:
        k = shown.index(cy) if cy in shown else None
        col = YEAR_COLORS[(n - 1) - (len(shown) - 1 - k) % n] if k is not None else GREY
        fig.add_scatter(x=["Q1", "Q2", "Q3", "Q4"], y=mat.loc[cy].values, name=cy, mode="lines+markers",
                        visible=True if k is not None else "legendonly", connectgaps=False,
                        line=dict(color=col, width=3.5 if cy == mat.index[-1] else 1.8), marker=dict(size=5))
    chart_layout(fig, height=h, legend=dict(orientation="h", x=0, y=-0.1, xanchor="left", yanchor="top", font=dict(size=10), bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig, width="stretch", key=f"seas_{series}")



def q_table(mat):
    full = mat.notna().all(axis=1)
    tot = mat.sum(axis=1).where(full)
    yoy = tot.pct_change(fill_method=None)
    cols = {c: (mat[c].min(), mat[c].max()) for c in mat.columns}
    scale = yoy.abs().max()
    rows = ""
    for cy in mat.index[::-1]:
        rows += f"<tr><td class='dt'>{cy}</td>" + "".join(
            f"<td style='{heat(mat.loc[cy, c], *cols[c])}'>{fmt(mat.loc[cy, c])}</td>" for c in mat.columns)
        rows += f"<td class='b'>{fmt(tot[cy])}</td><td style='{heat_div(yoy[cy], scale)}'>{pct(yoy[cy])}</td></tr>"
    st.markdown("<table class='dtab dtab-sm'><tr><th>Year</th><th>Q1</th><th>Q2</th><th>Q3</th><th>Q4</th><th>Q1-Q4</th><th>%</th></tr>"
                + rows + "</table>", unsafe_allow_html=True)


def change_table(chg):
    scale = float(chg.abs().stack().quantile(0.95)) if chg.notna().any().any() else 0
    rows = ""
    for cy in chg.index[::-1]:
        rows += f"<tr><td class='dt'>{cy}</td>" + "".join(
            f"<td style='{heat_div(chg.loc[cy, c], scale)}'>{pct(chg.loc[cy, c])}</td>" for c in chg.columns) + "</tr>"
    st.markdown("<table class='dtab dtab-sm'><tr><th>Year</th><th>Q1</th><th>Q2</th><th>Q3</th><th>Q4</th></tr>" + rows + "</table>",
                unsafe_allow_html=True)


def qoq(mat):
    flat = pd.Series(mat.values.ravel(), index=pd.MultiIndex.from_product([mat.index, mat.columns]))
    return flat.pct_change(fill_method=None).values.reshape(mat.shape)


def ytd_chart(mat, k, series):
    ytd = mat[list(range(1, k + 1))].sum(axis=1, min_count=k).dropna()
    chg = ytd.pct_change(fill_method=None)
    fig = go.Figure()
    fig.add_bar(x=ytd.index, y=ytd.values, name=f"YTD (Q1 to Q{k})", marker_color=COLOR[series], opacity=0.85)
    fig.add_scatter(x=chg.index, y=chg.values, name="YoY %", yaxis="y2", mode="lines+markers", line=dict(color=AMBER, width=2.5))
    lo = min(ytd.min() * 0.9, ytd.min() - 1) if len(ytd) else 0
    chart_layout(fig, height=205, showlegend=False, yaxis=dict(range=[lo, ytd.max() * 1.04] if len(ytd) else None),
                 yaxis2=dict(overlaying="y", side="right", tickformat=".0%", showgrid=False, color="#4a5578"))
    st.plotly_chart(fig, width="stretch", key=f"ytd_{series}_{k}")


def quarter_bars(mat, k, series):
    s = mat[k].dropna()
    fig = go.Figure(go.Bar(x=s.index, y=s.values, text=[fmt(v) for v in s.values], textposition="outside",
                           marker_color=[COLOR[series] if cy != s.index[-1] else AMBER for cy in s.index],
                           hovertemplate="%{x}: %{y:,.0f}<extra></extra>"))
    chart_layout(fig, height=205, showlegend=False, hovermode="closest",
                 yaxis=dict(range=[s.min() * 0.85, s.max() * 1.08] if len(s) else None))
    st.plotly_chart(fig, width="stretch", key=f"qbar_{series}_{k}")


def kpi(label, value, delta=None):
    cls = "" if delta is None else ("up" if delta >= 0 else "dn")
    return f"<div class='kpi'><div class='l'>{label}</div><div class='v {cls}'>{value}</div></div>"


def share_chart(d, series, h=205):
    parent = PARENT[series]
    rows = d[d[series].notna() & d[parent].notna()]
    fig = go.Figure(go.Scatter(x=rows["label"], y=rows[series] / rows[parent], mode="lines", line=dict(color=COLOR[series], width=2.5)))
    chart_layout(fig, height=h, showlegend=False, xaxis=dict(tickangle=-90, tickfont=dict(size=8)),
                 yaxis=dict(tickformat=".0%", hoverformat=".1%"))
    st.plotly_chart(fig, width="stretch", key=f"share_{series}")


def mix_charts(d, h=205):
    rows = d[d.Total.notna()]
    fig = go.Figure()
    for o in ORIGINS:
        fig.add_scatter(x=rows["label"], y=rows[o] / rows.Total, name=o, stackgroup="one", mode="lines",
                        line=dict(width=0.5, color=COLOR[o]), fillcolor=COLOR[o])
    chart_layout(fig, height=h, xaxis=dict(tickangle=-90, tickfont=dict(size=8)), yaxis=dict(tickformat=".0%", hoverformat=".1%"),
                 legend=dict(orientation="h", x=0, y=1.12, yanchor="bottom", font=dict(size=10), bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig, width="stretch", key="mix_share")
    return rows


def ratio_chart(d, h=205):
    rows = d[d.Total.notna()]
    fig = go.Figure(go.Scatter(x=rows["label"], y=rows.CAA / rows.ECA, mode="lines", line=dict(color=TEAL, width=2.5)))
    chart_layout(fig, height=h, showlegend=False, xaxis=dict(tickangle=-90, tickfont=dict(size=8)),
                 yaxis=dict(tickformat=".0%", hoverformat=".1%"))
    st.plotly_chart(fig, width="stretch", key="mix_ratio")


def overview_kpis(d):
    mat = matrix(d, "Total")
    last = d[d.Total.notna()].iloc[-1]
    i = d.index[d.label == last.label][0]
    qq = last.Total / d.Total[i - 1] - 1 if i > 0 else None
    ly = d[(d.cy0 == last.cy0 - 1) & (d.q == last.q)]
    yy = last.Total / ly.Total.iloc[0] - 1 if len(ly) and pd.notna(ly.Total.iloc[0]) else None
    cols_q = list(range(1, int(last.q) + 1))
    cy_now, cy_ly = f"{last.cy0}/{last.cy0 + 1}", f"{last.cy0 - 1}/{last.cy0}"
    ytd = mat.loc[cy_now, cols_q].sum() if mat.loc[cy_now, cols_q].notna().all() else None
    ytd_ly = mat.loc[cy_ly, cols_q].sum() if cy_ly in mat.index and mat.loc[cy_ly, cols_q].notna().all() else None
    yt = ytd / ytd_ly - 1 if ytd and ytd_ly else None
    c = st.columns(4, gap="small")
    c[0].markdown(kpi(f"Latest quarter {last.label}", fmt(last.Total)), unsafe_allow_html=True)
    c[1].markdown(kpi("YoY", pct(yy), yy), unsafe_allow_html=True)
    c[2].markdown(kpi("QoQ", pct(qq), qq), unsafe_allow_html=True)
    c[3].markdown(kpi(f"YTD (Q1 to Q{int(last.q)})", pct(yt), yt), unsafe_allow_html=True)


def dashboard(d, series, n_years, is_overview=False):
    """Everything for one series on one screen: table | trend + seasonality | Q1-Q4, YoY, QoQ, then YTD / Q-bars / extras."""
    mat = matrix(d, series)
    if is_overview:
        overview_kpis(d)
    a, b, c = st.columns([1.65 if series == "Total" else 0.8, 1.65, 1.5], gap="small")
    with a, st.container(border=True):
        card_head("Quarterly grind", series)
        with st.container(height=520, border=False):
            quarter_table(d, series)
    with b:
        with st.container(border=True):
            card_head("Grind by origin" if series == "Total" else f"{series} grind", series)
            area_chart(d, series)
        with st.container(border=True):
            card_head("Seasonality per quarter")
            seasonality_chart(mat, series, n_years)
    with c:
        with st.container(border=True):
            card_head("Q1-Q4")
            q_table(mat)
        c2, c3 = st.columns(2, gap="small")
        with c2, st.container(border=True):
            card_head("YoY change")
            change_table(mat.pct_change(fill_method=None))
        with c3, st.container(border=True):
            card_head("QoQ change")
            change_table(pd.DataFrame(qoq(mat), index=mat.index, columns=mat.columns))
    last = d[d[series].notna()].iloc[-1]
    qmax = int(last.q) if last.cy0 == int(mat.index[-1][:2]) else 4
    if f"qsel_{series}" not in st.session_state:
        st.session_state[f"qsel_{series}"] = f"Q{qmax}"
    hd = st.columns([6, 1.6], vertical_alignment="center")
    hd[0].markdown(f"<div class='card-title'>YTD and single quarter <span class='pill'>{series}</span></div>", unsafe_allow_html=True)
    with hd[1]:
        k = int(st.radio("Quarter", ["Q1", "Q2", "Q3", "Q4"], horizontal=True, label_visibility="collapsed", key=f"qsel_{series}")[1])
    extras = 2 + (1 if is_overview else 0) * 1 + (1 if series in PARENT else 0)
    cols = st.columns(extras if not is_overview else 4, gap="small")
    with cols[0], st.container(border=True):
        card_head(f"YTD (Q1 to Q{k})")
        ytd_chart(mat, k, series)
    with cols[1], st.container(border=True):
        card_head(f"Q{k} across years")
        quarter_bars(mat, k, series)
    if is_overview:
        with cols[2], st.container(border=True):
            card_head("Origin share of Total")
            mix_charts(d)
        with cols[3], st.container(border=True):
            card_head("CAA / ECA")
            ratio_chart(d)
    elif series in PARENT:
        with cols[2], st.container(border=True):
            card_head(f"{series} as % of {PARENT[series]}")
            share_chart(d, series)


# ---------------------------------------------------------------------------------------------
# entry (edits the CSV on GitHub)
# ---------------------------------------------------------------------------------------------
REPO, REPO_PATH = "virataryaa/cocoa-grind", "Database/cocoa_grind.csv"
GH_API = f"https://api.github.com/repos/{REPO}/contents/{REPO_PATH}"
GH_COMMITS = f"https://api.github.com/repos/{REPO}/commits"
TZ = "Europe/Amsterdam"


class GitHubError(Exception):
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status


@st.cache_resource
def gh_session():
    s = requests.Session()
    tok = str(st.secrets["github_token"]).strip().strip('"').strip("'")
    s.headers.update({"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"})
    return s


@st.cache_resource
def gh_state():
    return {}


def gh_check(r):
    if r.status_code >= 400:
        try:
            msg = r.json().get("message", "")
        except ValueError:
            msg = r.text[:200]
        hint = {401: "token is wrong or expired - re-paste github_token in Secrets",
                403: "token has no write access - give it Contents: Read and write on cocoa-grind",
                404: "token cannot see the cocoa-grind repo - add this repo to the token",
                409: "file changed meanwhile - press Save again"}.get(r.status_code, "")
        raise GitHubError(f"GitHub {r.status_code}: {msg}. {hint}", r.status_code)


def gh_read():
    r = gh_session().get(GH_API, params={"ref": "main"}, timeout=20)
    gh_check(r)
    j = r.json()
    frame = pd.read_csv(io.StringIO(base64.b64decode(j["content"]).decode("utf-8")), dtype={"crop_year": str})
    gh_state().update(csv=frame, sha=j["sha"])
    return frame.copy(), j["sha"]


def gh_write(frame, sha, msg):
    body = {"message": msg, "branch": "main", "sha": sha,
            "content": base64.b64encode(frame.to_csv(index=False, lineterminator="\n").encode()).decode()}
    r = gh_session().put(GH_API, json=body, timeout=20)
    gh_check(r)
    j = r.json()
    gh_state().update(csv=frame.copy(), sha=j["content"]["sha"])
    gh_state().setdefault("history", []).insert(0, (j["commit"]["committer"]["date"], msg))


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_history():
    r = gh_session().get(GH_COMMITS, params={"path": REPO_PATH, "per_page": 30}, timeout=20)
    gh_check(r)
    return [(c["commit"]["committer"]["date"], c["commit"]["message"].split("\n")[0]) for c in r.json()]


def save_history():
    s = gh_state()
    if "history" not in s:
        s["history"] = _fetch_history()
    return s["history"]


def entry_enabled():
    try:
        return "github_token" in st.secrets
    except Exception:
        return False


def parse_num(txt):
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):
        return None
    if isinstance(txt, (int, float)):
        return float(txt)
    txt = str(txt).replace(",", "").strip()
    return float(txt) if txt else None


def apply_entry(frame, cy, q, vals):
    frame = frame.copy()
    hit = (frame.crop_year == cy) & (frame.quarter == q)
    if hit.any():
        for c, v in vals.items():
            frame.loc[hit, c] = v
    else:
        frame = pd.concat([frame, pd.DataFrame([{"crop_year": cy, "quarter": q, **vals}])])
    frame = frame[~frame[COLS].isna().all(axis=1)]
    frame["_o"] = frame.crop_year.str[:2].astype(int) * 10 + frame.quarter.str[1].astype(int)
    frame = frame.sort_values("_o").drop(columns="_o").reindex(columns=["crop_year", "quarter", *COLS])
    frame[COLS] = frame[COLS].round().astype("Int64")
    return frame


def commit_change(change, msg):
    state = gh_state()
    frame, sha = (state["csv"], state["sha"]) if "sha" in state else gh_read()
    try:
        gh_write(change(frame), sha, msg)
    except GitHubError as ex:
        if ex.status not in (409, 422):
            raise
        frame, sha = gh_read()
        gh_write(change(frame), sha, msg)
    gh_state()["csv"].to_csv(DATA, index=False, lineterminator="\n")      # show it now, before Cloud redeploys
    load.clear()


def value_notes(d, cy, q, vals):
    """Checks that need a second look: >25% away from the previous quarter or from the same quarter last year."""
    notes = []
    order = int(cy[:2]) * 10 + q
    d = d.assign(_o=d.cy0 * 10 + d.q)
    for c, v in vals.items():
        if v is None:
            continue
        s = d[(d._o < order) & d[c].notna()]
        if not s.empty and abs(v / s[c].iloc[-1] - 1) > 0.25:
            notes.append(f"{c} {q} | {cy} {v:,.0f} is {v / s[c].iloc[-1] - 1:+.0%} vs the previous quarter ({s[c].iloc[-1]:,.0f}).")
        ly = d[(d.cy0 == int(cy[:2]) - 1) & (d.q == q) & d[c].notna()]
        if not ly.empty and abs(v / ly[c].iloc[0] - 1) > 0.25:
            notes.append(f"{c} {q} | {cy} {v:,.0f} is {v / ly[c].iloc[0] - 1:+.0%} vs a year earlier ({ly[c].iloc[0]:,.0f}).")
    return notes


def save_changes(changes, d):
    with st.spinner("Saving..."):
        try:
            for (cy, q), upd in sorted(changes.items()):
                txt = " | ".join(f"{c} {fmt(v)}" for c, v in upd.items())
                commit_change(lambda f, cy=cy, q=q, upd=upd: apply_entry(f, cy, f"Q{q}", upd),
                              f"Entry {cy} Q{q} via dashboard | {txt}")
        except (GitHubError, requests.RequestException) as ex:
            st.error(f"GitHub save failed: {ex}")
            return
    st.session_state.pop("pending_grid", None)
    st.session_state.pop("entry_grid", None)
    st.session_state["flash"] = f"Saved {len(changes)} quarter(s)."
    st.rerun()


def render_entry(d):
    if st.session_state.get("flash"):
        st.toast(st.session_state.pop("flash"))
    editable = entry_enabled()
    card_head("Entry")
    if not editable:
        st.markdown("<div class='card-desc'>Read-only: add github_token in Secrets.</div>", unsafe_allow_html=True)
    y = int(d.cy0.max())
    rows = [(f"{c:02d}/{c + 1:02d}", q) for c in (y - 1, y, y + 1) for q in (1, 2, 3, 4)]     # latest two crop years + the next one
    have = d.set_index(["crop_year", "q"])
    g = pd.DataFrame(index=[f"Q{q} | {cy}" for cy, q in rows])
    for c in COLS:
        g[c] = [fmt(have.loc[(cy, q), c]) if (cy, q) in have.index and pd.notna(have.loc[(cy, q), c]) else "" for cy, q in rows]
    vals = g[ORIGINS].apply(lambda col: col.map(parse_num))
    g.insert(len(ORIGINS), "Total", [fmt(r.sum()) if r.notna().all() else "" for _, r in vals.iterrows()])
    cfg = {c: st.column_config.TextColumn(c, alignment="right", width=88 if c in EXTRA else 76) for c in g.columns}
    cfg["Total"] = st.column_config.TextColumn("Total", alignment="right", width=82, disabled=True)
    cfg["_index"] = st.column_config.TextColumn("Quarter", width=82)
    key = "entry_grid"
    shown = g.style.set_properties(subset=["Total"], **{"background-color": "#e9ecf2", "font-weight": "600"})
    after = st.data_editor(shown, column_config=cfg, disabled=not editable, width="content", row_height=30,
                           height=len(g) * 30 + 52, key=key)
    changes = {}
    try:
        for c in COLS:
            for i, (a, b) in enumerate(zip(g[c], after[c])):
                a, b = parse_num(a), parse_num(b)
                if a != b:
                    changes.setdefault(rows[i], {})[c] = b
    except ValueError:
        st.error("Numbers only (commas are fine).")
        return
    if not editable:
        return
    bc = st.columns([1, 1, 4], vertical_alignment="center")
    save = bc[0].button("Save", type="primary", disabled=not changes, width="stretch")
    if bc[1].button("Undo", disabled=not changes, width="stretch"):
        st.session_state.pop(key, None)
        st.session_state.pop("pending_grid", None)
        st.rerun()
    if changes:
        bc[2].markdown(f"<div class='card-desc' style='margin:0'>{sum(len(v) for v in changes.values())} unsaved cell(s).</div>",
                       unsafe_allow_html=True)
    if save:
        notes = [n for (c_, q_), upd in sorted(changes.items()) for n in value_notes(d, c_, q_, upd)]
        if not notes:
            save_changes(changes, d)
            return
        st.session_state["pending_grid"] = notes
    if st.session_state.get("pending_grid") and changes:
        cc = st.columns([3.2, 0.6, 0.6, 1.6], vertical_alignment="center")
        cc[0].warning(" ".join(st.session_state["pending_grid"]) + " Save anyway?")
        if cc[1].button("Override", type="primary", width="stretch", key="grid_override"):
            save_changes(changes, d)
        if cc[2].button("Cancel", width="stretch", key="grid_cancel"):
            st.session_state.pop("pending_grid", None)
            st.rerun()



def render_history():
    if not entry_enabled():
        return
    try:
        hist = save_history()
    except (GitHubError, requests.RequestException) as ex:
        st.markdown(f"<div class='card-desc'>Not available: {ex}</div>", unsafe_allow_html=True)
        return
    rows = ""
    for ts, msg in hist:
        if not msg.startswith(("Entry ", "Data update")):
            continue
        when = pd.Timestamp(ts).tz_convert(TZ)
        head, _, detail = msg.partition("|")
        for_ = head.replace("Entry ", "").replace(" via dashboard", "").strip() if msg.startswith("Entry ") else "-"
        rows += (f"<tr><td class='ts'>{when:%d %b %H:%M}</td><td class='dt'>{for_}</td><td class='ts'>{detail.strip() or msg}</td>"
                 f"<td class='ts'>{'Dashboard' if msg.startswith('Entry ') else 'Local push'}</td></tr>")
        if rows.count("<tr>") >= 10:
            break
    if rows:
        st.markdown("<div class='card-desc'>Last 10 saves, Amsterdam time (CET).</div><table class='dtab'><tr><th>Saved at</th>"
                    "<th>For</th><th>Values</th><th>Via</th></tr>" + rows + "</table>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------------------------
# layout
# ---------------------------------------------------------------------------------------------
df = load()
latest = df[df.Total.notna()].iloc[-1]
prev_y = df[(df.cy0 == latest.cy0 - 1) & (df.q == latest.q)]

SECTIONS = {"Overview": ["Total"], "Origins": ["Total"] + ORIGINS,
            "Sub-regions": EXTRA + ["CAA ex-Malaysia", "ECA ex-German"]}
with st.sidebar:
    st.markdown("<div class='sb-title'>Cocoa Grind</div>", unsafe_allow_html=True)
    st.markdown("<div class='sb-label'>Section</div>", unsafe_allow_html=True)
    section = st.radio("Section", ["Overview", "Origins", "Sub-regions", "Data"], label_visibility="collapsed", key="section")
    series = "Total"
    if section in SECTIONS and len(SECTIONS[section]) > 1:
        st.markdown("<div class='sb-label'>Series</div>", unsafe_allow_html=True)
        series = st.radio("Series", SECTIONS[section], label_visibility="collapsed", key=f"series_{section}")
    if section != "Data":
        st.markdown("<div class='sb-label'>Years shown</div>", unsafe_allow_html=True)
        st.radio("Years shown", ["Last 5", "Last 7", "All"], index=1, horizontal=True, label_visibility="collapsed", key="yrs")
    n_years = {"Last 5": 5, "Last 7": 7, "All": 99}.get(st.session_state.get("yrs", "Last 7"), 7)
    st.markdown("<div class='sb-label'>Latest</div>", unsafe_allow_html=True)
    stats = [("Latest quarter", latest.label, None), ("Total", fmt(latest.Total), None)]
    if len(prev_y) and pd.notna(prev_y.Total.iloc[0]):
        stats.append(("YoY", pct(latest.Total / prev_y.Total.iloc[0] - 1), f"vs {prev_y.label.iloc[0]}"))
    stats.append(("CAA / ECA", pct(latest.CAA / latest.ECA, 0), None))
    html = "<div class='filter-stat'>" + "".join(
        f"{a}: <b>{b}</b>" + (f" <span style='color:#7a86a8;'>({c})</span>" if c else "") + "<br>" for a, b, c in stats) + "</div>"
    st.markdown(html, unsafe_allow_html=True)

if section == "Overview":
    dashboard(df, "Total", n_years, is_overview=True)
elif section == "Data":
    t_entry, t_hist = st.tabs(["Entry", "History"])
    with t_entry:
        le, ri = st.columns([1.6, 1.15], gap="medium")
        with le, st.container(border=True):
            render_entry(df)
        with ri, st.container(border=True):
            card_head("Quarterly grind", "Total")
            quarter_table(df, "Total")
    with t_hist:
        with st.container(border=True):
            card_head("Save history")
            if entry_enabled():
                render_history()
            else:
                st.markdown("<div class='card-desc'>Add github_token in Secrets to see saves.</div>", unsafe_allow_html=True)
            st.download_button("Download CSV", df[["crop_year", "quarter", *COLS]].to_csv(index=False), "cocoa_grind.csv", "text/csv")
else:
    dashboard(df, series, n_years)
