# SOMA

**System for Optimal Metabolic Adaptation** — an environment controller that reads your biometrics and adjusts your lights to match what your body actually needs.

---

## Why I Built This

I wear a WHOOP. I have smart lights. But the two never talked.

Generic advice is useless. "Get more blue light in the morning" doesn't know that I slept 4 hours and my HRV is 20% below my baseline. "Wind down before bed" doesn't know I just crushed a 14-strain workout and need to actually decompress. Population norms don't apply to me — my 30-day average does.

So I built SOMA: a loop that **reads** my WHOOP, **scores** it against my personal baselines, **prescribes** an environment mode, and **acts** on my lights. No rules. No schedules. Just: *what does my body need right now?*

The result: lights that adapt to *me* — recovery days get warm and dim, peak days get cool and bright, and after 22:00 it never goes above 2500K because melatonin matters more than productivity.

---

## What It Does

SOMA runs hourly (or on demand). It:

1. **READ** — Pulls recovery, HRV, strain, sleep from WHOOP; checks calendar, weather, time
2. **SCORE** — Compares to *your* 30-day baselines (not population norms)
3. **PRESCRIBE** — Picks a mode from a decision table (PEAK_FOCUS, RECOVERY_MODE, WIND_DOWN, etc.)
4. **ACT** — Pushes color temp and brightness to your Tapo bulb

Mood overrides let you tap "Stressed" or "Focus" and get an immediate prescription. Natural language ("make it warmer", "bedtime mode") goes through OpenAI and adjusts the light. A web dashboard shows metrics, control, and bedtime recommendations.

---

## Features

| Feature | Description |
|---------|-------------|
| **WHOOP integration** | Recovery, HRV, sleep, strain drive every decision |
| **Personal baselines** | 30-day rolling averages — your body, your norms |
| **Circadian-aware** | Sunrise simulation (5:30), wind-down (20:00), melatonin protection (hard 2500K cap after 22:00) |
| **Mood overrides** | Stressed / Flat / Focus / Wind Down — 90-min override |
| **Natural language** | "Make it warmer", "bedtime mode" via OpenAI |
| **Web dashboard** | Metrics, light control, schedule, bedtime signal |

---

## Installation

```bash
git clone https://github.com/ruthvik6698/SOMA-.git
cd SOMA-

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -e .
```

---

## Configuration

```bash
cp config/.env.example config/.env
# Edit config/.env with your credentials
```

| Variable | Purpose |
|----------|---------|
| `TAPO_IP`, `TAPO_EMAIL`, `TAPO_PASSWORD` | TP-Link Tapo bulb (L530) |
| `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET` | [developer.whoop.com](https://developer.whoop.com) |
| `OPENAI_API_KEY` | Natural language commands |
| `WEATHER_API_KEY`, `WEATHER_LOCATION` | [weatherapi.com](https://weatherapi.com) (optional) |

WHOOP OAuth runs automatically on first run if tokens are missing.

---

## Usage

```bash
soma-scheduler    # Automation + interactive CLI (runs the loop)
soma-dashboard    # Web UI at http://localhost:8000
soma-light on     # Direct light control, no WHOOP (hardware test)
```

Or use the scripts: `./run_scheduler.sh`, `./run_dashboard.sh`, `./run_light.sh`

---

## How It Decides

| Mode | When |
|------|------|
| PEAK_FOCUS | Green recovery, HRV above baseline |
| DEEP_FOCUS | Standard focus |
| GENTLE_FOCUS | HRV dip |
| RECOVERY_MODE | Red recovery |
| WORKOUT_MODE | 7:30–9:30 slot |
| WIND_DOWN | 20:00+ |
| SLEEP_PREP | 22:00+ (max 2500K) |
| SUNRISE_SIMULATION | 5:30–5:45 |

Mood overrides (Stressed, Flat, Focus, Wind Down) take precedence for 90 minutes. After 22:00, color temp is capped at 2500K regardless of mode.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SOMA Decision Loop                        │
│  READ (WHOOP, calendar, weather, mood) → SCORE (vs baselines)   │
│  → PRESCRIBE (mode from table) → ACT (light)                     │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   ┌──────────┐        ┌──────────────┐      ┌─────────────┐
   │  WHOOP   │        │  Tapo L530   │      │  FastAPI    │
   │  API     │        │  Smart Bulb  │      │  Dashboard  │
   └──────────┘        └──────────────┘      └─────────────┘
```

**Stack:** Python 3.10+, FastAPI, python-kasa (Tapo), OpenAI, WHOOP v2 API

---

## Project Structure

```
├── config/           # .env
├── data/             # WHOOP history cache (gitignored)
├── docs/             # FEATURES.md
├── frontend/         # Dashboard UI
├── scripts/          # run_scheduler, run_dashboard, run_light
├── src/soma/         # Main package
│   ├── config.py     # Paths, env
│   ├── core.py       # READ → SCORE → PRESCRIBE → ACT
│   ├── modes.py      # Mode prescriptions (light, fan, etc.)
│   ├── decider.py    # Mode selection, bedtime logic
│   ├── whoop_api.py, baselines.py, data.py
│   ├── light.py, devices.py, weather.py, calendar.py
│   ├── sleep_prep.py, wake.py, mood.py
│   ├── scheduler.py, server.py, light_control.py
├── tests/
├── pyproject.toml
└── README.md
```

---

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## License

MIT — see [LICENSE](LICENSE)

---

## Docs

- [docs/FEATURES.md](docs/FEATURES.md) — Full feature reference, API, modes
