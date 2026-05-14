# Scenario 04 — Connection storm.
# Opens many parallel connections, holds them idle, then closes them.
# Demonstrates the connection breakdown and the "High connection count" alert.
# Check the dashboard at: Overview -> Connection Breakdown,  AI Insights
# Run from project root:
#   python tests/scenarios/04_connection_storm.py             # 30 conns × 30s
#   python tests/scenarios/04_connection_storm.py 50 20       # custom N + secs

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import psycopg2

import config


def open_conn():
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )


def main(n: int = 30, duration: int = 30) -> None:
    print(f"Scenario 04 — Connection storm ({n} conns × {duration}s)")

    conns = []
    try:
        print(f"\nOpening {n} connections")
        for i in range(n):
            try:
                conns.append(open_conn())
                if (i + 1) % 10 == 0:
                    print(f"  opened {i + 1}/{n}")
            except Exception as e:
                print(f"  FAILED to open connection #{i + 1}: {e}")
                break
        print(f"  total open: {len(conns)}")

        print(f"\nHolding idle for {duration}s")
        for i in range(duration):
            time.sleep(1)
            if (i + 1) % 5 == 0:
                print(f"  {i + 1}s elapsed")

    finally:
        print("\nClosing all connections")
        for c in conns:
            try:
                c.close()
            except Exception:
                pass
        print(f"  closed {len(conns)} connections")

    print("\nDone. The active/idle counts will drop in ~30s.")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    dur = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    main(n, dur)
