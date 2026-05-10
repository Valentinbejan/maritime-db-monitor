"""
Page 3 — 📈 Trends: Historical charts with time-range selector.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone

import config
import storage
import sidebar

st.set_page_config(page_title="Trends — NAPA Monitor", page_icon="📈", layout="wide")
sidebar.render_sidebar()
st.markdown("# 📈 Historical Trends")
st.caption("Monitor database and system performance over time")

# ── Time Range Selector ──────────────────────────────────
time_opts = {
    "Last 30 min": timedelta(minutes=30),
    "Last 1 hour": timedelta(hours=1),
    "Last 6 hours": timedelta(hours=6),
    "Last 24 hours": timedelta(hours=24),
    "Last 7 days": timedelta(days=7),
    "All data": None,
}
sel = st.selectbox("Time Range", list(time_opts.keys()), index=1)
delta = time_opts[sel]
since = datetime.now(timezone.utc) - delta if delta else None

sys_data = storage.read_metrics(config.SYSTEM_METRICS_FILE, since=since)
conn_data = storage.read_metrics(config.CONNECTION_METRICS_FILE, since=since)

if not sys_data and not conn_data:
    st.warning("⏳ No data yet. Run `python collector.py`.")
    st.stop()

st.caption(f"{len(sys_data)} system / {len(conn_data)} connection samples")

CHART = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8892B0"), margin=dict(t=45, b=50, l=50, r=20),
    hovermode="x unified", height=320,
)
GRID = dict(gridcolor="#233554")

# ── System Charts ────────────────────────────────────────
if sys_data:
    df = pd.DataFrame(sys_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["cpu_percent"], name="CPU %",
                                 line=dict(color="#00E5FF", width=2), fill="tozeroy",
                                 fillcolor="rgba(0,229,255,0.08)"))
        fig.add_hline(y=80, line_dash="dash", line_color="#FFD93D",
                      annotation_text="Warning 80%", annotation_font_color="#FFD93D")
        fig.update_layout(title="🖥️ CPU Usage", yaxis=dict(title="%", **GRID),
                          xaxis=GRID, **CHART)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["memory_percent"], name="Memory %",
                                 line=dict(color="#64FFDA", width=2), fill="tozeroy",
                                 fillcolor="rgba(100,255,218,0.08)"))
        fig.add_hline(y=80, line_dash="dash", line_color="#FFD93D",
                      annotation_text="Warning 80%", annotation_font_color="#FFD93D")
        fig.update_layout(title="🧠 Memory Usage", yaxis=dict(title="%", **GRID),
                          xaxis=GRID, **CHART)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["cache_hit_ratio"], name="Cache Hit",
                             line=dict(color="#BB86FC", width=2)))
    fig.add_hline(y=0.95, line_dash="dash", line_color="#FFD93D",
                  annotation_text="Optimal 95%", annotation_font_color="#FFD93D")
    lo = max(0, df["cache_hit_ratio"].min() - 0.01)
    fig.update_layout(title="💾 Cache Hit Ratio", yaxis=dict(title="Ratio", range=[lo, 1.001], **GRID),
                      xaxis=GRID, **CHART)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["db_size_mb"], name="DB Size",
                             line=dict(color="#FF9800", width=2), fill="tozeroy",
                             fillcolor="rgba(255,152,0,0.08)"))
    fig.update_layout(title="📦 Database Size", yaxis=dict(title="MB", **GRID),
                      xaxis=GRID, **CHART)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    c3, c4 = st.columns(2)
    with c3:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["tx_commit"], name="Commits",
                                 line=dict(color="#64FFDA", width=2)))
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["tx_rollback"], name="Rollbacks",
                                 line=dict(color="#FF6B6B", width=2)))
        fig.update_layout(title="📝 Transactions", yaxis=dict(title="Count", **GRID),
                          xaxis=GRID, legend=dict(orientation="h", y=-0.25), **CHART)
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        if len(df) >= 2:
            dr = df.copy()
            dr["c_rate"] = dr["tx_commit"].diff().clip(lower=0)
            dr["r_rate"] = dr["tx_rollback"].diff().clip(lower=0)
            dr = dr.dropna()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=dr["timestamp"], y=dr["c_rate"], name="Commit Rate",
                                     line=dict(color="#64FFDA", width=2)))
            fig.add_trace(go.Scatter(x=dr["timestamp"], y=dr["r_rate"], name="Rollback Rate",
                                     line=dict(color="#FF6B6B", width=2)))
            fig.update_layout(title="⚡ TX Rate (Δ/interval)", yaxis=dict(title="Δ", **GRID),
                              xaxis=GRID, legend=dict(orientation="h", y=-0.25), **CHART)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Need more data for rate calc.")

# ── Connection Charts ────────────────────────────────────
st.markdown("---")
if conn_data:
    df_c = pd.DataFrame(conn_data)
    df_c["timestamp"] = pd.to_datetime(df_c["timestamp"])
    df_c = df_c.sort_values("timestamp")
    fig = go.Figure()
    for col, clr in [("active","#00E5FF"),("idle","#64FFDA"),("idle_in_tx","#FF6B6B"),("total","#8892B0")]:
        fig.add_trace(go.Scatter(x=df_c["timestamp"], y=df_c[col], name=col.replace("_"," ").title(),
                                 line=dict(color=clr, width=2)))
    fig.update_layout(title="🔌 Connections Over Time", yaxis=dict(title="Count", **GRID),
                      xaxis=GRID, legend=dict(orientation="h", y=-0.25), **CHART)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No connection data for selected range.")
