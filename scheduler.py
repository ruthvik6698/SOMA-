#!/usr/bin/env python3
"""
SOMA — Biometric environment controller.
AI-driven hourly loop: READ → SCORE → PRESCRIBE → ACT.
Runs sunrise, wind-down, bedtime sequences at fixed times; daytime is SOMA decision loop.
"""
import asyncio
import json
import os
import re
import sys
import threading
from datetime import datetime
from pathlib import Path

import pytz
from dotenv import load_dotenv
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / "config" / ".env")

IST = pytz.timezone("Asia/Kolkata")
LOG_PATH = PROJECT_ROOT / "logs" / "scheduler.log"

# Shared state (SOMA)
state = {
    "light": None,
    "fan": None,
    "today": None,
    "baselines": None,
    "history": [],
    "weather": None,
    "calendar_events": [],
    "mood_override": None,
    "mood_override_at": None,
    "bedtime": None,
    "signal_sent": False,
    "last_prescription": None,
    "last_soma_mode": None,
    "paused": False,
    "running": True,
    "last_soma_hour": None,
    "last_calendar_refresh": None,
    "sequence_task": None,
    "sequence_cancelled": False,
    "plan": "",
}

SYSTEM_PROMPT_TEMPLATE = '''You are SOMA, an intelligent biometric environment controller. You control lights and devices based on WHOOP data.

PERSONALITY: Direct, science-literate. One sentence when asked why. Never hedge.

CONTEXT:
{context_block}

LIGHT COMMAND FORMAT - end with exactly one JSON block:
Set: ```json
{{"action": "set_light", "color_temp": <2500-6500>, "brightness": <5-100>}}
```
Off: ```json
{{"action": "turn_off"}}
```
Sequence: ```json
{{"action": "sequence", "steps": [{{"color_temp": 2500, "brightness": 1}}, ...], "delay_seconds": 3}}
```
None: ```json
{{"action": "none"}}
```

HARD RULE: After 22:00 → max 2500K. No exceptions.
RESPONSE: 1-3 sentences max. Never output raw numbers.
'''


def _log(msg: str):
    ts = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def now_ist():
    return datetime.now(IST)


def refresh_data():
    from src.whoop_api import get_today, get_history
    from src.baselines import compute_baselines
    from src.data import save_history, load_history

    state["today"] = get_today()
    records = get_history(90)
    save_history(records)
    state["history"] = load_history()
    state["baselines"] = compute_baselines(state["history"])


def refresh_weather():
    from src.weather import get_weather
    state["weather"] = get_weather()


def refresh_calendar():
    from src.calendar import get_today_events
    state["calendar_events"] = get_today_events()
    state["last_calendar_refresh"] = now_ist()


def _meaningful_change(last: dict | None, new: dict) -> bool:
    if not last:
        return True
    k_old = last.get("color_temp") or 4000
    b_old = last.get("brightness") or 50
    light = new.get("light") or new
    k_new = (light.get("color_temp") if isinstance(light, dict) else light.get("color_temp")) or 4000
    b_new = (light.get("brightness") if isinstance(light, dict) else light.get("brightness")) or 50
    return abs(k_new - k_old) > 200 or abs(b_new - b_old) > 15


async def _apply_prescription(prescription: dict):
    """Apply SOMA prescription to light (and fan when available)."""
    from src.light import set_light, turn_off
    from src.devices import set_fan_speed

    device = state.get("light")
    if not device:
        return

    light = prescription.get("light")
    if light:
        k = light.get("color_temp")
        b = light.get("brightness")
        if k is not None and b is not None:
            await set_light(device, color_temp=k, brightness=b)
            state["last_prescription"] = {"color_temp": k, "brightness": b}
        elif b == 0:
            await turn_off(device)
            state["last_prescription"] = None

    fan_level = prescription.get("fan")
    if fan_level is not None:
        await set_fan_speed(state.get("fan"), fan_level)


