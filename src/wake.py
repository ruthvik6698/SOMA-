"""
Morning wake: SOMA sunrise simulation (5:30–5:45) and alarm pulse (5:45).
"""
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_PATH = PROJECT_ROOT / "logs" / "scheduler.log"


def _log(msg: str):
    from datetime import datetime
    import pytz
    ist = pytz.timezone("Asia/Kolkata")
    ts = datetime.now(ist).strftime("%Y-%m-%d %H:%M IST")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def _yesterday_recovery(state: dict) -> str:
    """GREEN, YELLOW, or RED from most recent scored day."""
    history = state.get("history") or []
    for c in history:
        rec = c.get("recovery_score")
        if rec is not None:
            if rec >= 66:
                return "GREEN"
            if rec < 34:
                return "RED"
            return "YELLOW"
    return "YELLOW"


async def sunrise_start(state: dict):
    """5:30am — SOMA: 2500K · 5% (near-dark amber)."""
    from src.light import set_light

    device = state.get("light")
    if not device:
        return

    await set_light(device, color_temp=2500, brightness=5)
    state["last_prescription"] = {"color_temp": 2500, "brightness": 5}
    _log("SUNRISE_START | SOMA 2500K, 5%")
    print("[5:30am] Sunrise simulation started.")


async def sunrise_ramp(state: dict):
    """
    SOMA sunrise: 5:30–5:45. Steps every ~3 min.
    5:30→2500K 5%, 5:33→3000K 15%, 5:36→3500K 35%, 5:39→4200K 55%, 5:42→5000K 75%, 5:43→peak (recovery-adjusted)
    """
    from src.light import set_light

    device = state.get("light")
    if not device:
        return

    tier = _yesterday_recovery(state)
    if tier == "GREEN":
        peak_k, peak_b = 6000, 100
    elif tier == "YELLOW":
        peak_k, peak_b = 5000, 90
    else:
        peak_k, peak_b = 4500, 75

    steps = [
        (2500, 5),
        (3000, 15),
        (3500, 35),
        (4200, 55),
        (5000, 75),
        (peak_k, peak_b),
    ]

    for k, b in steps:
        await set_light(device, color_temp=k, brightness=b)
        await asyncio.sleep(180)  # 3 min between steps

    state["last_prescription"] = {"color_temp": peak_k, "brightness": peak_b}
    _log(f"SUNRISE_RAMP | Recovery (yesterday): {tier} | Peak: {peak_k}K, {peak_b}%")
    print(f"[5:43am] Sunrise peak — {peak_k}K, {peak_b}%")


async def alarm_pulse(state: dict):
    """5:45am — SOMA: Blink 3×. Wake signal. Hold at recovery-adjusted level."""
    from src.light import set_light

    device = state.get("light")
    if not device:
        return

    tier = _yesterday_recovery(state)
    if tier == "GREEN":
        hold_k, hold_b = 6000, 100
    elif tier == "YELLOW":
        hold_k, hold_b = 5500, 90
    else:
        hold_k, hold_b = 4500, 75

    for _ in range(3):
        await set_light(device, color_temp=6500, brightness=100)
        await asyncio.sleep(1.5)
        await set_light(device, color_temp=5000, brightness=60)
        await asyncio.sleep(1.5)

    await set_light(device, color_temp=hold_k, brightness=hold_b)
    state["last_prescription"] = {"color_temp": hold_k, "brightness": hold_b}
    _log(f"ALARM_PULSE | Recovery (yesterday): {tier} | Hold: {hold_k}K, {hold_b}%")
    print(f"[5:45am] Alarm pulse complete. Wake light holding at {hold_k}K, {hold_b}%.")
