"""
ui_helpers.py — Shared Streamlit UI components.

DRY module: reasoning dropdowns, token usage captions, AI result rendering,
data guards, threshold-based color helpers, and the "AI action button +
API-key warning" composite are used across all dashboard pages.
"""

import streamlit as st
import re

import config


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
        f'<span class="material-symbols-outlined" style="font-size:1rem;vertical-align:middle;">psychology</span> Show AI Reasoning (Internal Thought Process)</summary>'
        f'<div style="margin-top:0.8rem; color:#8892B0; font-size:0.9rem;">'
        f'{reasoning_html}</div></details>',
        unsafe_allow_html=True,
    )


def no_data_guard(latest, source_label: str = "metrics") -> None:
    """Show a 'no data yet' warning and stop the page if `latest` is falsy."""
    if not latest:
        st.warning(
            f":material/hourglass_top: No {source_label} data yet. Make sure `python collector.py` is running."
        )
        st.stop()


def api_key_warning() -> None:
    """Show the 'set OPENROUTER_API_KEY' info block when the key is missing."""
    if not config.is_api_ready():
        st.info(
            ":material/key: Set `OPENROUTER_API_KEY` in your `.env` file to enable AI analysis. "
            "Get a free key at [openrouter.ai](https://openrouter.ai)."
        )


def ai_action_button(button_label: str, button_key: str) -> bool:
    """
    Render an AI-action button next to a model caption, plus the API-key warning
    if no key is configured. Returns True iff the button was clicked.
    """
    api_ready = config.is_api_ready()
    btn_col, model_col = st.columns([1, 2])
    with btn_col:
        clicked = st.button(
            button_label,
            disabled=not api_ready,
            type="primary",
            width="stretch",
            key=button_key,
        )
    with model_col:
        st.caption(f"Model: `{config.LLM_MODEL}`")
    api_key_warning()
    return clicked


def render_ai_result(
    result: dict,
    *,
    toggle_label: str,
    toggle_key: str,
    usage_layout: str = "inline",
) -> None:
    """
    Render an AI response dict (from ai_analyzer.call_llm) uniformly:
    error → reasoning dropdown → toggleable content → token usage footer.
    """
    if not result:
        return
    if result.get("error"):
        st.error(result["error"])
        return
    if result.get("reasoning"):
        render_reasoning_dropdown(result["reasoning"])
    if st.toggle(toggle_label, value=True, key=toggle_key):
        st.markdown(result.get("content", "No response generated."))
    render_token_usage(result.get("usage", {}), layout=usage_layout)


def threshold_color(val, *, warn: float, crit: float, ascending: bool = True) -> str:
    """
    Return a CSS style string colored by threshold.

    ascending=True  → larger is worse: val > crit red, val > warn yellow, else green.
    ascending=False → smaller is worse: val < crit red, val < warn yellow, else green.
    """
    if not isinstance(val, (int, float)):
        return ""
    if ascending:
        if val > crit:
            return "color: #FF6B6B; font-weight: 600"
        if val > warn:
            return "color: #FFD93D; font-weight: 600"
        return "color: #64FFDA"
    else:
        if val < crit:
            return "color: #FF6B6B; font-weight: 600"
        if val < warn:
            return "color: #FFD93D; font-weight: 600"
        return "color: #64FFDA"


def format_bytes(n) -> str:
    """Human-readable bytes (B / KB / MB)."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "—"
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n} B"


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
