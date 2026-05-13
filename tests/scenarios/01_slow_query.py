# Scenario 01 — Slow queries.
# Runs heavy unindexed queries against telemetry_logs so they show up in
# pg_stat_statements with high mean_exec_time.
# Check the dashboard at: 🐢 Slow Queries  (entries appear within ~30s)
# Run from project root:   python tests/scenarios/01_slow_query.py

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import db


HEAVY_QUERIES = [
    # No index on wave_height_m + sort on another unindexed column
    """
    SELECT vessel_id, AVG(fuel_consumption_lph) AS avg_fuel
    FROM telemetry_logs
    WHERE wave_height_m > 3.0
    GROUP BY vessel_id
    ORDER BY avg_fuel DESC
    """,
    # Self-join across the whole table
    """
    SELECT t1.vessel_id, COUNT(*) AS pair_count
    FROM telemetry_logs t1
    JOIN telemetry_logs t2
      ON t1.vessel_id = t2.vessel_id
     AND t1.speed_knots < t2.speed_knots
    WHERE t1.id < 200
    GROUP BY t1.vessel_id
    """,
    # Window function over the whole table
    """
    SELECT vessel_id, timestamp, fuel_consumption_lph,
           AVG(fuel_consumption_lph) OVER (PARTITION BY vessel_id
                                           ORDER BY timestamp
                                           ROWS BETWEEN 100 PRECEDING AND CURRENT ROW) AS rolling_avg
    FROM telemetry_logs
    """,
]


def main(repeats: int = 5) -> None:
    print("Scenario 01 — Slow queries")

    with db.get_connection() as conn:
        conn.autocommit = True
        for i, q in enumerate(HEAVY_QUERIES, 1):
            print(f"\nHeavy query #{i} × {repeats}")
            for r in range(repeats):
                with conn.cursor() as cur:
                    cur.execute(q)
                    rows = cur.fetchall()
                print(f"  run {r + 1}/{repeats}: returned {len(rows)} rows")

    print("\nDone. Open the Slow Queries page in ~30s (one collector cycle).")


if __name__ == "__main__":
    main()
