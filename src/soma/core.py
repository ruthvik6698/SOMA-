"""
SOMA decision loop: READ → SCORE → PRESCRIBE → ACT.
"""
import json
from datetime import datetime

import pytz

from .config import LOGS_DIR
from .modes import MODE_PRESCRIPTIONS, MOOD_PRESCRIPTIONS

LOG_PATH = LOGS_DIR / "soma.log"
IST = pytz.timezone("Asia/Kolkata")


def _log_prescription(entry: dict):
    """Log prescription in SOMA format."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def score_inputs(today: dict, baselines: dict) -> dict:
    """
    Score biometrics vs personal baselines.
    Returns: recovery_tier, hrv_tier, strain_tier, sleep_tier
    """
    rec = today.get("recovery_score")
    hrv = today.get("hrv")
    hrv_mean = baselines.get("hrv_mean", 60)
    hrv_std = baselines.get("hrv_std", 15)
    strain = today.get("day_strain")
    strain_avg = baselines.get("avg_strain", 10)
    sleep_perf = today.get("sleep_performance")
    sleep_hrs = today.get("sleep_duration_hrs")
    sleep_mean = baselines.get("sleep_mean", 7)
    rec_mean = baselines.get("recovery_mean", 50)

    # Recovery: HIGH (above 66 and above baseline), NORMAL, LOW (below 34 or below baseline)
    if rec is None:
        recovery_tier = "NORMAL"
    elif rec >= 66 and rec >= rec_mean:
        recovery_tier = "HIGH"
    elif rec < 34 or (rec_mean and rec < rec_mean - 10):
        recovery_tier = "LOW"
    else:
        recovery_tier = "NORMAL"

    # HRV: ABOVE (above mean+1SD), AT (±1SD), BELOW (below mean-1SD)
    if hrv is None:
        hrv_tier = "AT"
    elif hrv >= hrv_mean + hrv_std:
        hrv_tier = "ABOVE"
    elif hrv < hrv_mean - hrv_std:
        hrv_tier = "BELOW"
    else:
        hrv_tier = "AT"

    # Strain: LIGHT (< avg-2), NORMAL, HEAVY (> avg+3 or >14)
    if strain is None:
        strain_tier = "NORMAL"
    elif strain > 14 or strain > strain_avg + 3:
        strain_tier = "HEAVY"
    elif strain < strain_avg - 2:
        strain_tier = "LIGHT"
    else:
        strain_tier = "NORMAL"

    # Sleep: GOOD (≥ sleep_mean, perf ≥ 70), OK, POOR
    if sleep_hrs is None and sleep_perf is None:
        sleep_tier = "OK"
    elif sleep_perf is not None and sleep_perf < 50:
        sleep_tier = "POOR"
    elif sleep_hrs is not None and sleep_mean and sleep_hrs < sleep_mean - 1:
        sleep_tier = "POOR"
    elif sleep_perf is not None and sleep_perf >= 70:
        sleep_tier = "GOOD"
    else:
        sleep_tier = "OK"

    return {
        "recovery_tier": recovery_tier,
        "hrv_tier": hrv_tier,
        "strain_tier": strain_tier,
        "sleep_tier": sleep_tier,
    }


def infer_calendar_mode(calendar_events: list, hour: int, minute: int) -> str:
    """
    Infer current mode from calendar + time.
    Ruthvik's fixed blocks: 7:30-9:30 WORKOUT, 10-19 WORK, 19-20 TRANSITION, 20+ WIND_DOWN
    """
    mins = hour * 60 + minute

    if 5 * 60 + 30 <= mins < 5 * 60 + 45:
        return "SUNRISE_SIMULATION"
    if 5 * 60 + 45 <= mins < 7 * 60 + 30:
        return "MORNING_ACTIVE"
    if 7 * 60 + 30 <= mins < 9 * 60 + 30:
        return "WORKOUT_MODE"
    if 9 * 60 + 30 <= mins < 10 * 60:
        return "POST_WORKOUT_RECOVERY"
    if 19 * 60 <= mins < 20 * 60:
        return "TRANSITION"
    if mins >= 22 * 60:
        return "SLEEP_PREP"
    if mins >= 20 * 60:
        return "WIND_DOWN"

    # Check calendar for overrides (placeholder - events would come from Composio)
    for ev in (calendar_events or []):
        title = (ev.get("summary") or "").lower()
        if any(k in title for k in ["deep work", "focus", "writing", "build"]):
            return "DEEP_FOCUS"
        if any(k in title for k in ["meeting", "call", "sync", "standup", "review"]):
            return "MEETING_MODE"
        if any(k in title for k in ["lunch", "break", "walk"]):
            return "BREAK_MODE"
        if any(k in title for k in ["workout", "gym", "run", "training"]):
            return "WORKOUT_MODE"

    # Default work hours
    if 10 * 60 <= mins < 19 * 60:
        return "DEEP_FOCUS"
    if 12 * 60 <= mins < 13 * 60:
        return "BREAK_MODE"

    return "DEEP_FOCUS"


def select_mode(
    scores: dict,
    calendar_mode: str,
    weather: dict,
    mood: str | None,
    hour: int,
    minute: int,
) -> str:
    """
    Select environment mode from decision table.
    Mood overrides everything (expires after 90 min - caller checks).
    Hard rules: 22:00+ → SLEEP_PREP or WIND_DOWN; Red recovery + HRV below → RECOVERY_MODE
    """
    if mood:
        return f"MOOD_{mood.upper()}"

    # Hard rule: after 22:00 → max 2500K
    if hour >= 22:
        if minute >= 30 and (hour >= 23 or (hour == 22 and minute >= 30)):
            return "SLEEP_SIGNAL"
        return "SLEEP_PREP"
    if hour >= 20:
        return "WIND_DOWN"

    # Red recovery + HRV below = RECOVERY_MODE (override calendar)
    if scores.get("recovery_tier") == "LOW" and scores.get("hrv_tier") == "BELOW":
        return "RECOVERY_MODE"

    # Calendar-driven
    if calendar_mode == "WORKOUT_MODE":
        return "WORKOUT_MODE"
    if calendar_mode == "MEETING_MODE":
        return "MEETING_MODE"
    if calendar_mode == "BREAK_MODE":
        return "BREAK_MODE"
    if calendar_mode in ("SUNRISE_SIMULATION", "MORNING_ACTIVE", "POST_WORKOUT_RECOVERY", "TRANSITION"):
        return calendar_mode

    # Strain heavy + evening
    if hour >= 17 and scores.get("strain_tier") == "HEAVY":
        return "HEAVY_DAY_WIND_DOWN"

    # Focus modes by recovery + HRV
    if calendar_mode == "DEEP_FOCUS":
        if scores.get("recovery_tier") == "HIGH" and scores.get("hrv_tier") == "ABOVE":
            return "PEAK_FOCUS"
        if scores.get("recovery_tier") == "NORMAL" and scores.get("hrv_tier") in ("AT", "ABOVE"):
            return "DEEP_FOCUS"
        if scores.get("hrv_tier") == "BELOW":
            return "GENTLE_FOCUS"

    return "DEEP_FOCUS"


def get_mode_prescription(mode: str, weather: dict | None = None) -> dict:
    """
    Get full prescription for mode. Apply weather modifier.
    Hard rule: after 22:00 never exceed 2500K (caller enforces via mode selection).
    """
    if mode.startswith("MOOD_"):
        mood_key = mode.replace("MOOD_", "").lower()
        rx = MOOD_PRESCRIPTIONS.get(mood_key, MODE_PRESCRIPTIONS["DEEP_FOCUS"])
    else:
        rx = MODE_PRESCRIPTIONS.get(mode, MODE_PRESCRIPTIONS["DEEP_FOCUS"]).copy()

    # Weather modifier: overcast → +500K, +15% brightness
    if weather and isinstance(rx.get("light"), dict):
        cond = (weather.get("condition") or "").lower()
        if "cloud" in cond or "overcast" in cond or "mist" in cond:
            rx["light"] = dict(rx["light"])
            rx["light"]["color_temp"] = min(6500, rx["light"]["color_temp"] + 500)
            rx["light"]["brightness"] = min(100, rx["light"]["brightness"] + 15)

    return rx


def run_decision_loop(state: dict) -> dict | None:
    """
    READ → SCORE → PRESCRIBE. Returns prescription dict or None.
    Sets state["last_soma_mode"]. Caller handles ACT (push to devices).
    """
    today = state.get("today") or {}
    baselines = state.get("baselines") or {}
    weather = state.get("weather") or {}
    calendar_events = state.get("calendar_events") or []
    mood = state.get("mood_override")
    mood_ts = state.get("mood_override_at", 0)

    now = datetime.now(IST)
    hour, minute = now.hour, now.minute

    # Mood expires after 90 min
    if mood_ts:
        from datetime import datetime as dt
        elapsed = (dt.now().timestamp() - mood_ts) / 60
        if elapsed > 90:
            state["mood_override"] = None
            state["mood_override_at"] = None
            mood = None

    scores = score_inputs(today, baselines)
    calendar_mode = infer_calendar_mode(calendar_events, hour, minute)
    mode = select_mode(scores, calendar_mode, weather, mood, hour, minute)
    prescription = get_mode_prescription(mode, weather)

    # Enforce hard rule: 22:00+ max 2500K
    if hour >= 22 and prescription.get("light"):
        prescription["light"]["color_temp"] = min(2500, prescription["light"].get("color_temp", 2500))
        prescription["light"]["brightness"] = min(15, prescription["light"].get("brightness", 15))

    state["last_soma_mode"] = mode
    entry = {
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        "mode": mode,
        "inputs": {
            "recovery": today.get("recovery_score"),
            "hrv": today.get("hrv"),
            "hrv_baseline": baselines.get("hrv_mean"),
            "strain": today.get("day_strain"),
            "calendar": calendar_mode,
            "weather": f"{weather.get('temp_c', '?')}C, {weather.get('condition', 'unknown')}",
            "mood": mood,
        },
        "prescription": prescription,
        "reason": f"{mode} | Recovery {scores['recovery_tier']}, HRV {scores['hrv_tier']}, Strain {scores['strain_tier']}",
    }
    _log_prescription(entry)
    return prescription
