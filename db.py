"""
db.py — PostgreSQL connection pool and query helpers.
Uses psycopg2 SimpleConnectionPool with a context-manager
for safe connection checkout / return.
"""

import contextlib
import psycopg2
from psycopg2 import pool, extras
import config


# ── Connection Pool ──────────────────────────────────────
_pool = None


def get_pool():
    """Lazy-initialize and return the connection pool."""
    global _pool
    if _pool is None or _pool.closed:
        _pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            host=config.DB_HOST,
            port=config.DB_PORT,
            dbname=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD,
        )
    return _pool


@contextlib.contextmanager
def get_connection():
    """Context manager that checks out a connection and returns it on exit."""
    p = get_pool()
    conn = p.getconn()
    try:
        yield conn
    finally:
        p.putconn(conn)


def close_pool():
    """Close all connections in the pool. Call on shutdown."""
    global _pool
    if _pool is not None and not _pool.closed:
        _pool.closeall()
        _pool = None


# ── Query Helpers ────────────────────────────────────────

def fetch_active_connections():
    """Return connection counts grouped by state."""
    query = """
        SELECT
            count(*) FILTER (WHERE state = 'active')             AS active,
            count(*) FILTER (WHERE state = 'idle')               AS idle,
            count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_tx,
            count(*)                                              AS total
        FROM pg_stat_activity
        WHERE datname = current_database();
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(query)
            return cur.fetchone()


def fetch_database_stats():
    """Return database-level statistics: size, cache hit ratio, transactions."""
    query = """
        SELECT
            pg_database_size(current_database())           AS db_size_bytes,
            xact_commit                                     AS tx_commit,
            xact_rollback                                   AS tx_rollback,
            blks_hit,
            blks_read,
            CASE WHEN (blks_hit + blks_read) > 0
                 THEN round(blks_hit::numeric / (blks_hit + blks_read), 4)
                 ELSE 1
            END                                             AS cache_hit_ratio
        FROM pg_stat_database
        WHERE datname = current_database();
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(query)
            return cur.fetchone()


def fetch_slow_queries(limit=20):
    """Return top slow queries from pg_stat_statements."""
    query = """
        SELECT
            query,
            calls,
            round(total_exec_time::numeric, 2)  AS total_exec_time_ms,
            round(mean_exec_time::numeric, 2)   AS mean_exec_time_ms,
            rows
        FROM pg_stat_statements
        WHERE query NOT LIKE '%%pg_stat_statements%%'
          AND query NOT LIKE '%%pg_stat_activity%%'
        ORDER BY mean_exec_time DESC
        LIMIT %s;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(query, (limit,))
            return cur.fetchall()


def fetch_table_bloat():
    """Return dead-tuple counts per table (top 10)."""
    query = """
        SELECT relname, n_live_tup, n_dead_tup,
               CASE WHEN n_live_tup > 0
                    THEN round(n_dead_tup::numeric / n_live_tup, 4)
                    ELSE 0
               END AS dead_ratio
        FROM pg_stat_user_tables
        ORDER BY n_dead_tup DESC
        LIMIT 10;
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            cur.execute(query)
            return cur.fetchall()


def fetch_schema_context() -> str:
    """
    Dynamically introspect the database schema and return a human-readable
    description for use in AI prompts. Queries information_schema and
    pg_catalog so the app never needs hardcoded table definitions.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=extras.RealDictCursor) as cur:

            # 1. Get all user tables with row counts
            cur.execute("""
                SELECT
                    t.table_name,
                    s.n_live_tup AS approx_rows
                FROM information_schema.tables t
                LEFT JOIN pg_stat_user_tables s
                    ON s.relname = t.table_name
                WHERE t.table_schema = 'public'
                  AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name;
            """)
            tables = cur.fetchall()

            # 2. Get all columns
            cur.execute("""
                SELECT
                    table_name,
                    column_name,
                    data_type,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                ORDER BY table_name, ordinal_position;
            """)
            columns = cur.fetchall()

            # 3. Get primary keys
            cur.execute("""
                SELECT
                    tc.table_name,
                    kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public';
            """)
            pk_rows = cur.fetchall()
            pks = {}
            for row in pk_rows:
                pks.setdefault(row["table_name"], []).append(row["column_name"])

            # 4. Get foreign keys
            cur.execute("""
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name  AS referenced_table,
                    ccu.column_name AS referenced_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                    ON tc.constraint_name = ccu.constraint_name
                    AND tc.table_schema = ccu.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public';
            """)
            fk_rows = cur.fetchall()
            fks = {}
            for row in fk_rows:
                fks.setdefault(row["table_name"], {})[row["column_name"]] = (
                    f"{row['referenced_table']}({row['referenced_column']})"
                )

            # 5. Get indexes
            cur.execute("""
                SELECT
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY tablename, indexname;
            """)
            idx_rows = cur.fetchall()
            indexes = {}
            for row in idx_rows:
                indexes.setdefault(row["tablename"], []).append(row["indexname"])

    # ── Build the schema description string ──────────────
    cols_by_table = {}
    for col in columns:
        cols_by_table.setdefault(col["table_name"], []).append(col)

    lines = ["Database Schema (dynamically introspected):", ""]

    for table in tables:
        tname = table["table_name"]
        rows = table.get("approx_rows", "?")
        lines.append(f"TABLE {tname}  (~{rows} rows)")

        table_pks = set(pks.get(tname, []))
        table_fks = fks.get(tname, {})

        for col in cols_by_table.get(tname, []):
            cname = col["column_name"]
            dtype = col["data_type"]

            # Enrich type with length/precision
            if col["character_maximum_length"]:
                dtype += f"({col['character_maximum_length']})"
            elif col["numeric_precision"] and col["numeric_scale"]:
                dtype += f"({col['numeric_precision']},{col['numeric_scale']})"

            flags = []
            if cname in table_pks:
                flags.append("PK")
            if cname in table_fks:
                flags.append(f"FK→{table_fks[cname]}")
            if col["is_nullable"] == "NO" and cname not in table_pks:
                flags.append("NOT NULL")

            flag_str = f"  [{', '.join(flags)}]" if flags else ""
            lines.append(f"  {cname} {dtype}{flag_str}")

        # Indexes for this table
        table_idxs = indexes.get(tname, [])
        if table_idxs:
            lines.append(f"  Indexes: {', '.join(table_idxs)}")

        lines.append("")

    return "\n".join(lines).strip()

