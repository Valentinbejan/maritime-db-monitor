"""
ui_helpers.py — Shared Streamlit UI components.

DRY module: reasoning dropdowns and token usage captions are used across
Slow Queries, AI Insights, and DBA Chat pages.
"""

import streamlit as st


def render_reasoning_dropdown(reasoning_text: str) -> None:
    """Render AI reasoning in a collapsible HTML <details> block."""
    reasoning_html = reasoning_text.replace("\n", "<br>")
    st.markdown(
        f'<details style="margin-bottom:1rem; padding:0.8rem; '
        f'background:rgba(0,229,255,0.05); border-left:3px solid #00E5FF; '
        f'border-radius:0 8px 8px 0;">'
        f'<summary style="cursor:pointer; font-weight:600; color:#00E5FF;">'
        f'🧠 Show AI Reasoning (Internal Thought Process)</summary>'
        f'<div style="margin-top:0.8rem; color:#8892B0; font-size:0.9rem;">'
        f'{reasoning_html}</div></details>',
        unsafe_allow_html=True,
    )


def render_token_usage(usage: dict, layout: str = "inline") -> None:
    """
    Render token usage info.

    Args:
        usage: dict with prompt_tokens, completion_tokens, total_tokens.
        layout: 'inline' for a single caption, 'columns' for a 3-column layout.
    """
    if not usage:
        return

    if layout == "columns":
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            st.caption(f"Prompt tokens: {usage.get('prompt_tokens', '?')}")
        with tc2:
            st.caption(f"Completion tokens: {usage.get('completion_tokens', '?')}")
        with tc3:
            st.caption(f"Total tokens: {usage.get('total_tokens', '?')}")
    else:
        st.caption(
            f"Tokens: {usage.get('total_tokens', '?')} total "
            f"({usage.get('prompt_tokens', '?')} prompt + "
            f"{usage.get('completion_tokens', '?')} completion)"
        )
