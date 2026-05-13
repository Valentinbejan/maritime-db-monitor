# Scenario 07 — Autovacuum stress.
# Creates a small table and rapidly churns rows. Postgres fires autovacuum
# when n_dead_tup > threshold (50) + scale_factor (0.2) × n_live_tup.
# With 2000 live rows, ~450 dead tuples triggers a vacuum within the next
# naptime window (default 60s).
# Check the dashboard at: 🧹 Autovacuum → Active Workers + vacuum_count
# Run from project root:
#   python tests/scenarios/07_autovacuum_stress.py
#   python tests/scenarios/07_autovacuum_stress.py --cleanup

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import db


TABLE = "scenario_autovacuum"
ROWS = 2000
PASSES = 5


def main() -> None:
    do_cleanup = "--cleanup" in sys.argv

    print("Scenario 07 — Autovacuum stress")

    with db.get_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            if do_cleanup:
                print(f"\nDropping {TABLE}")
                cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
                print(f"  dropped {TABLE}")
                return

            print(f"\nCreating {TABLE} with {ROWS:,} rows")
            cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
            cur.execute(f"""
                CREATE TABLE {TABLE} (
                    id   SERIAL PRIMARY KEY,
                    val  INT NOT NULL,
                    note TEXT
                )
            """)
            cur.execute(f"""
                INSERT INTO {TABLE} (val, note)
                SELECT g, 'init' FROM generate_series(1, %s) AS g
            """, (ROWS,))

            print(f"\nChurning ({PASSES} passes of full-table UPDATE)")
            for p in range(PASSES):
                cur.execute(f"UPDATE {TABLE} SET val = val + 1, note = 'pass_' || %s", (p,))
                print(f"  pass {p + 1}/{PASSES}: {cur.rowcount} rows updated")

            print("\nPre-vacuum stats")
            cur.execute("""
                SELECT n_live_tup, n_dead_tup,
                       autovacuum_count, last_autovacuum
                FROM pg_stat_user_tables
                WHERE relname = %s
            """, (TABLE,))
            row = cur.fetchone()
            if row:
                print(f"  live={row[0]}  dead={row[1]}  autovacuum_count={row[2]}  last={row[3]}")

            print("\nWaiting 75s for autovacuum naptime to fire…")
            for i in range(75):
                time.sleep(1)
                if (i + 1) % 15 == 0:
                    print(f"  {i + 1}s elapsed")

            print("\nPost-vacuum stats")
            cur.execute("""
                SELECT n_live_tup, n_dead_tup,
                       autovacuum_count, last_autovacuum
                FROM pg_stat_user_tables
                WHERE relname = %s
            """, (TABLE,))
            row = cur.fetchone()
            if row:
                print(f"  live={row[0]}  dead={row[1]}  autovacuum_count={row[2]}  last={row[3]}")

    print("\nDone. Check the Autovacuum page for the vacuum_count bump.")
    print("Re-run with --cleanup to drop the test table.")


if __name__ == "__main__":
    main()
