"""
ui_helpers.py — Shared Streamlit UI components.

DRY module: reasoning dropdowns and token usage captions are used across
Slow Queries, AI Insights, and DBA Chat pages.
"""

import streamlit as st
import re


def _md_to_html(text: str) -> str:
    """
    Lightweight markdown → HTML converter for reasoning text.

    Handles the patterns LLMs typically use in their reasoning:
    code blocks, inline code, bold, italic, headers, and line breaks.
    """
    # Fenced code blocks: ```lang\ncode\n``` → <pre><code>
    text = re.sub(
        r"```(\w*)\n(.*?)```",
        lambda m: f'<pre style="background:#1a1a2e; padding:0.5rem; border-radius:4px; '
                  f'overflow-x:auto; font-size:0.85rem;"><code>{m.group(2).strip()}</code></pre>',
        text,
        flags=re.DOTALL,
    )

    # Inline code: `text` → <code>
    text = re.sub(
        r"`([^`]+)`",
        r'<code style="background:#1a1a2e; padding:0.1rem 0.3rem; border-radius:3px; '
        r'font-size:0.85rem;">\1</code>',
        text,
    )

    # Bullet lists: * item or - item → • item
    text = re.sub(r"^(\s*)[\*\-]\s+(.+)$", r"\1&bull; \2", text, flags=re.MULTILINE)

    # Bold: **text** → <strong>
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

    # Italic: *text* → <em>
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)

    # Headers: ### text → <h4>, ## text → <h3>, # text → <h3>
    text = re.sub(r"^### (.+)$", r'<h4 style="margin:0.5rem 0 0.2rem;">\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r'<h3 style="margin:0.5rem 0 0.2rem;">\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r'<h3 style="margin:0.5rem 0 0.2rem;">\1</h3>', text, flags=re.MULTILINE)

    # Line breaks
    text = text.replace("\n", "<br>")

    return text


def render_reasoning_dropdown(reasoning_text: str) -> None:
    """Render AI reasoning in a collapsible HTML <details> block with proper formatting."""
    reasoning_html = _md_to_html(reasoning_text)
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
