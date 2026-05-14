# NAPA Maritime DB Monitor

**An AI-Powered PostgreSQL Health & Performance Dashboard**

This application was built as an assignment to monitor the health and performance of a PostgreSQL database, tailored around a simulated maritime fleet management workload (vessels, compartments, telemetry logs).

It features a decoupled background metric collector, a rich Streamlit frontend for data visualization, and deep integration with Large Language Models (LLMs) acting as an automated Database Administrator (DBA).

---

## Assignment Fulfillment Checklist

- **Connect to PostgreSQL** — Connects to a local Dockerized Postgres 16 instance.
- **Periodically collect metrics** — A standalone `collector.py` daemon fetches CPU, memory, active connections, and slow queries.
- **Store collected data locally** — Metrics are stored in append-only JSON Lines (`.jsonl`) files.
- **Inspect current/historical trends** — Streamlit UI provides live metric cards and Plotly time-series charts.
- **AI Usage** — Context-aware AI integration via OpenRouter API.
- **Bonus features** — Interactive charts, threshold-based monitoring alerts, configurable polling intervals, `EXPLAIN ANALYZE` integration, Index Health tracking, Autovacuum monitoring, and load-testing scripts.

---

## Architecture Overview

The application is split into decoupled components to ensure the UI remains fast and data collection is never blocked:

- **The Database** (`docker-compose.yml`) — A PostgreSQL 16 container pre-configured with the `pg_stat_statements` extension. On startup, `init.sql` automatically seeds the schema and generates 50,000 rows of dummy fleet telemetry data.
- **The Collector** (`collector.py`) — A lightweight background Python daemon. Every 30 seconds (configurable), it polls OS stats (via `psutil`) and DB stats (via `psycopg2`), appending the results to flat `.jsonl` files.
- **Storage** (`data/metrics/*.jsonl`) — Acts as a local time-series database. JSONL is used because it is append-only, human-readable, and requires no external database dependencies.
- **The Dashboard** (`app.py`) — A Streamlit web application that reads the `.jsonl` files, visualizes the data, and interfaces with the OpenRouter AI API.

---

## Explanation of AI Usage

The AI in this application does not just generate generic advice; it acts as a **Context-Aware Database Administrator**.

- **Dynamic Schema Introspection** — Before making an API call, the app queries the PostgreSQL catalog to dynamically build a text representation of the schema (tables, columns, data types, primary/foreign keys, indexes) and injects it into the AI's system prompt.
- **Live Metrics Injection** — The AI is fed the latest CPU, memory, cache, and connection data.
- **Execution Plan Analysis** — For slow queries, the app safely executes `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` on the database and feeds the exact execution plan — including shared/local buffer hit/read ratios — to the AI for a node-by-node bottleneck breakdown.

### AI Features Implemented

- **Comprehensive Health Reports** — Generates full-system markdown reports based on collected metrics.
- **Per-Query Optimization** — Suggests specific `CREATE INDEX` statements or SQL rewrites for slow queries.
- **DBA ChatOps** — An interactive chat where you can ask things like _"Why are inserts into `telemetry_logs` slow?"_ and the AI will answer based on your actual live schema and metrics.
- **Index & Vacuum Tuning** — Analyzes PostgreSQL table bloat and suggests `ALTER SYSTEM` commands for autovacuum tuning.

---

## Setup Instructions

### Prerequisites

