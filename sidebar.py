"""
sidebar.py — Shared sidebar rendered on every page.

Call render_sidebar() from any page to get the consistent
NAPA Monitor sidebar with collector status, DB info, live
metrics snapshot, and connection breakdown.
"""

import streamlit as st
from datetime import datetime, timezone

import config
import storage


def render_sidebar():
    """Render the shared sidebar. Call this from every page."""

    with st.sidebar:
        st.markdown("### 🚢 NAPA Monitor")
        st.markdown("---")

        # ── Collector Status ─────────────────────────────
        last_modified = storage.get_last_modified(config.SYSTEM_METRICS_FILE)
        if last_modified:
            age_seconds = (datetime.now(timezone.utc) - last_modified).total_seconds()
            if age_seconds < config.COLLECTION_INTERVAL * 3:
                st.markdown(
                    '<span style="color:#64FFDA; font-weight:600;">● Collector Running</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span style="color:#FF6B6B; font-weight:600;">● Collector Stale</span>',
                    unsafe_allow_html=True,
                )
            st.caption(f"Last data: {last_modified.strftime('%H:%M:%S UTC')}")
        else:
            st.markdown(
                '<span style="color:#FF6B6B; font-weight:600;">● No Data Yet</span>',
                unsafe_allow_html=True,
            )
            st.caption("Run: `python collector.py`")

        st.markdown("---")

        # ── Database Info ────────────────────────────────
        st.markdown(
            f"**DB Host:** `{config.DB_HOST}:{config.DB_PORT}`  \n"
            f"**Database:** `{config.DB_NAME}`  \n"
            f"**Interval:** `{config.COLLECTION_INTERVAL}s`  \n"
            f"**AI Model:** `{config.LLM_MODEL}`"
        )

        st.markdown("---")

        # ── Live Metrics Snapshot ────────────────────────
        latest_sys = storage.read_latest(config.SYSTEM_METRICS_FILE)
        latest_conn = storage.read_latest(config.CONNECTION_METRICS_FILE)

        if latest_sys or latest_conn:
            st.markdown("**📊 Live Metrics**")

            if latest_sys:
                cpu = latest_sys.get("cpu_percent", "?")
                mem = latest_sys.get("memory_percent", "?")
                db_size = latest_sys.get("db_size_mb", "?")
                cache = latest_sys.get("cache_hit_ratio", "?")

                # Color-code CPU and memory
                cpu_color = "#FF6B6B" if isinstance(cpu, (int, float)) and cpu > 80 else "#64FFDA"
                mem_color = "#FF6B6B" if isinstance(mem, (int, float)) and mem > 80 else "#64FFDA"

                st.markdown(
                    f'CPU: <span style="color:{cpu_color}; font-weight:600;">{cpu}%</span>  \n'
                    f'Memory: <span style="color:{mem_color}; font-weight:600;">{mem}%</span>  \n'
                    f'DB Size: **{db_size} MB**  \n'
                    f'Cache Hit: **{cache}**',
                    unsafe_allow_html=True,
                )

            if latest_conn:
                active = latest_conn.get("active", 0)
                idle = latest_conn.get("idle", 0)
                idle_tx = latest_conn.get("idle_in_tx", 0)
                total = latest_conn.get("total", 0)

                tx_color = "#FF6B6B" if idle_tx > 5 else "#64FFDA"

                st.markdown(
                    f'Connections: **{active}** active, **{idle}** idle  \n'
                    f'Idle in TX: <span style="color:{tx_color}; font-weight:600;">{idle_tx}</span>  \n'
                    f'Total: **{total}**',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No metrics collected yet.")

        st.markdown("---")
        st.markdown(
            '<div style="text-align:center; color:#4A5568; font-size:0.8rem;">'
            '🚢 NAPA Maritime DB Monitor</div>',
            unsafe_allow_html=True,
        )
