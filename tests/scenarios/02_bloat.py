# Scenario 02 — Table bloat (dead tuples).
# Creates a `scenario_bloat` table, then churns it with UPDATEs to generate
# many dead tuples without growing the live-row count.
# Check the dashboard at: Overview -> Table Bloat,  Autovacuum -> Dead %
# Run from project root:
#   python tests/scenarios/02_bloat.py
#   python tests/scenarios/02_bloat.py --cleanup     # drop the test table

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import db


TABLE = "scenario_bloat"
ROWS = 5000
UPDATE_PASSES = 10


def setup(cur) -> None:
    cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
    cur.execute(f"""
        CREATE TABLE {TABLE} (
            id   SERIAL PRIMARY KEY,
            val  INT NOT NULL
        )
    """)
    cur.execute(f"""
        INSERT INTO {TABLE} (val)
        SELECT g FROM generate_series(1, %s) AS g
    """, (ROWS,))


def churn(cur) -> None:
    for p in range(UPDATE_PASSES):
        cur.execute(f"UPDATE {TABLE} SET val = val + 1")
        print(f"  pass {p + 1}/{UPDATE_PASSES}: updated {cur.rowcount} rows")


def report(cur) -> None:
    cur.execute("""
        SELECT n_live_tup, n_dead_tup
        FROM pg_stat_user_tables
        WHERE relname = %s
    """, (TABLE,))
    row = cur.fetchone()
    if row:
        live, dead = row
        print(f"  live={live}  dead={dead}")
    else:
        print("  (no stats yet — autovacuum hasn't sampled this table)")


def cleanup(cur) -> None:
    cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
    print(f"  dropped {TABLE}")


def main() -> None:
    do_cleanup = "--cleanup" in sys.argv

    print("Scenario 02 — Table bloat")

    with db.get_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            if do_cleanup:
                print("\nCleanup")
                cleanup(cur)
                return

            print(f"\nCreating {TABLE} with {ROWS:,} rows")
            setup(cur)

            print(f"\nChurning rows ({UPDATE_PASSES} passes)")
            churn(cur)

            print("\nFinal pg_stat_user_tables row")
            report(cur)

    print("\nDone. Check Overview → Table Bloat in ~30s.")
    print("Re-run with --cleanup to drop the test table.")


if __name__ == "__main__":
    main()
