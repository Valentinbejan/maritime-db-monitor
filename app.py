"""
app.py — Streamlit entry point / landing page for the NAPA Maritime DB Monitor.

This is the HOME page. It does NOT start or import the collector.
The collector (collector.py) must be run separately: python collector.py

Run this dashboard with:  streamlit run app.py
"""

import streamlit as st

import config
import storage
import sidebar

# ── Page Configuration ───────────────────────────────────
st.set_page_config(
    page_title="NAPA Maritime DB Monitor",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Shared Sidebar ───────────────────────────────────────
sidebar.render_sidebar()

# ── Custom CSS ───────────────────────────────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #00E5FF 0%, #00B8D4 50%, #0091EA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.1rem;
        color: #8892B0;
        margin-bottom: 2rem;
    }
    .feature-card {
        background: linear-gradient(135deg, #112240 0%, #1a2d50 100%);
        border: 1px solid #233554;
        border-radius: 12px;
        padding: 1.5rem;
        height: 100%;
        transition: border-color 0.3s ease;
    }
    .feature-card:hover {
        border-color: #00E5FF;
    }
    .feature-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    .feature-name {
        font-size: 1.1rem;
        font-weight: 600;
        color: #CCD6F6;
        margin-bottom: 0.3rem;
    }
    .feature-desc {
        font-size: 0.9rem;
        color: #8892B0;
    }
    .info-box {
        background: rgba(0, 229, 255, 0.05);
        border-left: 3px solid #00E5FF;
        border-radius: 0 8px 8px 0;
        padding: 1rem 1.2rem;
        margin: 1rem 0;
        color: #8892B0;
    }
</style>
""", unsafe_allow_html=True)

# ── Main Content ─────────────────────────────────────────
st.markdown('<div class="main-title">NAPA Maritime DB Monitor</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Real-time PostgreSQL health monitoring with AI-powered insights for maritime fleet databases</div>',
    unsafe_allow_html=True,
)

# ── Quick Status Row ─────────────────────────────────────
col1, col2, col3 = st.columns(3)

# Read latest metrics for the status cards
latest_system = storage.read_latest(config.SYSTEM_METRICS_FILE)
latest_conns = storage.read_latest(config.CONNECTION_METRICS_FILE)

with col1:
    if latest_system:
        st.metric("Database Size", f"{latest_system.get('db_size_mb', '?')} MB")
    else:
        st.metric("Database Size", "—")

with col2:
    if latest_system:
        ratio = latest_system.get("cache_hit_ratio", 0)
        st.metric("Cache Hit Ratio", f"{ratio:.2%}" if isinstance(ratio, (int, float)) else "—")
    else:
        st.metric("Cache Hit Ratio", "—")

with col3:
    if latest_conns:
        st.metric("Active Connections", latest_conns.get("active", "—"))
    else:
        st.metric("Active Connections", "—")

st.markdown("")

# ── Getting Started ──────────────────────────────────────
st.markdown('<div class="info-box">', unsafe_allow_html=True)
st.markdown("""
**Quick Start** — Run these in two separate terminals:

1. **Start the database:**  `docker compose up -d`
2. **Start the collector:**  `python collector.py`
3. **Start the dashboard:**  `streamlit run app.py`

Use the sidebar pages to explore metrics, slow queries, trends, and AI insights.
""")
st.markdown('</div>', unsafe_allow_html=True)

# ── Feature Cards ────────────────────────────────────────
st.markdown("### Dashboard Pages")
st.markdown("")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">📊</div>
        <div class="feature-name">Overview</div>
        <div class="feature-desc">Live metric cards, connection breakdown, and transaction rates</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🐢</div>
        <div class="feature-name">Slow Queries</div>
        <div class="feature-desc">Top slow queries with per-query AI analysis and optimization tips</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">📈</div>
        <div class="feature-name">Trends</div>
        <div class="feature-desc">Historical charts for CPU, memory, connections, and cache ratios</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")
c4, c5, c6 = st.columns(3)

with c4:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🤖</div>
        <div class="feature-name">AI Insights</div>
        <div class="feature-desc">AI-powered health reports, anomaly detection, and monitoring alerts</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">💬</div>
        <div class="feature-name">DBA Chat</div>
        <div class="feature-desc">Context-aware AI chat with live schema and metrics injected</div>
    </div>
    """, unsafe_allow_html=True)

with c6:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🗂️</div>
        <div class="feature-name">Index Health</div>
        <div class="feature-desc">Missing & unused index detection with AI optimization advice</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")
c7, _, _ = st.columns(3)

with c7:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">🧹</div>
        <div class="feature-name">Autovacuum</div>
        <div class="feature-desc">Track vacuum activity, detect stale tables, and tune autovacuum config</div>
    </div>
    """, unsafe_allow_html=True)

# ── Footer ───────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #4A5568; font-size: 0.85rem;">'
    '🚢 NAPA Maritime Database Monitor — Built with Streamlit & OpenRouter AI'
    '</div>',
    unsafe_allow_html=True,
)
