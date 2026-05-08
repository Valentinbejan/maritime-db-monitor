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

# ── Maritime Schema Context (used in AI prompts) ─────────
SCHEMA_CONTEXT = """
Maritime Database Schema (NAPA Context):

TABLE vessels:
  id SERIAL PK, imo_number VARCHAR(10) UNIQUE, vessel_name VARCHAR(100),
  vessel_type VARCHAR(50), year_built INT

TABLE compartments:
  id SERIAL PK, vessel_id INT FK→vessels, compartment_name VARCHAR(100),
  fluid_type VARCHAR(50), volume_m3 DECIMAL(10,2), center_of_gravity_z DECIMAL(10,2)

TABLE telemetry_logs:
  id SERIAL PK, vessel_id INT FK→vessels, timestamp TIMESTAMPTZ,
  latitude DECIMAL(9,6), longitude DECIMAL(9,6), speed_knots DECIMAL(5,2),
  fuel_consumption_lph DECIMAL(6,2), wave_height_m DECIMAL(4,2)

Indexes: idx_telemetry_vessel_id, idx_telemetry_timestamp
~50,000 telemetry rows across 5 vessels over 30 days.
""".strip()
