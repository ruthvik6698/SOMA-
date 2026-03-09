"""
AI brain: SOMA decision loop integration, bedtime decisions.
Light prescriptions come from SOMA modes; bedtime uses OpenAI.
"""
import json
import os

import pytz
from openai import OpenAI

from .config import SCHEDULER_LOG as LOG_PATH
IST = pytz.timezone("Asia/Kolkata")


def _log(msg: str):
    from datetime import datetime
    ts = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def get_plan_and_light(state: dict, weather: dict) -> dict:
    """
    SOMA-driven: run decision loop, return plan + light.
    Replaces old AI-based plan. Plan is derived from mode reason.
    """
    from . import run_decision_loop

    state["weather"] = weather
    prescription = run_decision_loop(state)
    if not prescription:
        return {"plan": state.get("plan", ""), "color_temp": 4000, "brightness": 70, "reason": "Fallback"}

    light = prescription.get("light") or {}
    mode = state.get("last_soma_mode", "DEEP_FOCUS")
    reason = f"{mode} | Recovery vs baseline, HRV, strain"
    return {
        "plan": f"SOMA: {mode}",
        "color_temp": light.get("color_temp", 4000),
        "brightness": light.get("brightness", 70),
        "reason": reason,
    }


def get_light_prescription(today: dict, baselines: dict, context: str) -> dict:
    """
    Legacy: returns light for a context. Uses SOMA scoring + mode selection.
    """
    from . import score_inputs, select_mode, get_mode_prescription, infer_calendar_mode
    from datetime import datetime

    now = datetime.now(IST)
    h, m = now.hour, now.minute
    scores = score_inputs(today, baselines)
    cal_mode = infer_calendar_mode([], h, m)
    mode = select_mode(scores, cal_mode, {}, None, h, m)
    rx = get_mode_prescription(mode, None)
    light = rx.get("light") or {}
    return {
        "color_temp": light.get("color_temp", 4000),
        "brightness": light.get("brightness", 70),
        "reason": f"{mode}",
    }


def decide_bedtime(state: dict) -> dict:
    """
    Called at 22:30 IST. Uses SOMA formula + OpenAI fallback.
    Stores result in state["bedtime"].
    """
    today = state.get("today") or {}
    baselines = state.get("baselines") or {}
    history = state.get("history") or []

    strain = today.get("day_strain") or 0
    sleep_perf = today.get("sleep_performance") or 70
    hrv = today.get("hrv")
    hrv_mean = baselines.get("hrv_mean", 60)
    rec = today.get("recovery_score") or 50
    sleep_mean = baselines.get("sleep_mean", 7)
    sleep_hrs = today.get("sleep_duration_hrs") or 7

    # SOMA formula
    base_mins = 23 * 60  # 23:00
    if strain > 14:
        base_mins -= 30
    if sleep_perf < 80 and sleep_hrs < sleep_mean:
        base_mins -= 20
    if hrv is not None and hrv < hrv_mean:
        base_mins -= 15
    if rec < 40:
        base_mins -= 30
    if rec >= 66 and hrv is not None and hrv >= hrv_mean:
        base_mins += 15

    base_mins = max(21 * 60, min(24 * 60, base_mins))
    rec_h = base_mins // 60
    rec_m = base_mins % 60
    recommended = f"{rec_h:02d}:{rec_m:02d}"
    latest_mins = base_mins + 45
    latest_mins = min(24 * 60, latest_mins)
    lh = latest_mins // 60
    lm = latest_mins % 60
    if lh >= 24:
        lh = 23
        lm = 59
    latest = f"{lh:02d}:{lm:02d}"

    pressure = "high" if strain > 14 or rec < 40 else ("low" if rec >= 66 else "medium")
    reasoning = f"Strain {strain:.1f}, recovery {rec}%, HRV vs baseline. Base 23:00, adjusted."
    result = {
        "recommended_bedtime": recommended,
        "latest_bedtime": latest,
        "reasoning": reasoning,
        "sleep_pressure": pressure,
    }
    state["bedtime"] = result
    _log(f"BEDTIME_DECISION | Recommended: {recommended} | Latest: {latest} | {reasoning} | Pressure: {pressure}")
    return result
