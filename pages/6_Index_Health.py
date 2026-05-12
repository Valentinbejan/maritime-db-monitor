"""
Page 6 — 🗂️ Index Health: Missing & unused index detection.

Shows:
  - Tables likely needing indexes (high sequential scan ratio)
  - Indexes that exist but are never/rarely used (wasting disk + slowing writes)
  - Total wasted disk space from unused indexes
  - AI analysis for index optimization recommendations
"""

import streamlit as st
import pandas as pd

import config
import storage
import ai_analyzer
import sidebar
import ui_helpers

st.set_page_config(page_title="Index Health — NAPA Monitor", page_icon="🗂️", layout="wide")
sidebar.render_sidebar()

st.markdown("# 🗂️ Index Health")
st.caption("Detect missing indexes (slow full-table scans) and unused indexes (wasted disk & slower writes)")

# ── Load Latest Index Health Snapshot ─────────────────────
latest = storage.read_latest(config.INDEX_HEALTH_FILE)

if not latest:
    st.warning("⏳ No index health data yet. Make sure `python collector.py` is running.")
    st.stop()

missing = latest.get("missing_indexes", [])
unused = latest.get("unused_indexes", [])
snapshot_time = latest.get("timestamp", "Unknown")
st.caption(f"Snapshot from: {snapshot_time}")

# ── Summary Metrics ──────────────────────────────────────
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("🔍 Tables Needing Indexes", len(missing))
with col2:
    st.metric("🗑️ Unused Indexes", len(unused))
with col3:
    total_waste = sum(u.get("index_size_bytes", 0) for u in unused)
    if total_waste > 1024 * 1024:
        waste_str = f"{total_waste / (1024 * 1024):.1f} MB"
    elif total_waste > 1024:
        waste_str = f"{total_waste / 1024:.1f} KB"
    else:
        waste_str = f"{total_waste} B"
    st.metric("💾 Wasted Disk Space", waste_str)

st.markdown("---")

# ── Missing Indexes Section ──────────────────────────────
st.markdown("### 🔍 Missing Indexes — Tables with Heavy Sequential Scans")
st.markdown(
    "These tables have more sequential scans (full-table reads) than index scans, "
    "suggesting they need additional indexes for the queries hitting them."
)

