"""
Page 2 — 🐢 Slow Queries: Top slow queries with per-query AI analysis.
"""

import streamlit as st
import pandas as pd

import config
import storage
import db
import ai_analyzer
import sidebar
import ui_helpers

st.set_page_config(page_title="Slow Queries — NAPA Monitor", page_icon="🐢", layout="wide")
sidebar.render_sidebar()

st.markdown("# 🐢 Slow Queries")
st.caption("Top slow queries from pg_stat_statements — click 'Analyze with AI' for optimization tips")

# ── Load Latest Slow Query Snapshot ──────────────────────
latest = storage.read_latest(config.SLOW_QUERIES_FILE)

if not latest or not latest.get("queries"):
    st.warning("⏳ No slow query data yet. Make sure `python collector.py` is running.")
    st.stop()

queries = latest["queries"]
snapshot_time = latest.get("timestamp", "Unknown")
st.caption(f"Snapshot from: {snapshot_time}")

# ── Summary Metrics ──────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Queries Tracked", len(queries))
with col2:
    if queries:
        slowest = max(float(q.get("mean_exec_time_ms", 0)) for q in queries)
        st.metric("Slowest (Mean)", f"{slowest:.2f} ms")
    else:
        st.metric("Slowest (Mean)", "—")
with col3:
    if queries:
        total_calls = sum(int(q.get("calls", 0)) for q in queries)
        st.metric("Total Calls", f"{total_calls:,}")
    else:
        st.metric("Total Calls", "—")

st.markdown("---")

# ── Queries Table ────────────────────────────────────────
# Build a clean DataFrame for display
display_data = []
for i, q in enumerate(queries):
    query_text = q.get("query", "")
    display_data.append({
        "#": i + 1,
        "Query (truncated)": query_text[:100] + ("..." if len(query_text) > 100 else ""),
        "Calls": q.get("calls", 0),
        "Mean Time (ms)": q.get("mean_exec_time_ms", 0),
        "Total Time (ms)": q.get("total_exec_time_ms", 0),
        "Rows": q.get("rows", 0),
    })

df = pd.DataFrame(display_data)

# Color-code by mean execution time
def highlight_slow(val):
    if isinstance(val, (int, float)):
        if val > 100:
            return "color: #FF6B6B; font-weight: 600"
        elif val > 10:
            return "color: #FFD93D; font-weight: 600"
        else:
            return "color: #64FFDA"
    return ""

styled_df = df.style.map(highlight_slow, subset=["Mean Time (ms)"])
st.dataframe(styled_df, use_container_width=True, hide_index=True, height=400)

# ── Per-Query Detail & AI Analysis ───────────────────────
st.markdown("---")
st.markdown("### 🔍 Query Details & AI Analysis")

# Initialize session state for AI results
if "ai_results" not in st.session_state:
    st.session_state.ai_results = {}

for i, q in enumerate(queries):
    query_text = q.get("query", "N/A")
    mean_ms = q.get("mean_exec_time_ms", 0)

    # Color indicator based on severity
    if mean_ms > 100:
        badge = "🔴"
    elif mean_ms > 10:
        badge = "🟡"
    else:
        badge = "🟢"

    with st.expander(f"{badge} Query #{i+1} — Mean: {mean_ms:.2f}ms | Calls: {q.get('calls', 0)}"):
        st.code(query_text, language="sql")

        stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
        with stat_col1:
            st.metric("Calls", q.get("calls", 0))
        with stat_col2:
            st.metric("Mean Time", f"{mean_ms:.2f} ms")
        with stat_col3:
            st.metric("Total Time", f"{q.get('total_exec_time_ms', 0):.2f} ms")
        with stat_col4:
            st.metric("Rows", q.get("rows", 0))

        # Action buttons
        result_key = f"ai_result_{i}"
        explain_key = f"explain_result_{i}"
        btn_col1, btn_col2, btn_col3 = st.columns(3)

        with btn_col1:
            analyze_clicked = st.button(
                "🤖 Analyze with AI", key=f"analyze_q_{i}", use_container_width=True
            )

        with btn_col2:
            explain_clicked = st.button(
                "🔬 EXPLAIN AI Analysis", key=f"explain_q_{i}", use_container_width=True
            )

        with btn_col3:
            discuss_clicked = st.button(
                "💬 Discuss in Chat", key=f"discuss_q_{i}", use_container_width=True
            )

        query_stats = {
            "calls": q.get("calls"),
            "mean_exec_time_ms": q.get("mean_exec_time_ms"),
            "total_exec_time_ms": q.get("total_exec_time_ms"),
            "rows": q.get("rows"),
        }

        # Handle Analyze with AI
        if analyze_clicked:
            with st.spinner("🧠 AI is analyzing this query..."):
                result = ai_analyzer.analyze_slow_query(
                    query_text=query_text, stats=query_stats,
                )
            st.session_state.ai_results[result_key] = result

        # Handle EXPLAIN AI Analysis
        if explain_clicked:
            with st.spinner("🔬 Running EXPLAIN ANALYZE on the database..."):
                explain_result = db.run_explain(query_text)

            if explain_result.get("error"):
                st.session_state.ai_results[explain_key] = {
                    "error": f"EXPLAIN failed: {explain_result['error']}",
                    "content": None, "reasoning": None, "usage": {},
                }
            else:
                with st.spinner("🧠 AI is analyzing the execution plan..."):
                    result = ai_analyzer.analyze_explain_plan(
                        query_text=query_text,
                        stats=query_stats,
                        explain_plan=explain_result["plan"],
                    )
                st.session_state.ai_results[explain_key] = result

        # Handle Discuss in Chat — store query context and navigate
        if discuss_clicked:
            chat_msg = (
                f"I'd like to discuss this slow query from our database:\n\n"
                f"```sql\n{query_text}\n```\n\n"
                f"**Execution Statistics:**\n"
                f"- Calls: {q.get('calls', 'N/A')}\n"
                f"- Mean Execution Time: {q.get('mean_exec_time_ms', 'N/A')} ms\n"
                f"- Total Execution Time: {q.get('total_exec_time_ms', 'N/A')} ms\n"
                f"- Rows Returned: {q.get('rows', 'N/A')}\n\n"
                f"Why might this query be slow, and how can I optimize it?"
            )
            st.session_state.chat_pending_query = chat_msg
            st.switch_page("pages/5_DBA_Chat.py")

        # Render stored AI result (persists across re-runs)
        if result_key in st.session_state.ai_results:
            result = st.session_state.ai_results[result_key]

            if result.get("error"):
                st.error(result["error"])
            else:
                if result.get("reasoning"):
                    ui_helpers.render_reasoning_dropdown(result["reasoning"])

                st.markdown("#### 💡 AI Recommendations")
                st.markdown(result.get("content", "No response."))
                ui_helpers.render_token_usage(result.get("usage", {}))

        # Render stored EXPLAIN result (separate from basic AI)
        if explain_key in st.session_state.ai_results:
            result = st.session_state.ai_results[explain_key]

            if result.get("error"):
                st.error(result["error"])
            else:
                if result.get("reasoning"):
                    ui_helpers.render_reasoning_dropdown(result["reasoning"])

                st.markdown("#### 🔬 EXPLAIN Plan Analysis")
                st.markdown(result.get("content", "No response."))
                ui_helpers.render_token_usage(result.get("usage", {}))
