"""
config.py — Centralized configuration loader.
Reads from .env file and exposes typed settings with safe defaults.
All other modules should import settings from here.
"""

import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

# ── Database ─────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5433"))
DB_NAME = os.getenv("DB_NAME", "napa_maritime")
DB_USER = os.getenv("DB_USER", "napa_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "napa_secret")

# ── Collector ────────────────────────────────────────────
COLLECTION_INTERVAL = int(os.getenv("COLLECTION_INTERVAL", "30"))  # seconds

# ── OpenRouter AI ────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")

# ── Paths ────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "metrics")
SYSTEM_METRICS_FILE = os.path.join(DATA_DIR, "system_metrics.jsonl")
CONNECTION_METRICS_FILE = os.path.join(DATA_DIR, "connection_metrics.jsonl")
SLOW_QUERIES_FILE = os.path.join(DATA_DIR, "slow_queries.jsonl")
INDEX_HEALTH_FILE = os.path.join(DATA_DIR, "index_health.jsonl")

# NOTE: Schema context is no longer hardcoded here.
# It is dynamically introspected from PostgreSQL via db.fetch_schema_context().


def is_api_ready() -> bool:
    """Return True if the OpenRouter API key is configured and not a placeholder."""
    return bool(OPENROUTER_API_KEY) and OPENROUTER_API_KEY != "your_openrouter_api_key_here"
