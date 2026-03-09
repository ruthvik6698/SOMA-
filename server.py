#!/usr/bin/env python3
"""
SOMA dashboard API server.
Serves WHOOP stats, light state, mood, and natural language commands.
"""
import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path

import pytz
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / "config" / ".env")

IST = pytz.timezone("Asia/Kolkata")

app = FastAPI(title="SOMA — Biometric Environment Controller")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared state (SOMA)
state = {
    "light": None,
    "today": None,
    "baselines": None,
    "history": [],
    "weather": None,
    "calendar_events": [],
    "mood_override": None,
    "mood_override_at": None,
    "plan": "",
    "last_prescription": None,
    "last_soma_mode": None,
    "paused": False,
    "light_state": None,
    "bedtime": None,
    "signal_sent": False,
}


def refresh_data():
    from src.whoop_api import get_today, get_history
    from src.baselines import compute_baselines
    from src.data import save_history, load_history

    try:
        state["today"] = get_today()
        records = get_history(90)
        save_history(records)
        state["history"] = load_history()
    except Exception as e:
        print(f"WHOOP fetch failed: {e}")
        state["history"] = state.get("history") or []
        state["today"] = state.get("today") or {}
    state["baselines"] = compute_baselines(state.get("history") or [])


def _get_weather():
    from src.weather import get_weather
    return get_weather()


def _get_context_block() -> str:
    today = state.get("today") or {}
    baselines = state.get("baselines") or {}
    t = datetime.now(IST)
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


SYSTEM_PROMPT = '''You are SOMA, an intelligent biometric environment controller.
You control lights based on WHOOP data. Direct, science-literate. One sentence when asked why.

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
{{"action": "sequence", "steps": [...], "delay_seconds": 3}}
```
None: ```json
{{"action": "none"}}
```

HARD RULE: After 22:00 → max 2500K. No exceptions.
RESPONSE: 1-3 sentences max.
'''


async def _fetch_light_state():
    dev = state.get("light")
    if not dev:
        return state.get("light_state")
    try:
        await dev.update()
        light_mod = dev.modules.get("Light") or dev.modules.get("kasa.Module.Light")
        if not light_mod:
            return state.get("light_state")
        is_on = dev.is_on
        brightness = getattr(light_mod, "brightness", None) or 0
        color_temp = getattr(light_mod, "color_temp", None) or 4000
        hsv_val = getattr(light_mod, "hsv", None)
        if is_on and light_mod:
            if hasattr(hsv_val, "hue"):
                hsv = [hsv_val.hue, hsv_val.saturation, hsv_val.value]
            elif isinstance(hsv_val, (tuple, list)):
                hsv = list(hsv_val)
            else:
                hsv = [0, 0, 0]
        else:
            hsv = [0, 0, 0]
            if not is_on:
                brightness = 0
        state["light_state"] = {
            "is_on": is_on,
            "brightness": brightness,
            "color_temp": color_temp,
            "hsv": hsv,
        }
        return state["light_state"]
    except Exception:
        return state.get("light_state")


@app.on_event("startup")
async def startup():
    from src.auth import ensure_authenticated
    from src.light import connect_light
    from src.calendar import get_today_events

    try:
        ensure_authenticated()
    except Exception as e:
        print(f"WHOOP auth failed: {e} — dashboard will show limited data")
    try:
        refresh_data()
    except Exception as e:
        print(f"Data refresh failed: {e}")
        from src.data import load_history
        state["history"] = load_history()
        state["today"] = state.get("today") or {}
        from src.baselines import compute_baselines
        state["baselines"] = compute_baselines(state["history"])
    state["weather"] = _get_weather()
    state["calendar_events"] = get_today_events()

    if all([os.getenv("TAPO_IP") or os.getenv("TAPO_DEVICE_IP"), os.getenv("TAPO_EMAIL"), os.getenv("TAPO_PASSWORD")]):
        try:
            state["light"] = await connect_light()
            await _fetch_light_state()
        except Exception as e:
            print(f"Light connection failed: {e}")


@app.get("/api/state")
async def get_state():
    state["weather"] = _get_weather()
    light_state = await _fetch_light_state() if state.get("light") else state.get("light_state")

    today = state.get("today") or {}
    baselines = state.get("baselines") or {}
    t = datetime.now(IST)

    return {
        "today": today,
        "baselines": baselines,
        "history": (state.get("history") or [])[:14],
        "weather": state.get("weather") or {},
        "plan": state.get("plan", ""),
        "last_prescription": state.get("last_prescription"),
        "last_soma_mode": state.get("last_soma_mode"),
        "mood_override": state.get("mood_override"),
        "paused": state.get("paused", False),
        "light_state": light_state,
        "time_ist": t.strftime("%H:%M"),
        "time_ist_full": t.strftime("%I:%M %p"),
        "date": t.strftime("%Y-%m-%d"),
        "profile": _get_profile(),
        "schedule": _get_schedule(),
        "alarm": _get_alarm_info_extended(t),
        "recent_jobs": _get_recent_jobs(),
        "connections": _get_connections(),
        "bedtime_decision": _get_bedtime_decision(),
        "scheduler_mode": _get_scheduler_mode(t),
    }


