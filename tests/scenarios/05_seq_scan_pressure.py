# Scenario 05 — Sequential scan pressure.
# Creates an unindexed table, fills it, then runs many full-table scans.
# Inflates the seq_scan counter that drives the "Missing Indexes" panel.
# Check the dashboard at: 🗂️ Index Health → Missing Indexes (look for
# scenario_no_index with seq_scan_pct ≈ 100%)
# Run from project root:
#   python tests/scenarios/05_seq_scan_pressure.py
#   python tests/scenarios/05_seq_scan_pressure.py --cleanup

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import db


TABLE = "scenario_no_index"
ROWS = 5000
SCANS = 200


def main() -> None:
    if "--cleanup" in sys.argv:
        print("Scenario 05 — cleanup")
        with db.get_connection() as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
        print(f"  dropped {TABLE}")
        return

    print("Scenario 05 — Sequential scan pressure")

    with db.get_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            print(f"\nCreating {TABLE} ({ROWS:,} rows, no indexes)")
            cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
            cur.execute(f"""
                CREATE TABLE {TABLE} (
                    id    INT,
                    val   INT,
                    name  TEXT
                )
            """)
            cur.execute(f"""
                INSERT INTO {TABLE} (id, val, name)
                SELECT g, (random() * 1000000)::int, 'row_' || g
                FROM generate_series(1, %s) AS g
            """, (ROWS,))

            print(f"\nRunning {SCANS} full-table scans")
            for i in range(SCANS):
                cur.execute(f"SELECT * FROM {TABLE} WHERE val = %s", (i * 37,))
                cur.fetchall()
                if (i + 1) % 50 == 0:
                    print(f"  {i + 1}/{SCANS} scans")

            print("\nFinal seq_scan counter")
            cur.execute("""
                SELECT seq_scan, idx_scan, seq_tup_read
                FROM pg_stat_user_tables
                WHERE relname = %s
            """, (TABLE,))
            row = cur.fetchone()
            if row:
                print(f"  seq_scan={row[0]}  idx_scan={row[1] or 0}  seq_tup_read={row[2]:,}")

    print("\nDone. Check Index Health in ~30s.")
    print("Re-run with --cleanup to drop the test table.")


if __name__ == "__main__":
    main()