- Docker & Docker Compose (for the database)
- Python 3.10+
- *(Optional)* An OpenRouter API key to enable AI features — get one at [openrouter.ai](https://openrouter.ai). The default model is `google/gemma-4-31b-it:free`, which is what I used during development and is recommended for this project. You can also use OpenRouter's **BYOK (Bring Your Own Key)** integration to plug in a Google AI Studio key and route requests to Google's models through OpenRouter without OpenRouter credits.

### 1. Clone the Repository

```bash
git clone https://github.com/Valentinbejan/maritime-db-monitor.git
cd maritime-db-monitor
```

### 2. Environment Setup

Creating a `.env` file is **required** — the app will refuse to start without `DB_PASSWORD` set. Copy the example file and edit it:

```bash
cp .env.example .env
```

Open `.env` and fill in:

- `DB_PASSWORD` — **required**. Any value works for local use (default `napa_secret` is fine).
- `OPENROUTER_API_KEY` — optional. Replace `your_openrouter_api_key_here` with a real key to enable AI features. Without it, the dashboard runs but the AI Insights / DBA Chat / Index Health AI sections will be disabled.
- `LLM_MODEL` — defaults to `google/gemma-4-31b-it:free` (recommended — this is what I used during development). If you prefer a Google model, you can configure **BYOK** in OpenRouter with a Google AI Studio key and switch `LLM_MODEL` to a `google/...` variant; requests will be routed through OpenRouter using your Google quota.

> **Port note:** The compose file maps Postgres to host port `5433` (not the default `5432`) so it doesn't collide with any local Postgres install. If you change `DB_PORT` in `.env`, the collector and the container will both pick it up.

### 3. Install Python Dependencies

It is highly recommended to use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Running the Application

The architecture has three processes, but Docker runs detached — so you only need **two persistent terminal windows** for the Python processes.

### Step 1 — Start the Database (any terminal)

```bash
docker compose up -d
```

This starts Postgres in the background, enables `pg_stat_statements`, and generates 50k rows of dummy data. The terminal is free to use afterwards.

### Terminal A — Start the Data Collector

```bash
source venv/bin/activate      # On Windows: venv\Scripts\activate
python collector.py
```

Leave this running. It will print logs to the console every 30 seconds as it gathers data.

### Terminal B — Start the Dashboard

```bash
source venv/bin/activate      # On Windows: venv\Scripts\activate
streamlit run app.py
```

This will automatically open the dashboard in your web browser at [http://localhost:8501](http://localhost:8501).

---

## Testing & Scenarios (Load Simulation)

To demonstrate the monitoring capabilities, the repository includes a suite of scenario scripts that simulate real-world database issues.

While the collector and dashboard are running, open a new terminal and run any of these scripts:

### Generate Slow Queries

```bash
python tests/scenarios/01_slow_query.py
```

Check the dashboard: navigate to **Slow Queries** in ~30s.

### Trigger Table Bloat (Dead Tuples)

```bash
python tests/scenarios/02_bloat.py
```

Check the dashboard: navigate to **Overview → Table Bloat** or **Autovacuum**.

### Simulate a Connection Leak (Idle in Transaction)

```bash
python tests/scenarios/03_idle_in_transaction.py
```

Check the dashboard: look at the Connection Breakdown pie chart on the **Overview** page.

### Trigger a Connection Storm

```bash
python tests/scenarios/04_connection_storm.py            # default: 30 conns × 30s
python tests/scenarios/04_connection_storm.py 50 20      # custom: N conns × duration
```

Opens many parallel connections and holds them open. Check the dashboard: **Overview → Connection Breakdown** and the **AI Insights** "High connection count" alert.

### Trigger Missing Index Warning

```bash
python tests/scenarios/05_seq_scan_pressure.py
```

Check the dashboard: navigate to **Index Health** to see the AI suggest a new index.

### Create an Unused Index

```bash
python tests/scenarios/06_unused_index.py
python tests/scenarios/06_unused_index.py --cleanup
```

Creates an index that no normal query uses, demonstrating wasted disk + slower writes. Check the dashboard: **Index Health → Unused Indexes**.

### Stress Autovacuum

```bash
python tests/scenarios/07_autovacuum_stress.py
python tests/scenarios/07_autovacuum_stress.py --cleanup
```

Rapidly churns rows in a small table to trigger an autovacuum cycle within the next naptime window. Check the dashboard: **Autovacuum → Active Workers** and the table's `vacuum_count`.

> Run `python tests/scenarios/cleanup_all.py` at any time to remove the test tables/indexes.