async def soma_tick():
    """
    SOMA decision loop: READ → SCORE → PRESCRIBE → ACT.
    Runs every hour (and on startup). Skips during sunrise (5:30-5:45) and fixed evening sequences.
    """
    if state.get("paused"):
        return

    now = now_ist()
    h, m = now.hour, now.minute

    # Skip during sunrise ramp
    if 5 * 60 + 30 <= h * 60 + m < 5 * 60 + 45:
        return

    device = state.get("light")
    if not device:
        return

    # Refresh data every 2 hours
    if h % 2 == 0 and m <= 5:
        refresh_data()
        refresh_weather()
    if state.get("last_calendar_refresh") is None or (now - (state["last_calendar_refresh"] or now)).seconds > 30 * 60:
        refresh_calendar()

    from src.soma import run_decision_loop

    prescription = run_decision_loop(state)
    if not prescription:
        return

    light_rx = prescription.get("light") or {}
    rx_simple = {"color_temp": light_rx.get("color_temp", 4000), "brightness": light_rx.get("brightness", 70)}
    if not _meaningful_change(state.get("last_prescription"), rx_simple):
        _log(f"SOMA_TICK | {h}:{m:02d} | no change | {state.get('last_soma_mode', '')}")
        return

    await _apply_prescription(prescription)
    mode = state.get("last_soma_mode", "?")
    _log(f"SOMA_TICK | {h}:{m:02d} | {mode} | → {rx_simple['color_temp']}K, {rx_simple['brightness']}%")
    print(f"[{h}:{m:02d}] SOMA: {mode} — {rx_simple['color_temp']}K, {rx_simple['brightness']}%")


def _get_context_block() -> str:
    today = state.get("today") or {}
    baselines = state.get("baselines") or {}
    t = now_ist()
    hour = t.hour % 12 or 12
    ampm = "AM" if t.hour < 12 else "PM"
    current_time = f"{hour}:{t.minute:02d} {ampm}"
    rec = today.get("recovery_score")
    hrv = today.get("hrv")
    rhr = today.get("resting_hr")
    sleep_perf = today.get("sleep_performance")
    sleep_hrs = today.get("sleep_duration_hrs")
    strain = today.get("day_strain")
    return f"""
Time: {current_time}
Recovery: {rec if rec is not None else 'not yet scored'}% (avg: {baselines.get('recovery_mean', 50):.0f}%)
HRV: {hrv if hrv is not None else 'unavailable'}ms (avg: {baselines.get('hrv_mean', 60):.0f}ms)
RHR: {rhr if rhr is not None else 'unavailable'}bpm
Sleep: {sleep_perf if sleep_perf is not None else 'unavailable'}% perf, {sleep_hrs if sleep_hrs is not None else 'unavailable'}hrs (avg: {baselines.get('sleep_mean', 7):.1f}hrs)
Strain: {strain if strain is not None else 'unavailable'} (avg: {baselines.get('avg_strain', 10):.1f})
"""


