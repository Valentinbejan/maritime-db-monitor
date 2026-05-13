"""
sidebar.py — Shared sidebar rendered on every page.

Call render_sidebar() from any page to get the consistent
NAPA Monitor sidebar with collector status, DB info, live
metrics snapshot, and connection breakdown.

Section collapse/expand state is stored in st.session_state
so it persists across page navigation.
"""

import streamlit as st
from datetime import datetime, timezone

import config
import storage


def _toggle(key: str):
    """Callback to flip a boolean session_state key."""
    st.session_state[key] = not st.session_state[key]


def render_sidebar():
    """Render the shared sidebar. Call this from every page."""

    # ── Initialize collapse state (survives page switches) ──
    if "sb_show_db_info" not in st.session_state:
        st.session_state.sb_show_db_info = True
    if "sb_show_metrics" not in st.session_state:
        st.session_state.sb_show_metrics = True
    if "sb_show_admin" not in st.session_state:
        st.session_state.sb_show_admin = False

    # CSS: Keep page nav always expanded, hide the collapse arrow
    st.markdown("""
    <style>
        /* Hide the collapse toggle arrow on sidebar navigation */
        [data-testid="stSidebarNav"] summary {
            display: none !important;
        }
        /* Ensure the page list is always visible and not clipped */
        [data-testid="stSidebarNav"] ul {
            display: block !important;
            max-height: none !important;
            overflow: visible !important;
        }
        [data-testid="stSidebarNav"] details {
            overflow: visible !important;
        }
        [data-testid="stSidebarNav"] details[open] > ul {
            max-height: none !important;
        }
        /* Sidebar section toggle buttons */
        .sb-toggle {
            background: none;
            border: none;
            color: #CCD6F6;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            padding: 0;
            width: 100%;
            text-align: left;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 🚢 NAPA Monitor")
        st.markdown("---")

        # ── Collector Status (always visible) ────────────
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

        # ── Database Info (collapsible) ──────────────────
        arrow_db = "▾" if st.session_state.sb_show_db_info else "▸"
        st.button(
            f"{arrow_db} Database Info",
            key="_toggle_db_info",
            on_click=_toggle,
            args=("sb_show_db_info",),
            use_container_width=True,
        )

        if st.session_state.sb_show_db_info:
            st.markdown(
                f"**Host:** `{config.DB_HOST}:{config.DB_PORT}`  \n"
                f"**Database:** `{config.DB_NAME}`  \n"
                f"**Interval:** `{config.COLLECTION_INTERVAL}s`  \n"
                f"**AI Model:** `{config.LLM_MODEL}`"
            )

        st.markdown("---")

        # ── Live Metrics (collapsible) ───────────────────
        arrow_m = "▾" if st.session_state.sb_show_metrics else "▸"
        st.button(
            f"{arrow_m} Live Metrics",
            key="_toggle_metrics",
            on_click=_toggle,
            args=("sb_show_metrics",),
            use_container_width=True,
        )

        if st.session_state.sb_show_metrics:
            latest_sys = storage.read_latest(config.SYSTEM_METRICS_FILE)
            latest_conn = storage.read_latest(config.CONNECTION_METRICS_FILE)

            if latest_sys or latest_conn:
                if latest_sys:
                    cpu = latest_sys.get("cpu_percent", "?")
                    mem = latest_sys.get("memory_percent", "?")
                    db_size = latest_sys.get("db_size_mb", "?")
                    cache = latest_sys.get("cache_hit_ratio", "?")

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

        # ── Admin (collapsible) ───────────────────────────
        arrow_admin = "▾" if st.session_state.sb_show_admin else "▸"
        st.button(
            f"{arrow_admin} ⚙️ Admin",
            key="_toggle_admin",
            on_click=_toggle,
            args=("sb_show_admin",),
            use_container_width=True,
        )

        if "wipe_confirm" not in st.session_state:
            st.session_state.wipe_confirm = False

        if st.session_state.sb_show_admin:
            if st.button("🗑️ Wipe All Metrics Data", use_container_width=True):
                st.session_state.wipe_confirm = True

            if st.session_state.wipe_confirm:
                confirm = st.text_input(
                    "Type **DELETE** to confirm:", key="wipe_input",
                    placeholder="DELETE",
                )
                if confirm == "DELETE":
                    import glob, os
                    pattern = os.path.join(config.DATA_DIR, "*.jsonl")
                    deleted = 0
                    for f in glob.glob(pattern):
                        os.remove(f)
                        deleted += 1
                    st.session_state.wipe_confirm = False
                    st.success(f"✅ Deleted {deleted} data file(s). Dashboard reset!")
                    st.rerun()
                elif confirm:
                    st.error("❌ Type exactly `DELETE` to confirm.")

        st.markdown("---")
        st.markdown(
            '<div style="text-align:center; color:#4A5568; font-size:0.8rem;">'
            '🚢 NAPA Maritime DB Monitor</div>',
            unsafe_allow_html=True,
        )
