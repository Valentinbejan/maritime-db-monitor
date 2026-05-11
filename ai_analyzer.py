"""
ai_analyzer.py — OpenRouter AI integration for database health analysis.

Provides:
  1. get_client()              — Shared OpenRouter client factory.
  2. build_system_prompt()     — Context-aware DBA system prompt (schema + optional metrics).
  3. generate_health_report()  — Full health assessment from all metrics.
  4. analyze_slow_query()      — Per-query optimization suggestions.
  5. check_alerts()            — Local threshold-based alerting (no AI call).
"""

import config
import storage
from openai import OpenAI


# ── Shared Client Factory ────────────────────────────────

def get_client() -> OpenAI | None:
    """Return an OpenRouter client, or None if no API key is set."""
    if not config.is_api_ready():
        return None
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=config.OPENROUTER_API_KEY,
    )


# ── LLM Call Helper ──────────────────────────────────────

def _call_llm(system_prompt: str, user_prompt: str) -> dict:
    """
    Send a chat completion request to OpenRouter.
    Returns a dict with keys: 'content', 'reasoning', 'usage', 'error'.
    """
    client = get_client()
    if client is None:
        return {
            "content": None,
            "reasoning": None,
            "usage": {},
            "error": "No OpenRouter API key configured. Set OPENROUTER_API_KEY in your .env file.",
        }

    try:
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            extra_body={
                "reasoning": {
                    "effort": "high"
                }
            },
        )

        # Convert to raw dict to access OpenRouter-specific fields
        raw = response.model_dump()
        message_data = raw["choices"][0]["message"]

        return {
            "content": (message_data.get("content") or "").strip(),
            "reasoning": message_data.get("reasoning"),
            "usage": raw.get("usage", {}),
            "error": None,
        }

    except Exception as e:
        return {
            "content": None,
            "reasoning": None,
            "usage": {},
            "error": f"OpenRouter API error: {e}",
        }


# ── System Prompt ────────────────────────────────────────

def build_system_prompt(include_metrics: bool = False) -> str:
    """
    Build the system prompt dynamically by introspecting the live database
    schema. Optionally includes the latest performance metrics snapshot.

    Args:
        include_metrics: If True, append live CPU/memory/connection/slow query
                         metrics to the prompt. Used by DBA Chat for full
                         situational awareness.
    """
    try:
        import db
        schema = db.fetch_schema_context()
    except Exception:
        schema = "(Schema introspection unavailable — database may be offline)"

    # Base DBA persona
    prompt = f"""You are a senior PostgreSQL Database Administrator (DBA) \
specializing in maritime fleet management databases for NAPA (Naval Architecture).

You have deep expertise in:
- PostgreSQL performance tuning, indexing, and query optimization
- Maritime data patterns (vessel telemetry, compartment geometry, voyage tracking)
- High-volume time-series data from fleet telematics systems

=== LIVE DATABASE SCHEMA ===
{schema}

When analyzing database health or queries, always:
1. Provide a clear overall assessment (Healthy / Warning / Critical)
2. Explain findings in the context of maritime operations
3. Give actionable, specific recommendations
4. Use markdown formatting with headers, bullet points, and code blocks for SQL

Keep your language professional but accessible to a developer audience."""

    # Optionally inject live metrics for chat context
    if include_metrics:
        metrics_lines = []

        latest_sys = storage.read_latest(config.SYSTEM_METRICS_FILE)
        latest_conn = storage.read_latest(config.CONNECTION_METRICS_FILE)
        latest_slow = storage.read_latest(config.SLOW_QUERIES_FILE)

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
        prompt += f"""

=== LATEST PERFORMANCE METRICS ===
{metrics_block}

RULES:
- You are context-aware. Use the schema and metrics above to give specific, grounded answers.
- When the user asks about tables, columns, or queries, reference the ACTUAL schema above.
- When asked about performance, reference the ACTUAL metrics above.
- Write SQL that matches the real schema — do not invent tables or columns.
- Be concise but thorough. Prioritize actionable advice.
- If asked to explain a slow query, consider the table sizes shown in the schema.
- You can suggest new indexes, query rewrites, partitioning strategies, or config tuning."""

    return prompt


# ── Public API ───────────────────────────────────────────

def generate_health_report(metrics: dict) -> dict:
    """
    Generate a comprehensive AI health report from collected metrics.

    Args:
        metrics: dict with keys 'system', 'connections', 'slow_queries'
                 each containing the latest metric snapshot.

    Returns:
        dict with 'content', 'reasoning', 'usage', 'error'.
    """
    user_prompt = f"""Analyze the following PostgreSQL database health metrics and provide a comprehensive report.

## System Metrics
- CPU Usage: {metrics.get('cpu_percent', 'N/A')}%
- Memory Usage: {metrics.get('memory_percent', 'N/A')}%
- Database Size: {metrics.get('db_size_mb', 'N/A')} MB
- Cache Hit Ratio: {metrics.get('cache_hit_ratio', 'N/A')}
- Transactions Committed: {metrics.get('tx_commit', 'N/A')}
- Transactions Rolled Back: {metrics.get('tx_rollback', 'N/A')}

## Connection Metrics
- Active Connections: {metrics.get('active', 'N/A')}
- Idle Connections: {metrics.get('idle', 'N/A')}
- Idle in Transaction: {metrics.get('idle_in_tx', 'N/A')}
- Total Connections: {metrics.get('total', 'N/A')}

## Top Slow Queries
{_format_slow_queries(metrics.get('slow_queries', []))}

## Table Bloat (Dead Tuples)
{_format_table_bloat(metrics.get('table_bloat', []))}

Please provide:
1. **Overall Health Assessment** (Healthy / Warning / Critical)
2. **Key Findings** — what stands out, especially in the context of maritime telemetry workloads
3. **Detected Anomalies** — anything unusual or concerning
4. **Slow Query Analysis** — explain why the slowest queries may be slow given the maritime schema
5. **Recommendations** — specific, actionable optimization steps (SQL, config changes, indexing)
"""
    return _call_llm(build_system_prompt(), user_prompt)