def _parse_json_from_reply(reply: str) -> dict | None:
    matches = list(re.finditer(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", reply))
    if not matches:
        return None
    try:
        return json.loads(matches[-1].group(1).strip())
    except json.JSONDecodeError:
        return None


def _strip_json_from_reply(reply: str) -> str:
    return re.sub(r"\s*```(?:json)?\s*\{[\s\S]*?\}\s*```\s*$", "", reply).strip()


def _abort_sequence():
    state["sequence_cancelled"] = True
    task = state.get("sequence_task")
    if task and not task.done():
        task.cancel()
    state["sequence_task"] = None


async def _run_sequence(cmd: dict):
    from src.light import set_light, turn_off
    device = state.get("light")
    if not device:
        state["sequence_task"] = None
        return
    steps = cmd.get("steps", [])
    delay = max(0.5, min(60, float(cmd.get("delay_seconds", 3))))
    state["sequence_cancelled"] = False
    try:
        for i, step in enumerate(steps):
            if state.get("sequence_cancelled"):
                break
            if step.get("action") == "turn_off":
                await turn_off(device)
            else:
                await set_light(
                    device,
                    color_temp=step.get("color_temp"),
                    hue=step.get("hue"),
                    saturation=step.get("saturation"),
                    brightness=step.get("brightness", 50),
                )
            if i < len(steps) - 1:
                await asyncio.sleep(delay)
    except asyncio.CancelledError:
        pass
    finally:
        state["sequence_task"] = None


async def _execute_light_command(cmd: dict):
    if not cmd:
        return
    from src.light import set_light, turn_off
    device = state.get("light")
    if not device:
        return
    try:
        action = cmd.get("action", "none")
        if action == "turn_off":
            _abort_sequence()
            await turn_off(device)
            state["last_prescription"] = None
            return
        if action == "sequence":
            _abort_sequence()
            state["sequence_task"] = asyncio.create_task(_run_sequence(cmd))
            return
        if action != "set_light":
            return
        _abort_sequence()
        await set_light(
            device,
            color_temp=cmd.get("color_temp"),
            hue=cmd.get("hue"),
            saturation=cmd.get("saturation"),
            brightness=cmd.get("brightness", 50),
        )
        state["last_prescription"] = {"color_temp": cmd.get("color_temp"), "brightness": cmd.get("brightness")}
    except (asyncio.CancelledError, Exception):
        pass


def _call_openai_cli(messages: list) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(model="gpt-4o", messages=messages)
    return resp.choices[0].message.content or ""


def _should_run_at(hour: int, minute: int) -> bool:
    """Run once per (hour, minute) per day."""
    now = now_ist()
    if now.hour != hour or now.minute > minute + 1:
        return False
    key = f"{hour}:{minute}"
    last = state.get("_last_run", {}).get(key)
    today = now.date()
    if last == today:
        return False
    if "_last_run" not in state:
        state["_last_run"] = {}
    state["_last_run"][key] = today
    return True


async def _run_scheduler_tick():
    if state.get("paused"):
        return

    now = now_ist()
    h, m = now.hour, now.minute
    mins = h * 60 + m
    device = state.get("light")
    if not device:
        return

    # Evening wind-down (SOMA schedule)
    if _should_run_at(20, 0):
        from src.sleep_prep import evening_start
        await evening_start(state)
    elif _should_run_at(21, 0):
        from src.sleep_prep import evening_check
        await evening_check(state)
    elif _should_run_at(22, 0):
        from src.sleep_prep import deep_wind_down
        await deep_wind_down(state)
    elif _should_run_at(22, 30):
        from src.decider import decide_bedtime
        decide_bedtime(state)
    elif _should_run_at(23, 0) or _should_run_at(23, 30) or _should_run_at(0, 0):
        from src.sleep_prep import bedtime_check
        await bedtime_check(state)

    # Morning sunrise
    elif _should_run_at(5, 30):
        from src.wake import sunrise_start, sunrise_ramp
        await sunrise_start(state)
        asyncio.create_task(sunrise_ramp(state))
    elif _should_run_at(5, 45):
        from src.wake import alarm_pulse
        await alarm_pulse(state)

    # SOMA hourly tick (every hour, skip sunrise window)
    if state.get("last_soma_hour") != h and not (5 * 60 + 30 <= mins < 5 * 60 + 45):
        state["last_soma_hour"] = h
        await soma_tick()


async def _process_cli_command(line: str, messages: list) -> list:
    line = line.strip().lower()
    if not line:
        return messages

    if line in ("quit", "exit", "q"):
        state["running"] = False
        print("Bye.")
        return messages

    if line == "pause":
        _abort_sequence()
        state["paused"] = True
        print("⏸ Automation paused. Type 'resume' to continue.")
        return messages

    if line == "stop":
        _abort_sequence()
        print("⏹ Stopped any running sequence.")
        return messages

    if line == "resume":
        state["paused"] = False
        print("▶ Automation resumed.")
        return messages

    if line == "status":
        today = state.get("today") or {}
        rec = today.get("recovery_score")
        hrv = today.get("hrv")
        sleep = today.get("sleep_performance")
        sleep_hrs = today.get("sleep_duration_hrs")
        strain = today.get("day_strain")
        rec_s = f"{rec}%" if rec is not None else "—"
        hrv_s = f"{hrv}ms" if hrv is not None else "—"
        sleep_s = f"{sleep}%" if sleep is not None else "—"
        sleep_hrs_s = f"{sleep_hrs}hrs" if sleep_hrs is not None else "—"
        strain_s = f"{strain:.1f}" if strain is not None else "—"
        mood = state.get("mood_override") or "—"
        print(f"Recovery: {rec_s} | HRV: {hrv_s} | Sleep: {sleep_s} ({sleep_hrs_s}) | Strain: {strain_s} | Mood: {mood}")
        return messages

    if line == "history":
        history = state.get("history") or []
        lines = ["date       | recovery | hrv   | sleep | strain", "-" * 45]
        for c in history[:14]:
            d = c.get("date", "?")
            r = c.get("recovery_score")
            hv = c.get("hrv")
            s = c.get("sleep_performance")
            st = c.get("day_strain")
            r_s = f"{r}%" if r is not None else "—"
            h_s = f"{hv}ms" if hv is not None else "—"
            s_s = f"{s}%" if s is not None else "—"
            st_s = f"{st:.1f}" if st is not None else "—"
            lines.append(f"{d} | {r_s:8} | {h_s:5} | {s_s:5} | {st_s}")
        print("\n".join(lines))
        return messages

    if line == "refresh":
        refresh_data()
        refresh_weather()
        refresh_calendar()
        print("Data refreshed.")
        return messages

    # Mood quick-set
    mood_map = {"stressed": "stressed", "flat": "flat", "focus": "focused", "focused": "focused", "wind down": "winding_down", "winding down": "winding_down", "energised": "energised"}
    if line in mood_map:
        from src.mood import set_mood_override
        if set_mood_override(state, mood_map[line]):
            print(f"Mood set: {mood_map[line]}. Overrides environment for 90 min.")
        return messages

    # Natural language → OpenAI
    context = _get_context_block()
    sys_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{context_block}", context)
    if not messages or messages[0].get("role") != "system":
        messages = [{"role": "system", "content": sys_prompt}]
    else:
        messages[0]["content"] = sys_prompt

    messages.append({"role": "user", "content": line})
    reply = _call_openai_cli(messages)
    messages.append({"role": "assistant", "content": reply})

    cmd = _parse_json_from_reply(reply)
    demo_keywords = ("demo", "sunrise", "wake up", "show me")
    fast_keywords = ("fast", "quick", "speed")
    if (not cmd or cmd.get("action") == "none") and any(k in line for k in demo_keywords):
        delay = 1 if any(k in line for k in fast_keywords) else 2
        cmd = {
            "action": "sequence",
            "steps": [
                {"color_temp": 2500, "brightness": 1},
                {"color_temp": 3000, "brightness": 25},
                {"color_temp": 4000, "brightness": 55},
                {"color_temp": 5500, "brightness": 95},
            ],
            "delay_seconds": delay,
        }
    if cmd:
        await _execute_light_command(cmd)
    print(f"\nSOMA: {_strip_json_from_reply(reply)}")
    return messages


def _input_thread(queue: asyncio.Queue, loop):
    while state.get("running", True):
        try:
            line = input("\nYou: ")
            loop.call_soon_threadsafe(queue.put_nowait, line)
        except EOFError:
            loop.call_soon_threadsafe(queue.put_nowait, "__EOF__")
            break
        except Exception:
            break


async def main_async():
    from src.auth import ensure_authenticated
    from src.light import connect_light, disconnect_light
    from src.devices import connect_fan

    if not all([os.getenv("TAPO_IP") or os.getenv("TAPO_DEVICE_IP"), os.getenv("TAPO_EMAIL"), os.getenv("TAPO_PASSWORD")]):
        print("Error: TAPO_IP, TAPO_EMAIL, TAPO_PASSWORD required in config/.env")
        sys.exit(1)
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY required in config/.env")
        sys.exit(1)

    ensure_authenticated()
    from src.whoop_api import get_profile
    profile = get_profile()
    name = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
    refresh_data()
    refresh_weather()
    refresh_calendar()
    state["light"] = await connect_light()
    state["fan"] = connect_fan()
    print(f"✅ WHOOP connected — {name} | 💡 Tapo: {state['light'].alias}")
    print(f"📊 Baselines: HRV {state['baselines']['hrv_mean']:.0f}ms | Recovery {state['baselines']['recovery_mean']:.0f}% | Sleep {state['baselines']['sleep_mean']:.1f}hrs")
    _log("SOMA scheduler started. Wake target: 05:45 IST.")

    # Initial SOMA tick
    h = now_ist().hour
    m = now_ist().minute
    mins = h * 60 + m
    if 6 <= h <= 19:
        await soma_tick()
    elif h == 20:
        from src.sleep_prep import evening_start
        await evening_start(state)
    elif h == 21:
        from src.sleep_prep import evening_check
        await evening_check(state)
    elif h >= 22 or h < 6:
        from src.sleep_prep import deep_wind_down
        await deep_wind_down(state)

    print("SOMA running (IST). Commands: pause | resume | stop | status | history | refresh | stressed | flat | focus | wind down | quit | or say anything\n")

    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    t = threading.Thread(target=_input_thread, args=(queue, loop), daemon=True)
    t.start()

    messages = []
    while state.get("running", True):
        try:
            line = await asyncio.wait_for(queue.get(), timeout=30.0)
            if line == "__EOF__":
                break
            messages = await _process_cli_command(line, messages)
        except asyncio.TimeoutError:
            await _run_scheduler_tick()

    try:
        await disconnect_light(state["light"])
    except (asyncio.CancelledError, Exception):
        pass
    state["running"] = False


def run():
    asyncio.run(main_async())


if __name__ == "__main__":
    run()
