"""
Meta Ads Overview dashboard (Streamlit + Plotly)
Run:  pip install streamlit pandas numpy plotly
      streamlit run meta_ads_dashboard.py

Replace load_data() with your real data (CSV, Meta Marketing API, BigQuery, Supabase...).
Demo data is synthetic. Required columns: date, campaign, platform, state, impressions, reach, clicks, spend
"""
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

st.set_page_config(page_title="Meta Ads Overview", page_icon="📊", layout="wide")

# ----------------------------------------------------------------------------
# 1. DATA  (synthetic demo - replace with pd.read_csv("your_file.csv"))
# ----------------------------------------------------------------------------
STATES = {  # name: (lat, lon, weight)  -> Indonesian provinces
    "DKI Jakarta": (-6.20, 106.85, 1.00),
    "Jawa Barat": (-6.90, 107.60, 0.85),
    "Jawa Timur": (-7.50, 112.20, 0.70),
    "Jawa Tengah": (-7.15, 110.14, 0.55),
    "Sumatera Utara": (2.10, 99.00, 0.42),
    "Bali": (-8.34, 115.09, 0.36),
    "Sulawesi Selatan": (-3.67, 119.97, 0.28),
}
# Fictional brands (safe for a public portfolio) + a "launch day" and a "boost" per campaign
CAMPAIGNS = {  # name: (size weight, launch offset in days, ctr multiplier)
    "nusa_coffee_reach_tofu_v2": (1.00, 0, 1.00),
    "kopikita_localawareness_mofu_v1": (0.80, 10, 1.15),
    "mobilgo_brandawareness_bofu_v3": (0.55, 25, 0.90),
    "tokoku_promo_conversion_bofu_v1": (0.35, 40, 1.35),
}
PLATFORMS = {"mobile_app": 0.90, "mobile_web": 0.06, "desktop": 0.035, "unknown": 0.005}


@st.cache_data
def load_data() -> pd.DataFrame:
    """Synthetic demo data: growth trend + weekly seasonality + campaign launches + one promo spike."""
    rng = np.random.default_rng(7)
    dates = pd.date_range(end=pd.Timestamp.today().normalize() - pd.Timedelta(days=1), periods=90)
    idx = pd.MultiIndex.from_product(
        [dates, list(CAMPAIGNS), list(PLATFORMS), list(STATES)],
        names=["date", "campaign", "platform", "state"],
    )
    df = idx.to_frame(index=False)
    day = (df["date"] - dates[0]).dt.days.to_numpy()

    c_size = df["campaign"].map(lambda c: CAMPAIGNS[c][0]).to_numpy()
    c_launch = df["campaign"].map(lambda c: CAMPAIGNS[c][1]).to_numpy()
    c_ctr = df["campaign"].map(lambda c: CAMPAIGNS[c][2]).to_numpy()

    growth = 1 + 0.012 * day                                   # steady upward trend
    weekly = 1 + 0.18 * np.sin(2 * np.pi * (df["date"].dt.dayofweek.to_numpy() - 4) / 7)  # weekend peak
    ramp = np.clip((day - c_launch) / 7, 0, 1)                 # campaign ramps up over 7 days
    spike = 1 + 0.6 * np.exp(-((day - 62) ** 2) / 18)          # one promo spike (~day 62)

    base = (
        2600 * c_size * growth * weekly * ramp * spike
        * df["platform"].map(PLATFORMS).to_numpy()
        * df["state"].map(lambda s: STATES[s][2]).to_numpy()
    )
    df["impressions"] = (base * rng.normal(1, 0.10, len(df))).clip(0).round()
    df["reach"] = (df["impressions"] / rng.normal(3.2, 0.25, len(df)).clip(1.5)).round()
    df["clicks"] = (df["impressions"] * c_ctr * rng.normal(0.0125, 0.0012, len(df)).clip(0.003)).round()
    df["spend"] = df["impressions"] * rng.normal(24_000, 1_500, len(df)) / 1000  # ~Rp24rb CPM
    return df


df_all = load_data()

# ----------------------------------------------------------------------------
# 2. FILTERS
# ----------------------------------------------------------------------------
st.sidebar.header("Filters")
d_min, d_max = df_all["date"].min().date(), df_all["date"].max().date()
date_range = st.sidebar.date_input(
    "Date range", (d_max - pd.Timedelta(days=29), d_max), min_value=d_min, max_value=d_max
)
if len(date_range) != 2:
    st.info("Pick a start and end date.")
    st.stop()
start, end = map(pd.Timestamp, date_range)

campaign_sel = st.sidebar.multiselect("Campaign", list(CAMPAIGNS))
platform_sel = st.sidebar.multiselect("Platform", list(PLATFORMS))
state_sel = st.sidebar.selectbox("State", ["All"] + list(STATES))