def _get_profile():
    try:
        from src.whoop_api import get_profile
        p = get_profile()
        return {"name": f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()}
    except Exception:
        return {"name": ""}


def _get_schedule():
    return [
        {"time": "05:30", "time_ist": "05:30", "job": "Sunrise start", "desc": "2500K, 5% — SOMA wake begins", "type": "wake"},
        {"time": "05:43", "time_ist": "05:43", "job": "Sunrise ramp", "desc": "Recovery-adjusted peak", "type": "wake"},
        {"time": "05:45", "time_ist": "05:45", "job": "Alarm pulse", "desc": "3 flashes, hold at wake level", "type": "alarm"},
        {"time": "06:00", "time_ist": "06:00", "job": "SOMA hourly", "desc": "READ → SCORE → PRESCRIBE → ACT", "type": "hourly"},
        {"time": "20:00", "time_ist": "20:00", "job": "Evening start", "desc": "First wind-down", "type": "winddown"},
        {"time": "21:00", "time_ist": "21:00", "job": "Evening check", "desc": "Tighten wind-down", "type": "winddown"},
        {"time": "22:00", "time_ist": "22:00", "job": "Deep wind-down", "desc": "2500K, 10% — hard floor", "type": "winddown"},
        {"time": "22:30", "time_ist": "22:30", "job": "Bedtime decision", "desc": "SOMA recommends sleep time", "type": "bedtime"},
        {"time": "23:00", "time_ist": "23:00", "job": "Bedtime check", "desc": "Blink signal if past bedtime", "type": "bedtime"},
    ]


def _get_connections():
    whoop_ok = False
    try:
        from src.whoop_api import get_profile
        get_profile()
        whoop_ok = True
    except Exception:
        pass
    light_ok = state.get("light") is not None
    return {"whoop": whoop_ok, "light": light_ok}


def _get_bedtime_decision():
    bt = state.get("bedtime")
    if bt:
        return {
            "recommended": bt.get("recommended_bedtime", "22:45"),
            "latest": bt.get("latest_bedtime", "23:30"),
            "reasoning": bt.get("reasoning", ""),
            "sleep_pressure": bt.get("sleep_pressure", "medium"),
        }
    return {
        "recommended": "22:45",
        "latest": "23:30",
        "reasoning": "Run scheduler at 22:30 for SOMA bedtime decision.",
        "sleep_pressure": "medium",
    }


def _get_scheduler_mode(t):
    h, m = t.hour, t.minute
    mins = h * 60 + m
    if 20 * 60 <= mins < 22 * 60:
        return "SLEEP_PREP"
    if mins >= 22 * 60 or mins < 5 * 60 + 30:
        return "SLEEPING"
    if 5 * 60 + 30 <= mins < 5 * 60 + 45:
        return "SUNRISE"
    return "AWAKE"


def _get_alarm_info():
    return {
        "time": "05:45 IST",
        "description": "3 bright flashes then hold at wake level (recovery-adjusted)",
        "hold_by_recovery": {
            "GREEN": "6000K, 100%",
            "YELLOW": "5500K, 90%",
            "RED": "4500K, 75%",
        },
    }


def _get_alarm_info_extended(t):
    base = _get_alarm_info()
    h, m = t.hour, t.minute
    now_mins = h * 60 + m
    alarm_mins = 5 * 60 + 45

    if 5 * 60 + 30 <= now_mins < 5 * 60 + 45:
        base["active_phase"] = "sunrise"
        base["countdown_minutes"] = alarm_mins - now_mins
    elif now_mins >= 5 * 60 + 45 and now_mins < 6 * 60:
        base["active_phase"] = "alarm_just_fired"
        base["countdown_minutes"] = 0
    else:
        base["active_phase"] = None
        if now_mins < 5 * 60 + 30:
            base["countdown_minutes"] = alarm_mins - now_mins
        else:
            base["countdown_minutes"] = (24 * 60 - now_mins) + alarm_mins
    return base


def _get_recent_jobs():
    log_path = PROJECT_ROOT / "logs" / "scheduler.log"
    soma_path = PROJECT_ROOT / "logs" / "soma.log"
    entries = []
    for p in [soma_path, log_path]:
        if not p.exists():
            continue
        try:
            with open(p) as f:
                lines = f.readlines()
            for line in reversed(lines[-30:]):
                line = line.strip()
                if not line:
                    continue
                if " IST] " in line:
                    idx = line.find(" IST] ")
                    if idx > 0:
                        ts = line[1:idx].strip()
                        msg = line[idx + 6:].strip()
                        entries.append({"time": ts, "message": msg})
                else:
                    try:
                        j = json.loads(line)
                        ts = j.get("timestamp", "")[:16].replace("T", " ")
                        mode = j.get("mode", "?")
                        rx = j.get("prescription", {}).get("light", {})
                        k = rx.get("color_temp")
                        b = rx.get("brightness")
                        msg = f"SOMA {mode}" + (f" → {k}K, {b}%" if k and b else "")
                        entries.append({"time": ts, "message": msg})
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
    entries.sort(key=lambda x: x.get("time", ""), reverse=True)
    return entries[:15]


