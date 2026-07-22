"""JSON file store for seen repos and push history."""
import json
import os
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _read_json(filename):
    """Read JSON file, return default if missing or corrupt."""
    _ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    default: dict | list = {} if filename == "seen.json" else []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json(filename, data):
    """Atomically write JSON file."""
    _ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# --- Seen repos ---

def load_seen() -> dict:
    return _read_json("seen.json")


def save_seen(data: dict) -> None:
    _write_json("seen.json", data)


def is_seen(repo_id: int) -> bool:
    return str(repo_id) in load_seen()


def mark_seen(repo_id: int, score: int, source: str = "daily") -> None:
    data = load_seen()
    data[str(repo_id)] = {
        "score": score,
        "pushed_at": datetime.now().strftime("%Y-%m-%d"),
        "source": source,
    }
    save_seen(data)


# --- History ---

def load_history() -> list:
    return _read_json("history.json")


def add_history_entry(entry: dict) -> None:
    history = load_history()
    history.append(entry)
    _write_json("history.json", history)


def get_history_for_period(days: int) -> list:
    """Return history entries from the last `days` days."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [e for e in load_history() if e.get("date", "") >= cutoff]
