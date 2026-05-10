"""
Page 5 — 💬 DBA Chat: Context-aware ChatOps assistant.

NOT a generic chatbot. Before every conversation, the system prompt is
silently injected with:
  1. The live PostgreSQL schema (dynamically introspected via db.fetch_schema_context())
  2. The latest CPU, memory, connection, and slow query metrics from the collector

This gives the AI full situational awareness of the database without the
user having to copy-paste anything.
"""

import streamlit as st

import config
import storage
import db
import sidebar
from openai import OpenAI

st.set_page_config(page_title="DBA Chat — NAPA Monitor", page_icon="💬", layout="wide")
sidebar.render_sidebar()

st.markdown("# 💬 DBA Chat")
st.caption("Context-aware database assistant — your schema and live metrics are injected automatically")


# ── Helpers ──────────────────────────────────────────────

def _get_client() -> OpenAI | None:
    """Return OpenRouter client or None."""
    if not config.OPENROUTER_API_KEY or config.OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        return None
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=config.OPENROUTER_API_KEY,
    )


def _build_context_system_prompt() -> str:
    """
    Build a rich system prompt that includes:
      - DBA persona
      - Live database schema
      - Latest collected metrics snapshot
    """
    # 1. Dynamic schema
    try:
        schema = db.fetch_schema_context()
    except Exception:
        schema = "(Schema unavailable — database may be offline)"

    # 2. Latest metrics
    latest_sys = storage.read_latest(config.SYSTEM_METRICS_FILE)
    latest_conn = storage.read_latest(config.CONNECTION_METRICS_FILE)
    latest_slow = storage.read_latest(config.SLOW_QUERIES_FILE)

    metrics_lines = []
    if latest_sys:
        metrics_lines.append(
            f"CPU: {latest_sys.get('cpu_percent', '?')}% | "
            f"Memory: {latest_sys.get('memory_percent', '?')}% | "
            f"DB Size: {latest_sys.get('db_size_mb', '?')} MB | "
            f"Cache Hit Ratio: {latest_sys.get('cache_hit_ratio', '?')} | "
            f"TX Committed: {latest_sys.get('tx_commit', '?')} | "
            f"TX Rolled Back: {latest_sys.get('tx_rollback', '?')}"
        )
    if latest_conn:
        metrics_lines.append(
            f"Connections — Active: {latest_conn.get('active', '?')} | "
            f"Idle: {latest_conn.get('idle', '?')} | "
            f"Idle in TX: {latest_conn.get('idle_in_tx', '?')} | "
            f"Total: {latest_conn.get('total', '?')}"
        )
    if latest_slow and latest_slow.get("queries"):
        top3 = latest_slow["queries"][:3]
        for i, q in enumerate(top3, 1):
            metrics_lines.append(
                f"Slow Query #{i}: mean={q.get('mean_exec_time_ms', '?')}ms | "
                f"calls={q.get('calls', '?')} | "
                f"query={q.get('query', '?')[:120]}"
            )

    metrics_block = "\n".join(metrics_lines) if metrics_lines else "(No metrics collected yet)"

    return f"""You are a senior PostgreSQL DBA specializing in maritime fleet management \
databases for NAPA (Naval Architecture). You are embedded inside a live monitoring dashboard.

You have REAL-TIME access to the following information about the user's database:

=== LIVE DATABASE SCHEMA ===
{schema}

=== LATEST PERFORMANCE METRICS ===
{metrics_block}

RULES:
- You are context-aware. Use the schema and metrics above to give specific, grounded answers.
- When the user asks about tables, columns, or queries, reference the ACTUAL schema above.
- When asked about performance, reference the ACTUAL metrics above.
- Write SQL that matches the real schema — do not invent tables or columns.
- Use markdown formatting with code blocks for SQL.
- Be concise but thorough. Prioritize actionable advice.
- If asked to explain a slow query, consider the table sizes shown in the schema.
- You can suggest new indexes, query rewrites, partitioning strategies, or config tuning."""


# ── Session State Init ───────────────────────────────────

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "chat_context_prompt" not in st.session_state:
    st.session_state.chat_context_prompt = None


# ── Chat-specific sidebar controls ───────────────────────
with st.sidebar:
    st.markdown("---")
    st.caption("💬 Schema & metrics are injected into every message.")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_messages = []
        st.session_state.chat_context_prompt = None
        st.rerun()


# ── API Check ────────────────────────────────────────────

client = _get_client()
if client is None:
    st.info(
        "🔑 Set `OPENROUTER_API_KEY` in your `.env` file to enable the DBA Chat. "
        "Get a free key at [openrouter.ai](https://openrouter.ai)."
    )
    st.stop()


# ── Render Chat History ──────────────────────────────────

def _render_reasoning(reasoning_text):
    """Render the reasoning dropdown HTML."""
    reasoning_html = reasoning_text.replace("\n", "<br>")
    st.markdown(
        f'<details style="margin-bottom:1rem; padding:0.8rem; '
        f'background:rgba(0,229,255,0.05); border-left:3px solid #00E5FF; '
        f'border-radius:0 8px 8px 0;">'
        f'<summary style="cursor:pointer; font-weight:600; color:#00E5FF;">'
        f'🧠 Show AI Reasoning</summary>'
        f'<div style="margin-top:0.8rem; color:#8892B0; font-size:0.9rem;">'
        f'{reasoning_html}</div></details>',
        unsafe_allow_html=True,
    )

def _render_usage(usage):
    """Render token usage caption."""
    if usage:
        st.caption(
            f"Tokens: {usage.get('total_tokens', '?')} total "
            f"({usage.get('prompt_tokens', '?')} prompt + "
            f"{usage.get('completion_tokens', '?')} completion)"
        )

for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            # Render reasoning if saved
            if msg.get("reasoning"):
                _render_reasoning(msg["reasoning"])
            st.markdown(msg["content"])
            _render_usage(msg.get("usage"))
        else:
            st.markdown(msg["content"])


# ── Auto-inject pending query from Slow Queries page ─────

pending = st.session_state.pop("chat_pending_query", None)

# ── Chat Input ───────────────────────────────────────────

prompt = st.chat_input("Ask about your database — schema, performance, queries...")

# Use the pending query if no manual input
if pending and not prompt:
    prompt = pending

if prompt:

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.chat_messages.append({"role": "user", "content": prompt})

    # Build the context-aware system prompt (refreshed each message for live metrics)
    system_prompt = _build_context_system_prompt()

    # Build the full messages list for the API (only role + content for the API)
    api_messages = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.chat_messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    # Stream the response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=api_messages,
                    temperature=0.3,
                    extra_body={
                        "reasoning": {
                            "effort": "high"
                        }
                    },
                )

                raw = response.model_dump()
                message_data = raw["choices"][0]["message"]
                assistant_content = (message_data.get("content") or "").strip()
                reasoning = message_data.get("reasoning")
                usage = raw.get("usage", {})

                # Show reasoning dropdown if present
                if reasoning:
                    _render_reasoning(reasoning)

                st.markdown(assistant_content)
                _render_usage(usage)

            except Exception as e:
                assistant_content = f"❌ Error: {e}"
                reasoning = None
                usage = {}
                st.error(assistant_content)

    # Save assistant message with reasoning and usage to history
    st.session_state.chat_messages.append({
        "role": "assistant",
        "content": assistant_content,
        "reasoning": reasoning,
        "usage": usage,
    })
