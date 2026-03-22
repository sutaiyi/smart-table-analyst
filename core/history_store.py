import json
import os

_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "history.json")
_MAX_RECORDS = 50


def _ensure_dir():
    os.makedirs(os.path.dirname(_HISTORY_FILE), exist_ok=True)


def _read_all() -> list[dict]:
    if not os.path.exists(_HISTORY_FILE):
        return []
    try:
        with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _write_all(records: list[dict]):
    _ensure_dir()
    with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def save_history(record: dict):
    records = _read_all()
    records.insert(0, record)
    records = records[:_MAX_RECORDS]
    _write_all(records)


def load_history() -> list[dict]:
    return _read_all()


def delete_history(record_id: int):
    records = _read_all()
    records = [r for r in records if r.get("id") != record_id]
    _write_all(records)


def update_history(record_id: int, updates: dict):
    records = _read_all()
    for rec in records:
        if rec.get("id") == record_id:
            rec.update(updates)
            break
    _write_all(records)


def clear_history():
    _write_all([])
