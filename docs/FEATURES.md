# SOMA — Feature Reference

Full documentation for the biometric environment controller.

---

## Project Structure

```
whoop/
├── config/
│   ├── .env              # Your credentials (gitignored)
│   └── .env.example      # Template
├── data/
│   └── whoop_history.json # Cached WHOOP cycles (90 days)
├── docs/
│   └── FEATURES.md       # This file
├── frontend/
│   ├── index.html
│   └── assets/
├── logs/                  # scheduler.log, soma.log (gitignored)
├── scripts/
│   ├── run_scheduler.sh
│   ├── run_dashboard.sh
│   └── run_light.sh
├── src/
│   ├── soma/             # Decision engine
│   ├── auth.py, baselines.py, calendar.py, data.py
│   ├── decider.py, devices.py, light.py, light_control.py
│   ├── mood.py, sleep_prep.py, wake.py, weather.py, whoop_api.py
├── scheduler.py
├── server.py
├── test_light.py
├── requirements.txt
└── LICENSE
```

---

## Run Commands

| Command | What it does |
|---------|--------------|
| `./run_scheduler.sh` | SOMA automation + interactive CLI |
| `./run_dashboard.sh` | Web UI at http://localhost:8000 |
| `./run_light.sh on \| off \| status` | Direct light (hardware test) |
| `python3 test_light.py` | Verify Tapo connection |

---

## SOMA Decision Loop

1. **READ** — WHOOP, calendar, weather, mood, time
2. **SCORE** — Recovery vs baseline, HRV vs 30-day mean, strain
3. **PRESCRIBE** — Mode from decision table, weather modifier, mood override
4. **ACT** — Push to light (and fan when available)

**Hard rules:** After 22:00 → max 2500K. Red recovery + HRV below → RECOVERY_MODE. Mood expires in 90 min.

---

## Environment Modes

| Mode | When |
|------|------|
| PEAK_FOCUS | Green recovery, HRV above baseline |
| DEEP_FOCUS | Standard focus |
| GENTLE_FOCUS | HRV dip |
| RECOVERY_MODE | Red recovery |
| WORKOUT_MODE | 7:30–9:30 |
| MEETING_MODE | Calendar meeting |
| WIND_DOWN | 20:00+ |
| SLEEP_PREP | 22:00+ |
| SUNRISE_SIMULATION | 5:30–5:45 |

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/state` | GET | Full state |
| `/api/refresh` | POST | Refresh WHOOP, run SOMA |
| `/api/mood` | POST | Set mood override |
| `/api/command` | POST | Natural language → AI → light |
| `/api/light/set` | POST | `{color_temp, brightness}` |
| `/api/bedtime-signal` | POST | 10-blink sequence |

---

## Configuration

Copy `config/.env.example` to `config/.env`. See README for setup.
