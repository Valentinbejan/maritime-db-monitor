# Scenario 06 — Unused index.
# Creates an index on telemetry_logs.fuel_consumption_lph that no normal
# query uses. The dashboard flags it as wasted disk + slower writes.
# Check the dashboard at: 🗂️ Index Health → Unused Indexes
# Run from project root:
#   python tests/scenarios/06_unused_index.py
#   python tests/scenarios/06_unused_index.py --cleanup

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import db


INDEX_NAME = "idx_scenario_unused_fuel"


def main() -> None:
    do_cleanup = "--cleanup" in sys.argv

    print("Scenario 06 — Unused index")

    with db.get_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            if do_cleanup:
                print(f"\nDropping {INDEX_NAME}")
                cur.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
                print(f"  dropped {INDEX_NAME}")
                return

            print(f"\nCreating {INDEX_NAME} on telemetry_logs(fuel_consumption_lph)")
            cur.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
            cur.execute(f"""
                CREATE INDEX {INDEX_NAME}
                ON telemetry_logs(fuel_consumption_lph)
            """)
            print(f"  created {INDEX_NAME}")

            print("\nIndex size + scan count")
            cur.execute("""
                SELECT
                    pg_size_pretty(pg_relation_size(indexrelid)) AS size,
                    idx_scan
                FROM pg_stat_user_indexes
                WHERE indexrelname = %s
            """, (INDEX_NAME,))
            row = cur.fetchone()
            if row:
                print(f"  size={row[0]}  idx_scan={row[1]}")

    print("\nDone. Check Index Health → Unused Indexes in ~30s.")
    print("Re-run with --cleanup to drop the index.")


if __name__ == "__main__":
    main()
