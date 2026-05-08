"""
collector.py — Standalone metric collection script.

Run in a separate terminal:  python collector.py

Periodically collects database and system metrics, writing them
to JSONL files under data/metrics/. This script must NEVER be
imported or started as a thread inside the Streamlit app.
"""

import sys
import time
import logging
from datetime import datetime, timezone
from decimal import Decimal

import psutil

import config
import db
import storage

# ── Logging Setup ────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [COLLECTOR]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _serialize(obj):
    """Convert Decimal and other non-JSON types to JSON-safe values."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (int, float, bool, type(None))):
        return obj
    return str(obj)


def _to_plain_dict(row: dict) -> dict:
    """Convert a RealDictRow to a plain dict with JSON-safe values."""
    return {k: _serialize(v) for k, v in row.items()}


# ── Collection Functions ─────────────────────────────────

def collect_system_metrics():
    """Collect host CPU/memory + database-level stats."""
    try:
        db_stats = db.fetch_database_stats()
        bloat = db.fetch_table_bloat()

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "memory_used_mb": round(psutil.virtual_memory().used / (1024 * 1024), 1),
            "db_size_bytes": int(db_stats["db_size_bytes"]),
            "db_size_mb": round(int(db_stats["db_size_bytes"]) / (1024 * 1024), 1),
            "cache_hit_ratio": float(db_stats["cache_hit_ratio"]),
            "tx_commit": int(db_stats["tx_commit"]),
            "tx_rollback": int(db_stats["tx_rollback"]),
            "table_bloat": [_to_plain_dict(b) for b in bloat],
        }

        storage.append_metric(config.SYSTEM_METRICS_FILE, record)
        storage.rotate_if_needed(config.SYSTEM_METRICS_FILE)
        log.info(
            "System: CPU=%.1f%% | MEM=%.1f%% | DB=%.1fMB | Cache=%.4f",
            record["cpu_percent"],
            record["memory_percent"],
            record["db_size_mb"],
            record["cache_hit_ratio"],
        )
    except Exception as e:
        log.error("Failed to collect system metrics: %s", e)


def collect_connection_metrics():
    """Collect active/idle/idle-in-tx connection counts."""
    try:
        conns = db.fetch_active_connections()
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active": int(conns["active"]),
            "idle": int(conns["idle"]),
            "idle_in_tx": int(conns["idle_in_tx"]),
            "total": int(conns["total"]),
        }

        storage.append_metric(config.CONNECTION_METRICS_FILE, record)
        storage.rotate_if_needed(config.CONNECTION_METRICS_FILE)
        log.info(
            "Connections: active=%d | idle=%d | idle_in_tx=%d | total=%d",
            record["active"],
            record["idle"],
            record["idle_in_tx"],
            record["total"],
        )
    except Exception as e:
        log.error("Failed to collect connection metrics: %s", e)


def collect_slow_queries():
    """Collect top slow queries from pg_stat_statements."""
    try:
        queries = db.fetch_slow_queries(limit=20)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "queries": [_to_plain_dict(q) for q in queries],
        }

        storage.append_metric(config.SLOW_QUERIES_FILE, record)
        storage.rotate_if_needed(config.SLOW_QUERIES_FILE)
        log.info("Slow queries: captured %d entries", len(queries))
    except Exception as e:
        log.error("Failed to collect slow queries: %s", e)


# ── Main Loop ────────────────────────────────────────────

def main():
    """Run the collection loop until interrupted."""
    interval = config.COLLECTION_INTERVAL
    log.info("=" * 50)
    log.info("NAPA Maritime DB Collector starting")
    log.info("Interval: %ds | DB: %s:%d/%s", interval, config.DB_HOST, config.DB_PORT, config.DB_NAME)
    log.info("Saving to: %s", config.DATA_DIR)
    log.info("=" * 50)
    log.info("Press Ctrl+C to stop.\n")

    try:
        while True:
            log.info("── Collecting metrics ──")
            collect_system_metrics()
            collect_connection_metrics()
            collect_slow_queries()
            log.info("── Done. Sleeping %ds ──\n", interval)
            time.sleep(interval)
    except KeyboardInterrupt:
        log.info("\nShutting down gracefully...")
    finally:
        db.close_pool()
        log.info("Connection pool closed. Goodbye!")


if __name__ == "__main__":
    main()
