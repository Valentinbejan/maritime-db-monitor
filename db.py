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
