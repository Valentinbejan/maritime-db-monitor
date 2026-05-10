"""
Page 1 — 📊 Overview: Live metric cards, connection breakdown, transaction rates.
Auto-refreshes every 30s using @st.fragment.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone

import config
import storage
import sidebar

st.set_page_config(page_title="Overview — NAPA Monitor", page_icon="📊", layout="wide")
sidebar.render_sidebar()

# ── Custom CSS ───────────────────────────────────────────
st.markdown("""
<style>
    .metric-header {
        font-size: 0.85rem;
        color: #8892B0;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.2rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #CCD6F6;
    }
    .metric-card {
        background: linear-gradient(135deg, #112240 0%, #1a2d50 100%);
        border: 1px solid #233554;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #CCD6F6;
        margin: 1.5rem 0 0.8rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("# 📊 Overview")

# Manual refresh button (st.fragment requires Streamlit 1.37+)
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.caption("Live database health metrics")
with col_btn:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()


def live_metrics():
    """Render live metric cards and charts."""

    latest_sys = storage.read_latest(config.SYSTEM_METRICS_FILE)
    latest_conn = storage.read_latest(config.CONNECTION_METRICS_FILE)

    if not latest_sys and not latest_conn:
        st.warning("⏳ No metrics data yet. Make sure `python collector.py` is running.")
        return

    # ── Metric Cards Row ─────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)

    if latest_sys:
        with c1:
            cpu = latest_sys.get("cpu_percent", 0)
            st.metric("CPU Usage", f"{cpu:.1f}%")
        with c2:
            mem = latest_sys.get("memory_percent", 0)
            st.metric("Memory Usage", f"{mem:.1f}%")
        with c3:
            db_mb = latest_sys.get("db_size_mb", 0)
            st.metric("DB Size", f"{db_mb} MB")
        with c4:
            cache = latest_sys.get("cache_hit_ratio", 0)
            st.metric("Cache Hit Ratio", f"{cache:.2%}")
        with c5:
            if latest_conn:
                st.metric("Active Connections", latest_conn.get("active", 0))
            else:
                st.metric("Active Connections", "—")

    # ── Connection Breakdown ─────────────────────────────
    st.markdown('<div class="section-title">Connection Breakdown</div>', unsafe_allow_html=True)

    if latest_conn:
        conn_col1, conn_col2 = st.columns([1, 2])

        with conn_col1:
            labels = ["Active", "Idle", "Idle in Transaction"]
            values = [
                latest_conn.get("active", 0),
                latest_conn.get("idle", 0),
                latest_conn.get("idle_in_tx", 0),
            ]
            colors = ["#00B4D8", "#FFB703", "#FF6B6B"]

            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                marker=dict(colors=colors),
                textinfo="label+value",
                textfont=dict(size=13, color="#CCD6F6"),
            )])
            fig.update_layout(
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=20, b=20, l=20, r=20),
                height=280,
            )
            st.plotly_chart(fig, use_container_width=True)

        with conn_col2:
            # Connection history line chart
            conn_data = storage.read_metrics(config.CONNECTION_METRICS_FILE)
            if conn_data:
                df = pd.DataFrame(conn_data)
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.sort_values("timestamp")

                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=df["timestamp"], y=df["active"],
                    name="Active", line=dict(color="#00B4D8", width=2),
                    fill="tozeroy", fillcolor="rgba(0,180,216,0.1)",
                ))
                fig2.add_trace(go.Scatter(
                    x=df["timestamp"], y=df["idle"],
                    name="Idle", line=dict(color="#FFB703", width=2),
                ))
                fig2.add_trace(go.Scatter(
                    x=df["timestamp"], y=df["idle_in_tx"],
                    name="Idle in TX", line=dict(color="#FF6B6B", width=2),
                ))
                fig2.update_layout(
                    title="Connection History",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#8892B0"),
                    xaxis=dict(gridcolor="#233554"),
                    yaxis=dict(gridcolor="#233554"),
                    legend=dict(orientation="h", y=-0.2),
                    margin=dict(t=40, b=40, l=40, r=20),
                    height=280,
                )
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Collecting connection history...")

    # ── Transaction Rate ─────────────────────────────────
    st.markdown('<div class="section-title">Transaction Rate</div>', unsafe_allow_html=True)

    sys_data = storage.read_metrics(config.SYSTEM_METRICS_FILE)
    if sys_data and len(sys_data) >= 2:
        df = pd.DataFrame(sys_data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(
            x=df["timestamp"], y=df["tx_commit"],
            name="Commits", line=dict(color="#64FFDA", width=2),
            fill="tozeroy", fillcolor="rgba(100,255,218,0.08)",
        ))
        fig3.add_trace(go.Scatter(
            x=df["timestamp"], y=df["tx_rollback"],
            name="Rollbacks", line=dict(color="#FF6B6B", width=2),
            fill="tozeroy", fillcolor="rgba(255,107,107,0.08)",
        ))
        fig3.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8892B0"),
            xaxis=dict(gridcolor="#233554"),
            yaxis=dict(gridcolor="#233554", title="Cumulative Count"),
            legend=dict(orientation="h", y=-0.2),
            margin=dict(t=20, b=40, l=40, r=20),
            height=300,
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Collecting transaction data...")

    # ── Table Bloat ──────────────────────────────────────
    if latest_sys and latest_sys.get("table_bloat"):
        st.markdown('<div class="section-title">Table Bloat (Dead Tuples)</div>', unsafe_allow_html=True)
        bloat_df = pd.DataFrame(latest_sys["table_bloat"])
        if not bloat_df.empty:
            bloat_df.columns = ["Table", "Live Tuples", "Dead Tuples", "Dead Ratio"]
            st.dataframe(bloat_df, use_container_width=True, hide_index=True)


# Run the fragment
live_metrics()
