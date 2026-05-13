"""
Page 4 — 🤖 AI Insights: Full health report generation + monitoring alerts.
"""

import streamlit as st

import config
import storage
import ai_analyzer
import sidebar
import ui_helpers

st.set_page_config(page_title="AI Insights — NAPA Monitor", page_icon="🤖", layout="wide")
sidebar.render_sidebar()
st.markdown("# 🤖 AI Insights")
st.caption("AI-powered health analysis and monitoring alerts via OpenRouter")

# ── Load Latest Metrics ──────────────────────────────────
latest_sys = storage.read_latest(config.SYSTEM_METRICS_FILE)
latest_conn = storage.read_latest(config.CONNECTION_METRICS_FILE)
latest_slow = storage.read_latest(config.SLOW_QUERIES_FILE)

ui_helpers.no_data_guard(latest_sys or latest_conn)

# ── Monitoring Alerts ────────────────────────────────────
st.markdown("### 🚨 Monitoring Alerts")

# Build a combined metrics dict for alert checking
alert_metrics = {}
if latest_sys:
    alert_metrics.update({
        "cpu_percent": latest_sys.get("cpu_percent"),
        "memory_percent": latest_sys.get("memory_percent"),
        "cache_hit_ratio": latest_sys.get("cache_hit_ratio"),
    })
if latest_conn:
    alert_metrics.update({
        "idle_in_tx": latest_conn.get("idle_in_tx"),
        "total": latest_conn.get("total"),
    })

alerts = ai_analyzer.check_alerts(alert_metrics)

if alerts:
    for alert in alerts:
        if alert["level"] == "critical":
            st.error(f"🔴 **CRITICAL — {alert['metric']}**: {alert['message']}")
        else:
            st.warning(f"🟡 **WARNING — {alert['metric']}**: {alert['message']}")
else:
    st.success("✅ All metrics are within normal thresholds.")

# Show current thresholds
with st.expander("⚙️ Alert Thresholds"):
    st.markdown("""
    | Metric | Warning | Critical |
    |--------|---------|----------|
    | CPU Usage | > 80% | > 90% |
    | Memory Usage | > 80% | > 90% |
    | Cache Hit Ratio | < 95% | < 90% |
    | Idle in Transaction | > 5 | — |
    | Total Connections | > 80 | — |
    """)

st.markdown("---")

# ── AI Health Report ─────────────────────────────────────
st.markdown("### 🧠 AI Health Report")
st.markdown("Generate a comprehensive analysis of your database health using AI.")

# Show what data will be sent
with st.expander("📋 Data that will be sent to AI"):
    col1, col2 = st.columns(2)
    with col1:
        if latest_sys:
            st.markdown("**System Metrics**")
            st.json({
                "cpu_percent": latest_sys.get("cpu_percent"),
                "memory_percent": latest_sys.get("memory_percent"),
                "db_size_mb": latest_sys.get("db_size_mb"),
                "cache_hit_ratio": latest_sys.get("cache_hit_ratio"),
                "tx_commit": latest_sys.get("tx_commit"),
                "tx_rollback": latest_sys.get("tx_rollback"),
            })
    with col2:
        if latest_conn:
            st.markdown("**Connection Metrics**")
            st.json(latest_conn)

# Build the full metrics payload for AI
ai_metrics = {}
if latest_sys:
    ai_metrics.update(latest_sys)
if latest_conn:
    ai_metrics.update(latest_conn)
if latest_slow and latest_slow.get("queries"):
    ai_metrics["slow_queries"] = latest_slow["queries"]
if latest_sys and latest_sys.get("table_bloat"):
    ai_metrics["table_bloat"] = latest_sys["table_bloat"]

# Initialize session state for the health report
if "health_report" not in st.session_state:
    st.session_state.health_report = None

generate = ui_helpers.ai_action_button(
    "🚀 Generate Health Report", button_key="generate_health_report"
)

if generate:
    with st.spinner("🧠 AI is analyzing your database — this may take 15-30 seconds..."):
        st.session_state.health_report = ai_analyzer.generate_health_report(ai_metrics)

# Render stored result (persists across re-runs)
if st.session_state.health_report is not None:
    st.markdown("---")
    ui_helpers.render_ai_result(
        st.session_state.health_report,
        toggle_label="🧠 Show Full AI Analysis Report",
        toggle_key="toggle_ai_insights",
        usage_layout="columns",
    )

# ── Footer ───────────────────────────────────────────────
st.markdown("---")
st.caption(
    "AI insights are generated via [OpenRouter](https://openrouter.ai) and should be "
    "treated as suggestions, not definitive diagnoses. Always verify recommendations "
    "before applying to production systems."
)

