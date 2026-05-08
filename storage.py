"""
storage.py — JSON Lines (.jsonl) read / write helpers.
Each line in a .jsonl file is a self-contained JSON object with a
'timestamp' field, making it easy to append and stream.
"""

import json
import os
from datetime import datetime, timezone

import config

# Maximum lines to keep per file (avoids unbounded growth in a demo app)
MAX_LINES = 100_000


def _ensure_dir():
    """Create the data/metrics directory if it doesn't exist."""
    os.makedirs(config.DATA_DIR, exist_ok=True)


def append_metric(filepath: str, data: dict) -> None:
    """
    Append a single metric record as a JSON line.
    Automatically adds an ISO-8601 'timestamp' if not present.
    """
    _ensure_dir()
    if "timestamp" not in data:
        data["timestamp"] = datetime.now(timezone.utc).isoformat()

    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, default=str) + "\n")


def read_metrics(filepath: str, since: datetime = None) -> list[dict]:
    """
    Read all metric records from a JSONL file.
    If 'since' is provided, only return records with timestamp >= since.
    Returns an empty list if the file doesn't exist.
    """
    if not os.path.exists(filepath):
        return []

    records = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if since is not None:
                ts_str = record.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(ts_str)
                    if ts < since:
                        continue
                except (ValueError, TypeError):
                    continue

            records.append(record)
    return records


def read_latest(filepath: str) -> dict | None:
    """
    Read the last (most recent) record from a JSONL file.
    Efficient: reads from the end of the file.
    Returns None if the file is empty or doesn't exist.
    """
    if not os.path.exists(filepath):
        return None

    last_line = None
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                last_line = stripped

    if last_line is None:
        return None

    try:
        return json.loads(last_line)
    except json.JSONDecodeError:
        return None


def rotate_if_needed(filepath: str) -> None:
    """
    If the file exceeds MAX_LINES, keep only the last half.
    This prevents unbounded file growth in long-running demos.
    """
    if not os.path.exists(filepath):
        return

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) > MAX_LINES:
        # Keep the most recent half
        keep = lines[len(lines) // 2:]
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(keep)


def get_last_modified(filepath: str) -> datetime | None:
    """Return the last-modified time of a file, or None if it doesn't exist."""
    if not os.path.exists(filepath):
        return None
    mtime = os.path.getmtime(filepath)
    return datetime.fromtimestamp(mtime, tz=timezone.utc)
