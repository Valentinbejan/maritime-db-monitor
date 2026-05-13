"""
Page 7 — 🧹 Autovacuum: Track vacuum activity, stale tables, and configuration.

Answers the DBA's critical question: "Is autovacuum actually running?"
Shows:
  - Currently active autovacuum workers
  - Per-table vacuum/analyze timestamps with staleness alerts
  - Dead tuple hotspots cross-referenced with vacuum history
  - Autovacuum configuration parameters
  - AI analysis for vacuum tuning recommendations
"""

import streamlit as st
import pandas as pd

import config
import storage
import ai_analyzer
import sidebar
import ui_helpers

st.set_page_config(page_title="Autovacuum — NAPA Monitor", page_icon="🧹", layout="wide")
sidebar.render_sidebar()

st.markdown("# 🧹 Autovacuum Tracking")
st.caption("Monitor vacuum activity, detect stale tables, and tune autovacuum configuration")

# ── Load Latest Autovacuum Snapshot ───────────────────────
latest = storage.read_latest(config.AUTOVACUUM_FILE)
ui_helpers.no_data_guard(latest, source_label="autovacuum")

active_workers = latest.get("active_workers", [])
table_stats = latest.get("table_stats", [])
settings = latest.get("settings", [])
snapshot_time = latest.get("timestamp", "Unknown")
st.caption(f"Snapshot from: {snapshot_time}")


# ── Helper: format seconds to human-readable ─────────────

def _fmt_age(seconds):
    """Convert seconds to a human-readable age string."""
    if seconds is None:
        return "Never"
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.0f}s ago"
    if seconds < 3600:
        return f"{seconds / 60:.0f}m ago"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h ago"
    return f"{seconds / 86400:.1f}d ago"


# ── Summary Metrics ──────────────────────────────────────
total_dead = sum(int(t.get("n_dead_tup", 0)) for t in table_stats)
stale_tables = [
    t for t in table_stats
    if t.get("seconds_since_vacuum") is not None
    and float(t["seconds_since_vacuum"]) > 86400
]
never_vacuumed = [
    t for t in table_stats
    if t.get("last_any_vacuum") is None
]

col1, col2, col3, col4 = st.columns(4)
with col1:
    if active_workers:
        st.metric("🔄 Active Workers", len(active_workers))
    else:
        st.metric("🔄 Active Workers", "0", help="No autovacuum workers running right now")
with col2:
    st.metric("💀 Total Dead Tuples", f"{total_dead:,}")
with col3:
    st.metric("⚠️ Stale Tables (>24h)", len(stale_tables))
with col4:
    st.metric("🚫 Never Vacuumed", len(never_vacuumed))

st.markdown("---")

# ── Active Autovacuum Workers ────────────────────────────
st.markdown("### 🔄 Active Autovacuum Workers")

if active_workers:
    st.success(f"✅ Autovacuum is running — {len(active_workers)} worker(s) active right now.")
    for w in active_workers:
        query_preview = str(w.get("query", ""))[:120]
        duration = w.get("duration", "?")
        st.markdown(
            f"- **PID {w.get('pid', '?')}** — `{query_preview}` "
            f"(running for {duration})"
        )
else:
    st.info(
        "💤 No autovacuum workers active right now. This is normal — "
        "autovacuum runs periodically when tables accumulate enough dead tuples."
    )

# Check if autovacuum is enabled
av_enabled = next((s for s in settings if s["name"] == "autovacuum"), None)
if av_enabled and av_enabled.get("setting") == "off":
    st.error(
        "🔴 **CRITICAL: Autovacuum is DISABLED!** "
        "This will cause table bloat to grow unbounded. "
        "Run `ALTER SYSTEM SET autovacuum = on; SELECT pg_reload_conf();` immediately."
    )

st.markdown("---")

# ── Per-Table Vacuum Status ──────────────────────────────
st.markdown("### 📋 Per-Table Vacuum & Analyze Status")
st.markdown(
    "Tables sorted by dead tuples. Red = stale (not vacuumed in >24h), "
    "Yellow = aging (>6h), Green = healthy."
)