mask = pd.Series(True, index=df_all.index)
if campaign_sel:
    mask &= df_all["campaign"].isin(campaign_sel)
if platform_sel:
    mask &= df_all["platform"].isin(platform_sel)
if state_sel != "All":
    mask &= df_all["state"] == state_sel
df_f = df_all[mask]

# current period + previous period of the same length (for % change)
n_days = (end - start).days + 1
prev_start, prev_end = start - pd.Timedelta(days=n_days), start - pd.Timedelta(days=1)
cur = df_f[df_f["date"].between(start, end)]
prev = df_f[df_f["date"].between(prev_start, prev_end)]


def totals(d: pd.DataFrame) -> dict:
    imp, clk, spd, rch = d["impressions"].sum(), d["clicks"].sum(), d["spend"].sum(), d["reach"].sum()
    return {
        "Impressions": imp, "Reach": rch, "Link Clicks": clk, "Amount Spent": spd,
        "Frequency": imp / rch if rch else 0,
        "CPM": spd / imp * 1000 if imp else 0,
        "CTR": clk / imp * 100 if imp else 0,
        "Cost/Link Click": spd / clk if clk else 0,
    }


T_cur, T_prev = totals(cur), totals(prev)


def pct(k: str) -> float:
    return (T_cur[k] - T_prev[k]) / T_prev[k] * 100 if T_prev[k] else 0.0


# ----------------------------------------------------------------------------
# 3. STYLING + KPI CARDS
# ----------------------------------------------------------------------------
st.markdown(
    """
<style>
.block-container {padding-top: 1.5rem;}
.kpi {border-radius:14px; padding:14px 18px; color:white; margin-bottom:12px;}
.kpi .label {font-size:.9rem; font-weight:600; opacity:.95;}
.kpi .value {font-size:1.9rem; font-weight:700; line-height:1.2;}
.kpi .delta {font-size:.8rem; opacity:.9;}
.panel {background:#5b5ff7; color:white; border-radius:14px; padding:16px 20px;}
.panel h4 {margin:0 0 6px 0; color:white;}
</style>
""",
    unsafe_allow_html=True,
)


def kpi(col, label, value_str, delta, color):
    arrow = "▲" if delta >= 0 else "▼"
    col.markdown(
        f"""<div class="kpi" style="background:{color}">
        <div class="label">{label}</div>
        <div class="value">{value_str}</div>
        <div class="delta">{arrow} {delta:+.1f}% vs previous period</div></div>""",
        unsafe_allow_html=True,
    )


def human(n: float) -> str:
    for unit, div in (("M", 1e6), ("K", 1e3)):
        if abs(n) >= div:
            return f"{n/div:.1f}{unit}"
    return f"{n:,.0f}"


st.title("Meta Ads · Overview")
st.caption("⚠️ Demo dashboard — all data is randomly generated sample data (fictional brands). Currency: Rupiah.")
left, right = st.columns(2)
with left:
    st.subheader("Progress Over Time")
    c1, c2 = st.columns(2)
    kpi(c1, "Impressions", human(T_cur["Impressions"]), pct("Impressions"), "#1e6ff1")
    kpi(c2, "Frequency", f'{T_cur["Frequency"]:.1f}', pct("Frequency"), "#2fb0c4")
    kpi(c1, "Reach", human(T_cur["Reach"]), pct("Reach"), "#12c2a5")
    kpi(c2, "CPM", f'{T_cur["CPM"]:.2f}', pct("CPM"), "#2ea8e6")
with right:
    st.subheader("Conversions")
    c1, c2 = st.columns(2)
    kpi(c1, "Link Clicks", f'{T_cur["Link Clicks"]:,.0f}', pct("Link Clicks"), "#ff9500")
    kpi(c2, "CTR (Link Clicks)", f'{T_cur["CTR"]:.2f}%', pct("CTR"), "#a54bd8")
    kpi(c1, "Cost / Link Click", f'{T_cur["Cost/Link Click"]:.2f}', pct("Cost/Link Click"), "#ff9500")
    kpi(c2, "Amount Spent", human(T_cur["Amount Spent"]), pct("Amount Spent"), "#2cc84d")

# ----------------------------------------------------------------------------
# 4. TIMELINE (bars + two lines, dual axis)
# ----------------------------------------------------------------------------
st.subheader("Timeline")
daily = cur.groupby("date")[["clicks", "impressions", "spend"]].sum().reset_index()
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_bar(x=daily["date"], y=daily["clicks"], name="Link Clicks", marker_color="#ff9500")
fig.add_scatter(x=daily["date"], y=daily["impressions"], name="Impressions",
                mode="lines+markers", line=dict(color="#1e6ff1"), secondary_y=True)
fig.add_scatter(x=daily["date"], y=daily["spend"], name="Amount Spent",
                mode="lines+markers", line=dict(color="#2cc84d"), secondary_y=True)
fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10),
                  legend=dict(orientation="h", y=1.12), hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# ----------------------------------------------------------------------------
# 5. CAMPAIGN TABLE (in-cell data bars + % change)
# ----------------------------------------------------------------------------
st.subheader("Campaigns")
g_cur = cur.groupby("campaign")[["impressions", "reach", "clicks", "spend"]].sum()
g_prev = prev.groupby("campaign")[["impressions", "reach", "clicks", "spend"]].sum()
delta = ((g_cur - g_prev) / g_prev.replace(0, np.nan) * 100).add_suffix("_chg")
tbl = g_cur.join(delta).sort_values("impressions", ascending=False).reset_index()
tbl = tbl[["campaign", "impressions", "impressions_chg", "reach", "clicks", "clicks_chg", "spend", "spend_chg"]]

st.dataframe(
    tbl,
    hide_index=True,
    use_container_width=True,
    column_config={
        "campaign": "Campaign Name",
        "impressions": st.column_config.ProgressColumn("Impressions", format="%d", min_value=0, max_value=float(tbl["impressions"].max() or 1)),
        "impressions_chg": st.column_config.NumberColumn("% Δ", format="%.1f%%"),
        "reach": st.column_config.ProgressColumn("Reach", format="%d", min_value=0, max_value=float(tbl["reach"].max() or 1)),
        "clicks": st.column_config.ProgressColumn("Link Clicks", format="%d", min_value=0, max_value=float(tbl["clicks"].max() or 1)),
        "clicks_chg": st.column_config.NumberColumn("% Δ", format="%.1f%%"),
        "spend": st.column_config.ProgressColumn("Amount Spent", format="%.2f", min_value=0, max_value=float(tbl["spend"].max() or 1)),
        "spend_chg": st.column_config.NumberColumn("% Δ", format="%.1f%%"),
    },
)

# ----------------------------------------------------------------------------
# 6. DEVICE DONUT + STATE MAP/TABLE + TOP STATE
# ----------------------------------------------------------------------------
col_dev, col_state = st.columns(2)

with col_dev:
    st.subheader("Device performance | Impressions & Clicks")
    by_dev = cur.groupby("platform")["impressions"].sum().reset_index()
    donut = px.pie(by_dev, names="platform", values="impressions", hole=0.6,
                   color_discrete_sequence=["#5b5ff7", "#ff7043", "#b9bcf5", "#e8e0d8"])
    donut.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(donut, use_container_width=True)

    mob = cur[cur["platform"].isin(["mobile_app", "mobile_web"])]
    comp = cur[cur["platform"] == "desktop"]
    m_col, c_col = st.columns(2)
    for col, name, d, color in ((m_col, "Mobile", mob, "#5b5ff7"), (c_col, "Computer", comp, "#ff7043")):
        col.markdown(
            f"""<div class="kpi" style="background:{color}; text-align:center">
            <div class="label">{name}</div>
            <div class="delta">Impressions</div><div class="value">{d['impressions'].sum():,.0f}</div>
            <div class="delta">Link Clicks</div><div class="value">{d['clicks'].sum():,.0f}</div></div>""",
            unsafe_allow_html=True,
        )

with col_state:
    st.subheader("State performance")
    by_state = cur.groupby("state")[["impressions", "clicks", "spend"]].sum().reset_index()
    by_state["lat"] = by_state["state"].map(lambda s: STATES[s][0])
    by_state["lon"] = by_state["state"].map(lambda s: STATES[s][1])
    geo = px.scatter_geo(by_state, lat="lat", lon="lon", size="impressions", color="impressions",
                         hover_name="state", color_continuous_scale="YlOrRd", size_max=40)
    geo.update_geos(scope="asia", fitbounds="locations", showcountries=True)
    geo.update_layout(height=300, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(geo, use_container_width=True)
    st.dataframe(by_state.sort_values("impressions", ascending=False)[["state", "impressions", "clicks"]],
                 hide_index=True, use_container_width=True, height=180)

    if not by_state.empty:
        top = by_state.sort_values("impressions", ascending=False).iloc[0]
        ctr = top["clicks"] / top["impressions"] * 100 if top["impressions"] else 0
        cpc = top["spend"] / top["clicks"] if top["clicks"] else 0
        st.markdown(
            f"""<div class="panel"><h4>Top performing State: {top['state']}</h4>
            Impressions {top['impressions']:,.0f} &nbsp;|&nbsp; Link Clicks {top['clicks']:,.0f}
            &nbsp;|&nbsp; Spent {top['spend']:,.2f} &nbsp;|&nbsp; CTR {ctr:.2f}% &nbsp;|&nbsp; CPC {cpc:.2f}</div>""",
            unsafe_allow_html=True,
        )