if missing:
    display_missing = []
    for m in missing:
        seq_pct = float(m.get("seq_scan_pct", 0))
        display_missing.append({
            "Table": m.get("table_name", "?"),
            "Rows": m.get("row_estimate", 0),
            "Seq Scans": m.get("seq_scan", 0),
            "Index Scans": m.get("idx_scan", 0),
            "Seq Scan %": seq_pct,
            "Rows Read (seq)": m.get("seq_tup_read", 0),
            "Table Size": m.get("table_size", "?"),
        })

    df_missing = pd.DataFrame(display_missing)

    # Color-code the seq scan percentage
    def highlight_seq_pct(val):
        if isinstance(val, (int, float)):
            if val > 90:
                return "color: #FF6B6B; font-weight: 600"
            elif val > 70:
                return "color: #FFD93D; font-weight: 600"
            else:
                return "color: #64FFDA"
        return ""

    styled = df_missing.style.map(highlight_seq_pct, subset=["Seq Scan %"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Detail expanders
    for m in missing:
        table = m.get("table_name", "?")
        seq_pct = float(m.get("seq_scan_pct", 0))
        badge = "🔴" if seq_pct > 90 else ("🟡" if seq_pct > 70 else "🟢")

        with st.expander(f"{badge} {table} — {seq_pct}% sequential scans"):
            dc1, dc2, dc3, dc4 = st.columns(4)
            with dc1:
                st.metric("Rows", f"{m.get('row_estimate', 0):,}")
            with dc2:
                st.metric("Seq Scans", f"{m.get('seq_scan', 0):,}")
            with dc3:
                st.metric("Index Scans", f"{m.get('idx_scan', 0):,}")
            with dc4:
                st.metric("Table Size", m.get("table_size", "?"))

            st.markdown(
                f"**{m.get('seq_tup_read', 0):,}** rows read via sequential scans. "
                f"Adding an index on frequently filtered columns could dramatically reduce this."
            )
else:
    st.success("✅ All tables have healthy index usage — no missing indexes detected.")

st.markdown("---")

# ── Unused Indexes Section ───────────────────────────────
st.markdown("### 🗑️ Unused Indexes — Wasting Disk & Slowing Writes")
st.markdown(
    "These indexes exist but are rarely or never used by any query. "
    "They still consume disk space and slow down every INSERT/UPDATE/DELETE "
    "because PostgreSQL must maintain them. Primary key and unique indexes are excluded."
)

if unused:
    display_unused = []
    for u in unused:
        display_unused.append({
            "Table": u.get("table_name", "?"),
            "Index Name": u.get("index_name", "?"),
            "Scans": u.get("idx_scan", 0),
            "Tuples Read": u.get("idx_tup_read", 0),
            "Index Size": u.get("index_size", "?"),
        })

    df_unused = pd.DataFrame(display_unused)

    # Color-code the scans column
    def highlight_scans(val):
        if isinstance(val, (int, float)):
            if val == 0:
                return "color: #FF6B6B; font-weight: 600"
            elif val < 10:
                return "color: #FFD93D; font-weight: 600"
            else:
                return "color: #64FFDA"
        return ""

    styled_unused = df_unused.style.map(highlight_scans, subset=["Scans"])
    st.dataframe(styled_unused, use_container_width=True, hide_index=True)

    # Drop index suggestions
    st.markdown("#### 🧹 Drop Candidates")
    st.markdown("Review these indexes and consider dropping them if they're truly unused:")

    for u in unused:
        scans = u.get("idx_scan", 0)
        badge = "🔴" if scans == 0 else "🟡"
        idx_name = u.get("index_name", "?")
        table = u.get("table_name", "?")
        size = u.get("index_size", "?")

        with st.expander(f"{badge} {idx_name} on {table} — {scans} scans, {size}"):
            st.code(f"-- Review before dropping!\nDROP INDEX IF EXISTS {idx_name};", language="sql")
            st.caption(
                f"This index on `{table}` has been scanned only **{scans}** times. "
                f"It occupies **{size}** of disk space."
            )
else:
    st.success("✅ All indexes are actively used — no unused indexes detected.")

st.markdown("---")

# ── AI Analysis ──────────────────────────────────────────
st.markdown("### 🤖 AI Index Optimization")
st.markdown("Get AI-powered recommendations for your index strategy.")

if "index_ai_result" not in st.session_state:
    st.session_state.index_ai_result = None

btn_col, model_col = st.columns([1, 2])
with btn_col:
    analyze = st.button(
        "🧠 Analyze Index Health",
        disabled=not config.is_api_ready(),
        type="primary",
        use_container_width=True,
    )
with model_col:
    st.caption(f"Model: `{config.LLM_MODEL}`")

if not config.is_api_ready():
    st.info(
        "🔑 Set `OPENROUTER_API_KEY` in your `.env` file to enable AI analysis. "
        "Get a free key at [openrouter.ai](https://openrouter.ai)."
    )

if analyze:
    # Build the context for AI
    missing_text = ""
    if missing:
        lines = []
        for m in missing:
            lines.append(
                f"- {m.get('table_name')}: {m.get('row_estimate', 0)} rows, "
                f"seq_scan={m.get('seq_scan', 0)}, idx_scan={m.get('idx_scan', 0)}, "
                f"seq_scan_pct={m.get('seq_scan_pct', 0)}%, "
                f"seq_tup_read={m.get('seq_tup_read', 0)}"
            )
        missing_text = "\n".join(lines)
    else:
        missing_text = "None detected."

    unused_text = ""
    if unused:
        lines = []
        for u in unused:
            lines.append(
                f"- {u.get('index_name')} on {u.get('table_name')}: "
                f"scans={u.get('idx_scan', 0)}, size={u.get('index_size', '?')}"
            )
        unused_text = "\n".join(lines)
    else:
        unused_text = "None detected."

    user_prompt = f"""Analyze the following index health data from our maritime fleet PostgreSQL database.

## Tables Likely Missing Indexes (High Sequential Scans)
{missing_text}

## Unused Indexes (Wasting Disk & Slowing Writes)
{unused_text}

Please provide:
1. **Overall Index Health Assessment** — rate the index strategy
2. **Missing Index Recommendations** — specific CREATE INDEX SQL for tables that need them, considering the maritime schema (vessel telemetry, compartment data, etc.)
3. **Safe-to-Drop Indexes** — which unused indexes can be safely dropped, with the DROP INDEX SQL
4. **Write Performance Impact** — estimate how much write performance would improve if unused indexes are removed
5. **Best Practices** — any general indexing advice for this type of maritime data workload
"""

    with st.spinner("🧠 AI is analyzing your index health..."):
        result = ai_analyzer._call_llm(ai_analyzer.build_system_prompt(), user_prompt)
    st.session_state.index_ai_result = result

# Render stored result
if st.session_state.index_ai_result is not None:
    result = st.session_state.index_ai_result

    if result.get("error"):
        st.error(result["error"])
    else:
        if result.get("reasoning"):
            ui_helpers.render_reasoning_dropdown(result["reasoning"])

        if st.toggle("🗂️ Show AI Index Optimization Strategy", value=True, key="toggle_ai_index"):
            st.markdown(result.get("content", "No response generated."))
        ui_helpers.render_token_usage(result.get("usage", {}))
