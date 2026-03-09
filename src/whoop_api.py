"""
Official WHOOP v2 API client.
"""
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / "config" / ".env"
load_dotenv(ENV_PATH)

BASE_URL = "https://api.prod.whoop.com/developer/v2"


def _headers():
    return {"Authorization": f"Bearer {os.getenv('WHOOP_ACCESS_TOKEN')}"}


def _get(endpoint, params=None):
    from .auth import refresh_token

    resp = requests.get(f"{BASE_URL}{endpoint}", headers=_headers(), params=params)
    if resp.status_code == 401:
        refresh_token()
        resp = requests.get(f"{BASE_URL}{endpoint}", headers=_headers(), params=params)
    resp.raise_for_status()
    return resp.json()


def get_profile():
    return _get("/user/profile/basic")


def get_today() -> dict:
    """Returns today's vitals. Handles nulls gracefully."""
    today = datetime.now().strftime("%Y-%m-%dT00:00:00.000Z")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z")

    cycles = _get("/cycle", params={"start": yesterday, "end": tomorrow, "limit": 5})
    cycle = cycles.get("records", [{}])[0] if cycles.get("records") else {}

    recovery_data = {}
    if cycle.get("id"):
        try:
            rec = _get(f"/cycle/{cycle['id']}/recovery")
            recovery_data = rec.get("score", {}) or {}
        except Exception:
            pass

    sleeps = _get("/activity/sleep", params={"start": yesterday, "end": tomorrow, "limit": 5})
    sleep_rec = sleeps.get("records", [{}])[0] if sleeps.get("records") else {}
    sleep = sleep_rec.get("score", {}) or {}
    stage = sleep.get("stage_summary", {}) or {}

    workouts = _get("/activity/workout", params={"start": today, "end": tomorrow, "limit": 10})
    workout_list = workouts.get("records", [])

    strain = cycle.get("score", {}) or {}

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "recovery_score": recovery_data.get("recovery_score"),
        "hrv": recovery_data.get("hrv_rmssd_milli"),
        "resting_hr": recovery_data.get("resting_heart_rate"),
        "spo2": recovery_data.get("spo2_percentage"),
        "skin_temp": recovery_data.get("skin_temp_celsius"),
        "sleep_score": sleep.get("sleep_performance_percentage"),
        "sleep_duration_hrs": round(stage.get("total_in_bed_time_milli", 0) / 3_600_000, 1),
        "sleep_performance": sleep.get("sleep_performance_percentage"),
        "rem_hrs": round(stage.get("total_rem_sleep_time_milli", 0) / 3_600_000, 1),
        "deep_hrs": round(stage.get("total_slow_wave_sleep_time_milli", 0) / 3_600_000, 1),
        "day_strain": strain.get("strain"),
        "avg_hr": strain.get("average_heart_rate"),
        "max_hr": strain.get("max_heart_rate"),
        "kilojoules": strain.get("kilojoule"),
        "workout_count": len(workout_list),
    }


def get_history(days=90) -> list:
    """Pull last N days of cycles with recovery and sleep."""
    start = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00.000Z")
    end = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z")

    records = []
    next_token = None

    while True:
        params = {"start": start, "end": end, "limit": 25}
        if next_token:
            params["nextToken"] = next_token

        data = _get("/cycle", params=params)
        cycles = data.get("records", [])

        for cycle in cycles:
            cycle_id = cycle.get("id")
            strain = cycle.get("score", {}) or {}

            recovery_data = {}
            try:
                rec = _get(f"/cycle/{cycle_id}/recovery")
                recovery_data = rec.get("score", {}) or {}
            except Exception:
                pass

            sleep_data = {}
            try:
                cycle_start = cycle.get("start", "")
                cycle_end = cycle.get("end", "") or end
                sleeps = _get("/activity/sleep", params={"start": cycle_start, "end": cycle_end, "limit": 1})
                sleep_rec = sleeps.get("records", [{}])[0] if sleeps.get("records") else {}
                sleep_data = sleep_rec.get("score", {}) or {}
            except Exception:
                pass

            stage = sleep_data.get("stage_summary", {}) or {}

            records.append({
                "cycle_id": cycle_id,
                "date": cycle.get("start", "")[:10],
                "recovery_score": recovery_data.get("recovery_score"),
                "hrv": recovery_data.get("hrv_rmssd_milli"),
                "resting_hr": recovery_data.get("resting_heart_rate"),
                "sleep_score": sleep_data.get("sleep_performance_percentage"),
                "sleep_performance": sleep_data.get("sleep_performance_percentage"),
                "sleep_duration_hrs": round(stage.get("total_in_bed_time_milli", 0) / 3_600_000, 1),
                "day_strain": strain.get("strain"),
                "avg_hr": strain.get("average_heart_rate"),
                "max_hr": strain.get("max_heart_rate"),
                "workout_count": 0,
                "prescriptions": [],
            })

        next_token = data.get("next_token")
        if not next_token:
            break

    return sorted(records, key=lambda x: x["date"], reverse=True)