@app.post("/api/refresh")
async def refresh():
    refresh_data()
    state["weather"] = _get_weather()
    try:
        from src.soma import run_decision_loop
        state["weather"] = _get_weather()
        run_decision_loop(state)
        state["plan"] = f"SOMA: {state.get('last_soma_mode', '?')}"
    except Exception:
        pass
    t = datetime.now(IST)
    if t.hour >= 20 or t.hour < 6:
        try:
            from src.decider import decide_bedtime
            state["bedtime"] = decide_bedtime(state)
        except Exception:
            pass
    return {"ok": True}


class MoodRequest(BaseModel):
    mood: str


@app.post("/api/mood")
async def set_mood(req: MoodRequest):
    """Set mood override: stressed | flat | focused | winding_down | energised"""
    from src.mood import set_mood_override
    if set_mood_override(state, req.mood):
        return {"ok": True, "mood": state.get("mood_override")}
    raise HTTPException(status_code=400, detail="Invalid mood. Use: stressed, flat, focused, winding_down, energised")


class LightSetRequest(BaseModel):
    color_temp: int
    brightness: int


@app.post("/api/light/set")
async def light_set(req: LightSetRequest):
    if not state.get("light"):
        raise HTTPException(status_code=503, detail="Light not connected")
    from src.light import set_light
    device = state["light"]
    k = max(2500, min(6500, req.color_temp))
    b = max(5, min(100, req.brightness))
    await set_light(device, color_temp=k, brightness=b)
    state["last_prescription"] = {"color_temp": k, "brightness": b}
    await asyncio.sleep(0.3)
    await _fetch_light_state()
    return {"ok": True}


@app.post("/api/light/on")
async def light_on():
    if not state.get("light"):
        raise HTTPException(status_code=503, detail="Light not connected")
    from src.light import set_light
    device = state["light"]
    rx = state.get("last_prescription") or {"color_temp": 4000, "brightness": 70}
    await set_light(device, color_temp=rx["color_temp"], brightness=rx["brightness"])
    await asyncio.sleep(0.3)
    await _fetch_light_state()
    return {"ok": True}


@app.post("/api/light/off")
async def light_off():
    if not state.get("light"):
        raise HTTPException(status_code=503, detail="Light not connected")
    from src.light import turn_off
    await turn_off(state["light"])
    state["last_prescription"] = None
    await asyncio.sleep(0.3)
    await _fetch_light_state()
    return {"ok": True}


@app.post("/api/bedtime-signal")
async def bedtime_signal():
    if not state.get("light"):
        raise HTTPException(status_code=503, detail="Light not connected")
    from src.sleep_prep import bedtime_signal as do_bedtime_signal
    await do_bedtime_signal(state)
    return {"ok": True}


class CommandRequest(BaseModel):
    message: str


@app.post("/api/command")
async def run_command(req: CommandRequest):
    from openai import OpenAI

    if not state.get("light"):
        raise HTTPException(status_code=503, detail="Light not connected")

    context = _get_context_block()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context_block=context)},
        {"role": "user", "content": req.message},
    ]

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(model="gpt-4o", messages=messages)
    reply = resp.choices[0].message.content or ""

    cmd = _parse_json_from_reply(reply)
    if cmd:
        from src.light import set_light, turn_off

        device = state["light"]
        action = cmd.get("action", "none")
        if action == "turn_off":
            await turn_off(device)
            state["last_prescription"] = None
        elif action == "sequence":
            steps = cmd.get("steps", [])
            delay = max(0.5, min(60, float(cmd.get("delay_seconds", 3))))
            for i, step in enumerate(steps):
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
        elif action == "set_light":
            await set_light(
                device,
                color_temp=cmd.get("color_temp"),
                hue=cmd.get("hue"),
                saturation=cmd.get("saturation"),
                brightness=cmd.get("brightness", 50),
            )
            state["last_prescription"] = {
                "color_temp": cmd.get("color_temp"),
                "brightness": cmd.get("brightness"),
            }

    await asyncio.sleep(0.4)
    await _fetch_light_state()

    text_reply = re.sub(r"\s*```(?:json)?\s*\{[\s\S]*?\}\s*```\s*$", "", reply).strip()
    return {"reply": text_reply, "command_executed": cmd is not None}


FRONTEND_DIR = PROJECT_ROOT / "frontend"
if (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/")
async def serve_index():
    if (FRONTEND_DIR / "index.html").exists():
        return FileResponse(FRONTEND_DIR / "index.html")
    return {"message": "SOMA API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
