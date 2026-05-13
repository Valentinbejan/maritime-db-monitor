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
import sidebar
import ai_analyzer
import ui_helpers

st.set_page_config(page_title="DBA Chat — NAPA Monitor", page_icon="💬", layout="wide")
sidebar.render_sidebar()

st.markdown("# 💬 DBA Chat")
st.caption("Context-aware database assistant — your schema and live metrics are injected automatically")


# ── Session State Init ───────────────────────────────────

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


# ── Chat-specific sidebar controls ───────────────────────
with st.sidebar:
    st.markdown("---")
    st.caption("💬 Schema & metrics are injected into every message.")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_messages = []
        st.rerun()


# ── API Check ────────────────────────────────────────────

if not config.is_api_ready():
    st.info(
        "🔑 Set `OPENROUTER_API_KEY` in your `.env` file to enable the DBA Chat. "
        "Get a free key at [openrouter.ai](https://openrouter.ai)."
    )
    st.stop()


# ── Render Chat History ──────────────────────────────────

for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            if msg.get("reasoning"):
                ui_helpers.render_reasoning_dropdown(msg["reasoning"])
            st.markdown(msg["content"])
            ui_helpers.render_token_usage(msg.get("usage"))
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
    system_prompt = ai_analyzer.build_system_prompt(include_metrics=True)

    # Build the full messages list for the API (only role + content for the API)
    api_messages = [{"role": "system", "content": system_prompt}]
    for m in st.session_state.chat_messages:
        api_messages.append({"role": m["role"], "content": m["content"]})

    # Send to the LLM and render
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = ai_analyzer.call_llm(messages=api_messages)

        if result.get("error"):
            assistant_content = f"❌ {result['error']}"
            reasoning = None
            usage = {}
            st.error(assistant_content)
        else:
            assistant_content = result.get("content", "")
            reasoning = result.get("reasoning")
            usage = result.get("usage", {})
            if reasoning:
                ui_helpers.render_reasoning_dropdown(reasoning)
            st.markdown(assistant_content)
            ui_helpers.render_token_usage(usage)

    # Save assistant message with reasoning and usage to history
    st.session_state.chat_messages.append({
        "role": "assistant",
        "content": assistant_content,
        "reasoning": reasoning,
        "usage": usage,
    })