if table_stats:
    display_data = []
    for t in table_stats:
        secs_vac = t.get("seconds_since_vacuum")
        secs_ana = t.get("seconds_since_analyze")

        display_data.append({
            "Table": t.get("table_name", "?"),
            "Live Rows": int(t.get("n_live_tup", 0)),
            "Dead Tuples": int(t.get("n_dead_tup", 0)),
            "Dead %": float(t.get("dead_pct", 0)),
            "Last Vacuum": _fmt_age(secs_vac),
            "Last Analyze": _fmt_age(secs_ana),
            "Vacuum Runs": int(t.get("vacuum_count", 0)) + int(t.get("autovacuum_count", 0)),
            "Analyze Runs": int(t.get("analyze_count", 0)) + int(t.get("autoanalyze_count", 0)),
        })

    df = pd.DataFrame(display_data)

    styled = df.style.map(
        lambda v: ui_helpers.threshold_color(v, warn=10, crit=20),
        subset=["Dead %"],
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Detail expanders for problem tables
    problem_tables = [
        t for t in table_stats
        if (t.get("seconds_since_vacuum") is not None and float(t["seconds_since_vacuum"]) > 21600)
        or t.get("last_any_vacuum") is None
        or float(t.get("dead_pct", 0)) > 10
    ]

    if problem_tables:
        st.markdown("#### ⚠️ Tables Needing Attention")

        for t in problem_tables:
            table = t.get("table_name", "?")
            dead = int(t.get("n_dead_tup", 0))
            dead_pct = float(t.get("dead_pct", 0))
            secs = t.get("seconds_since_vacuum")

            if t.get("last_any_vacuum") is None:
                badge = "🚫"
                status = "Never vacuumed"
            elif secs and float(secs) > 86400:
                badge = "🔴"
                status = f"Stale — last vacuum {_fmt_age(secs)}"
            elif secs and float(secs) > 21600:
                badge = "🟡"
                status = f"Aging — last vacuum {_fmt_age(secs)}"
            elif dead_pct > 10:
                badge = "🟡"
                status = f"High bloat — {dead_pct:.1f}% dead"
            else:
                badge = "🟢"
                status = "OK"

            with st.expander(f"{badge} {table} — {dead:,} dead tuples, {status}"):
                dc1, dc2, dc3, dc4 = st.columns(4)
                with dc1:
                    st.metric("Live Rows", f"{int(t.get('n_live_tup', 0)):,}")
                with dc2:
                    st.metric("Dead Tuples", f"{dead:,}")
                with dc3:
                    st.metric("Dead %", f"{dead_pct:.2f}%")
                with dc4:
                    total_vac = int(t.get("vacuum_count", 0)) + int(t.get("autovacuum_count", 0))
                    st.metric("Total Vacuums", total_vac)

                vc1, vc2 = st.columns(2)
                with vc1:
                    st.markdown("**Vacuum History**")
                    st.markdown(f"- Manual: {t.get('vacuum_count', 0)} runs")
                    st.markdown(f"- Auto: {t.get('autovacuum_count', 0)} runs")
                    last_v = t.get("last_any_vacuum")
                    st.markdown(f"- Last: {last_v if last_v else 'Never'}")
                with vc2:
                    st.markdown("**Analyze History**")
                    st.markdown(f"- Manual: {t.get('analyze_count', 0)} runs")
                    st.markdown(f"- Auto: {t.get('autoanalyze_count', 0)} runs")
                    last_a = t.get("last_any_analyze")
                    st.markdown(f"- Last: {last_a if last_a else 'Never'}")

                # Manual vacuum suggestion
                st.code(
                    f"-- Force a manual vacuum + analyze on this table:\n"
                    f"VACUUM (VERBOSE, ANALYZE) {table};",
                    language="sql",
                )
else:
    st.info("No table statistics available.")

st.markdown("---")

# ── Autovacuum Configuration ─────────────────────────────
st.markdown("### ⚙️ Autovacuum Configuration")

if settings:
    config_data = []
    for s in settings:
        unit = s.get("unit") or ""
        config_data.append({
            "Parameter": s.get("name", "?"),
            "Value": f"{s.get('setting', '?')} {unit}".strip(),
            "Description": s.get("short_desc", ""),
        })

    df_config = pd.DataFrame(config_data)
    st.dataframe(df_config, use_container_width=True, hide_index=True)

    with st.expander("📖 What do these settings mean?"):
        st.markdown("""
| Parameter | What it controls |
|-----------|-----------------|
| `autovacuum` | Master switch — on/off |
| `autovacuum_max_workers` | Max parallel vacuum workers |
| `autovacuum_naptime` | Seconds between autovacuum checks |
| `autovacuum_vacuum_threshold` | Min dead tuples before vacuum triggers |
| `autovacuum_vacuum_scale_factor` | Fraction of table size added to threshold |
| `autovacuum_analyze_threshold` | Min changed tuples before analyze triggers |
| `autovacuum_analyze_scale_factor` | Fraction of table size added to analyze threshold |
| `autovacuum_vacuum_cost_delay` | Throttle delay (ms) — higher = slower vacuum |
| `autovacuum_vacuum_cost_limit` | Cost budget per round — higher = more aggressive |

**Formula:** A table gets vacuumed when `dead_tuples > threshold + scale_factor × n_live_tup`
        """)
else:
    st.info("Could not retrieve autovacuum settings.")

st.markdown("---")

# ── AI Analysis ──────────────────────────────────────────
st.markdown("### 🤖 AI Vacuum Tuning")
st.markdown("Get AI-powered recommendations for your autovacuum configuration and table maintenance.")

if "vacuum_ai_result" not in st.session_state:
    st.session_state.vacuum_ai_result = None

analyze = ui_helpers.ai_action_button(
    "🧠 Analyze Vacuum Health", button_key="analyze_vacuum_health"
)

if analyze:
    # Build context
    worker_text = f"{len(active_workers)} workers active" if active_workers else "No workers active"

    table_lines = []
    for t in table_stats[:15]:
        secs = t.get("seconds_since_vacuum")
        table_lines.append(
            f"- {t.get('table_name')}: {t.get('n_live_tup', 0)} live, "
            f"{t.get('n_dead_tup', 0)} dead ({t.get('dead_pct', 0)}%), "
            f"last_vacuum={_fmt_age(secs)}, "
            f"auto_count={t.get('autovacuum_count', 0)}"
        )
    table_text = "\n".join(table_lines) if table_lines else "No tables found."

    settings_text = "\n".join(
        f"- {s.get('name')}: {s.get('setting')} {s.get('unit', '')}"
        for s in settings
    ) if settings else "Settings unavailable."

    user_prompt = f"""Analyze the autovacuum health of our maritime fleet PostgreSQL database.

## Current Autovacuum Workers
{worker_text}

## Per-Table Vacuum Status (sorted by dead tuples)
{table_text}

## Stale Tables (not vacuumed in >24h)
{len(stale_tables)} tables

## Never Vacuumed
{len(never_vacuumed)} tables

## Autovacuum Configuration
{settings_text}

Please provide:
1. **Autovacuum Health Assessment** — is autovacuum running effectively?
2. **Stale Table Remediation** — which tables need immediate VACUUM ANALYZE and why
3. **Configuration Tuning** — specific ALTER SYSTEM commands to improve vacuum behavior for this maritime workload (high-volume telemetry inserts, time-series data)
4. **Dead Tuple Analysis** — are the bloat levels acceptable, and what's causing them?
5. **Monitoring Advice** — what thresholds should trigger alerts for this database
"""

    with st.spinner("🧠 AI is analyzing your vacuum health..."):
        st.session_state.vacuum_ai_result = ai_analyzer.call_llm(
            ai_analyzer.build_system_prompt(), user_prompt
        )

# Render stored result
if st.session_state.vacuum_ai_result is not None:
    ui_helpers.render_ai_result(
        st.session_state.vacuum_ai_result,
        toggle_label="🧹 Show AI Vacuum Tuning Recommendations",
        toggle_key="toggle_ai_vacuum",
    )
