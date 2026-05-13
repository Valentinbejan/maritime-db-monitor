# Drops every table and index created by the scenario scripts.
# Safe to run repeatedly — uses IF EXISTS.
# Run from project root:   python tests/scenarios/cleanup_all.py

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import db


TABLES = [
    "scenario_bloat",
    "scenario_no_index",
    "scenario_autovacuum",
]

INDEXES = [
    "idx_scenario_unused_fuel",
]


def main() -> None:
    print("Scenario cleanup — drop all test artifacts")

    with db.get_connection() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            print("\nDropping tables")
            for t in TABLES:
                cur.execute(f"DROP TABLE IF EXISTS {t}")
                print(f"  - {t}")

            print("\nDropping indexes")
            for i in INDEXES:
                cur.execute(f"DROP INDEX IF EXISTS {i}")
                print(f"  - {i}")

    print("\nAll scenario artifacts removed.")


if __name__ == "__main__":
    main()
