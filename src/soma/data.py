"""Shared data utilities for history save/load."""
import json
from pathlib import Path

from .config import DATA_DIR, HISTORY_FILE


def save_history(records: list) -> tuple[int, int, int]:
    """Merge records into history. Returns (total, new, updated)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            existing = json.load(f)
    else:
        existing = []

    existing_ids = {c["cycle_id"] for c in existing if c.get("cycle_id")}
    new_count = 0
    updated_count = 0

    for rec in records:
        rec = dict(rec)
        rec.setdefault("prescriptions", [])
        cid = rec.get("cycle_id")
        if not cid:
            continue
        if cid in existing_ids:
            for saved in existing:
                if saved.get("cycle_id") == cid:
                    if saved.get("recovery_score") is None and rec.get("recovery_score") is not None:
                        prescriptions = saved.get("prescriptions", [])
                        saved.update(rec)
                        saved["prescriptions"] = prescriptions
                        updated_count += 1
                    break
        else:
            existing.append(rec)
            existing_ids.add(cid)
            new_count += 1

    existing.sort(key=lambda x: x.get("date", ""), reverse=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(existing, f, indent=2)
    return len(existing), new_count, updated_count


def load_history() -> list:
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return []
