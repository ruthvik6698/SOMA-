"""
Evening wind-down (8pm–sleep) and bedtime signal.
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


def _recovery_tier(rec, baselines) -> str:
    """GREEN, YELLOW, or RED based on recovery vs personal baseline."""
    if rec is None:
        return "YELLOW"
    avg = baselines.get("recovery_mean", 50)
    if rec > 66:
        return "GREEN"
    if rec < 34:
        return "RED"
    return "YELLOW"


def _strain_high(today, baselines) -> bool:
    """True if strain > personal avg + 3."""
    strain = today.get("day_strain")
    avg = baselines.get("avg_strain", 10)
    if strain is None:
        return False
    return strain > avg + 3


def _get_wind_down_preset(tier: str, aggressive: bool) -> tuple[int, int]:
    """Returns (color_temp, brightness) for 8pm/9pm/10pm."""
    if aggressive:
        return (2700, 20), (2500, 12), (2500, 5)
    if tier == "GREEN":
        return (3000, 40), (2700, 25), (2500, 10)
    if tier == "YELLOW":
        return (2800, 30), (2600, 20), (2500, 8)
    return (2700, 20), (2500, 12), (2500, 5)


async def evening_start(state: dict):
    """8pm. First wind-down. Preset based on recovery + strain."""
    from src.light import set_light

    today = state.get("today") or {}
    baselines = state.get("baselines") or {}
    device = state.get("light")
    if not device:
        return

    tier = _recovery_tier(today.get("recovery_score"), baselines)
    aggressive = _strain_high(today, baselines)

    presets = _get_wind_down_preset(tier, aggressive)
    k, b = presets[0]

    await set_light(device, color_temp=k, brightness=b)
    state["last_prescription"] = {"color_temp": k, "brightness": b}
    rec = today.get("recovery_score") or 0
    strain = today.get("day_strain") or 0
    _log(f"EVENING_START | Recovery: {rec}% | Strain: {strain} | → {k}K, {b}%")
    print(f"[8pm] Wind-down started — {k}K, {b}%")


async def evening_check(state: dict):
    """9pm. Tighten further. Never above 2800K."""
    today = state.get("today") or {}
    baselines = state.get("baselines") or {}
    device = state.get("light")
    if not device:
        return

    tier = _recovery_tier(today.get("recovery_score"), baselines)
    aggressive = _strain_high(today, baselines)
    presets = _get_wind_down_preset(tier, aggressive)
    k, b = presets[1]

    await set_light(device, color_temp=k, brightness=b)
    state["last_prescription"] = {"color_temp": k, "brightness": b}
    _log(f"EVENING_CHECK | → {k}K, {b}%")
    print(f"[9pm] Wind-down — {k}K, {b}%")


async def deep_wind_down(state: dict):
    """10pm. Hard floor: 2500K, 10%. Non-negotiable."""
    from src.light import set_light

    device = state.get("light")
    if not device:
        return

    await set_light(device, color_temp=2500, brightness=10)
    state["last_prescription"] = {"color_temp": 2500, "brightness": 10}
    _log("DEEP_WIND_DOWN | → 2500K, 10%")
    print("[10pm] Deep wind-down — 2500K, 10%")


async def bedtime_signal(state: dict):
    """Blink 10 times to signal: time to sleep. Ends with light OFF."""
    from src.light import set_light, turn_off

    device = state.get("light")
    if not device:
        return

    for _ in range(10):
        await set_light(device, color_temp=2500, brightness=15)
        await asyncio.sleep(0.8)
        await turn_off(device)
        await asyncio.sleep(0.8)
    await turn_off(device)
    state["signal_sent"] = True
    _log("BEDTIME_SIGNAL | Sent 10 blinks | Light off")
    print("[Bedtime] Signal sent — 10 blinks, lights out")


async def bedtime_check(state: dict):
    """Check if we're past recommended/latest bedtime. Send signal if so."""
    import pytz
    from datetime import datetime

    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)
    hour, minute = now.hour, now.minute
    current_mins = hour * 60 + minute

    bedtime = state.get("bedtime") or {}
    rec_str = bedtime.get("recommended_bedtime", "23:00")
    latest_str = bedtime.get("latest_bedtime", "23:45")

    def parse_time(s):
        parts = s.split(":")
        h = int(parts[0]) if parts else 23
        m = int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m

    rec_mins = parse_time(rec_str)
    latest_mins = parse_time(latest_str)

    # Reset signal during day (6am–8pm) so we can send again tonight
    if 6 <= hour < 20:
        state["signal_sent"] = False

    if state.get("signal_sent"):
        return

    if current_mins >= latest_mins or current_mins >= rec_mins:
        await bedtime_signal(state)