def analyze_slow_query(query_text: str, stats: dict) -> dict:
    """
    Analyze a single slow query and suggest optimizations.

    Args:
        query_text: The SQL query text.
        stats: dict with 'calls', 'mean_exec_time_ms', 'total_exec_time_ms', 'rows'.

    Returns:
        dict with 'content', 'reasoning', 'usage', 'error'.
    """
    user_prompt = f"""Analyze this slow PostgreSQL query from our maritime fleet database and suggest optimizations.

## Query
```sql
{query_text}
```

## Execution Statistics
- Total Calls: {stats.get('calls', 'N/A')}
- Mean Execution Time: {stats.get('mean_exec_time_ms', 'N/A')} ms
- Total Execution Time: {stats.get('total_exec_time_ms', 'N/A')} ms
- Rows Returned: {stats.get('rows', 'N/A')}

Please provide:
1. **Why is this query slow?** — Explain in the context of the maritime schema (large telemetry_logs table, etc.)
2. **Optimization suggestions** — Include specific SQL (indexes, query rewrites, partitioning ideas)
3. **Expected improvement** — Rough estimate of performance gain
"""
    return _call_llm(build_system_prompt(), user_prompt)


def check_alerts(metrics: dict) -> list[dict]:
    """
    Check metrics against configurable thresholds and return alert dicts.
    This is a local check — no AI call needed.

    Returns:
        List of dicts: [{'level': 'warning'|'critical', 'metric': ..., 'message': ...}]
    """
    alerts = []

    # CPU usage
    cpu = metrics.get("cpu_percent")
    if cpu is not None:
        if cpu > 90:
            alerts.append({"level": "critical", "metric": "CPU", "message": f"CPU usage critically high at {cpu}%"})
        elif cpu > 80:
            alerts.append({"level": "warning", "metric": "CPU", "message": f"CPU usage elevated at {cpu}%"})

    # Memory usage
    mem = metrics.get("memory_percent")
    if mem is not None:
        if mem > 90:
            alerts.append({"level": "critical", "metric": "Memory", "message": f"Memory usage critically high at {mem}%"})
        elif mem > 80:
            alerts.append({"level": "warning", "metric": "Memory", "message": f"Memory usage elevated at {mem}%"})

    # Cache hit ratio
    cache = metrics.get("cache_hit_ratio")
    if cache is not None:
        if cache < 0.90:
            alerts.append({"level": "critical", "metric": "Cache", "message": f"Cache hit ratio dangerously low at {cache:.2%}"})
        elif cache < 0.95:
            alerts.append({"level": "warning", "metric": "Cache", "message": f"Cache hit ratio below optimal at {cache:.2%}"})

    # Idle in transaction
    idle_tx = metrics.get("idle_in_tx")
    if idle_tx is not None and idle_tx > 5:
        alerts.append({"level": "warning", "metric": "Connections", "message": f"{idle_tx} connections are idle in transaction — potential lock contention"})

    # Total connections
    total = metrics.get("total")
    if total is not None and total > 80:
        alerts.append({"level": "warning", "metric": "Connections", "message": f"High connection count: {total}"})

    return alerts


# ── Formatting Helpers ───────────────────────────────────

def _format_slow_queries(queries: list) -> str:
    """Format slow queries list for the AI prompt."""
    if not queries:
        return "No slow queries recorded yet."
    lines = []
    for i, q in enumerate(queries[:10], 1):
        lines.append(
            f"{i}. `{q.get('query', '?')[:120]}...`\n"
            f"   Calls: {q.get('calls', '?')} | "
            f"Mean: {q.get('mean_exec_time_ms', '?')}ms | "
            f"Total: {q.get('total_exec_time_ms', '?')}ms | "
            f"Rows: {q.get('rows', '?')}"
        )
    return "\n".join(lines)


def _format_table_bloat(bloat: list) -> str:
    """Format table bloat list for the AI prompt."""
    if not bloat:
        return "No table bloat data available."
    lines = []
    for b in bloat:
        lines.append(
            f"- {b.get('relname', '?')}: "
            f"{b.get('n_dead_tup', 0)} dead / {b.get('n_live_tup', 0)} live "
            f"(ratio: {b.get('dead_ratio', 0)})"
        )
    return "\n".join(lines)
