# Scenario 03 — Idle in transaction.
# Opens a transaction, runs a small SELECT, then sleeps with the tx OPEN.
# Postgres reports the connection as state='idle in transaction'.
# Uses a raw psycopg2 connection (not the pool) so the tx state sticks.
# Check the dashboard at: 📊 Overview → Connection Breakdown, sidebar "Idle in TX"
# Run from project root:
#   python tests/scenarios/03_idle_in_transaction.py            # 60s default
#   python tests/scenarios/03_idle_in_transaction.py 30         # custom seconds

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg2

import config


def main(duration: int = 60) -> None:
    print(f"Scenario 03 — Idle in transaction ({duration}s)")

    conn = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            print("\nStarting transaction with a small SELECT")
            cur.execute("SELECT count(*) FROM vessels")
            print(f"  vessels: {cur.fetchone()[0]}")

        print(f"\nSleeping {duration}s with open transaction…")
        for i in range(duration):
            time.sleep(1)
            if (i + 1) % 5 == 0:
                print(f"  {i + 1}s elapsed")

    finally:
        conn.rollback()
        conn.close()
        print("\nTransaction rolled back, connection closed.")


if __name__ == "__main__":
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    main(dur)
