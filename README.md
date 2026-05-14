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
- **Execution Plan Analysis** — For slow queries, the app safely executes `EXPLAIN (ANALYZE, FORMAT JSON)` on the database and feeds the exact execution plan to the AI for a node-by-node bottleneck breakdown.

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
- An OpenRouter API key (free tier is fine — get one at [openrouter.ai](https://openrouter.ai))

### 1. Clone the Repository

```bash
git clone https://github.com/Valentinbejan/maritime-db-monitor.git
cd maritime-db-monitor
```

### 2. Environment Setup

Copy the example environment file and add your AI API key:

```bash
cp .env.example .env
```

Open `.env` in a text editor and replace `your_openrouter_api_key_here` with your actual key.

> **Note:** The app will still function without this key, but AI features will be disabled.

### 3. Install Python Dependencies

It is highly recommended to use a virtual environment:

```bash
python -m venv venv
source venv/bin/activate      # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Running the Application

Because of the decoupled architecture, you need to run three separate processes. Open three terminal windows:

### Terminal 1 — Start the Database

```bash
docker compose up -d
```

This starts Postgres, enables `pg_stat_statements`, and generates 50k rows of dummy data.

### Terminal 2 — Start the Data Collector

```bash
source venv/bin/activate      # On Windows: venv\Scripts\activate
python collector.py
```

Leave this running. It will print logs to the console every 30 seconds as it gathers data.

### Terminal 3 — Start the Dashboard

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

### Trigger Missing Index Warning

```bash
python tests/scenarios/05_seq_scan_pressure.py
```

Check the dashboard: navigate to **Index Health** to see the AI suggest a new index.

> Run `python tests/scenarios/cleanup_all.py` at any time to remove the test tables/indexes.
