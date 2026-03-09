# SOMA — Biometric Environment Controller

> An intelligent environment controller that reads WHOOP biometrics hourly and orchestrates smart lights to match what your body needs at that moment.

**SOMA** (System for Optimal Metabolic Adaptation) is a personal automation system that combines wearable physiology data, circadian science, and smart home control. It runs a continuous decision loop: **READ** → **SCORE** → **PRESCRIBE** → **ACT**.

---

## Features

- **WHOOP integration** — Recovery, HRV, sleep, strain drive environment decisions
- **Personal baselines** — Compares to your 30-day averages, not population norms
- **Circadian-aware** — Sunrise simulation, wind-down sequences, melatonin protection (hard 2500K cap after 22:00)
- **Mood overrides** — Quick-tap: Stressed / Flat / Focus / Wind Down (90-min override)
- **Natural language** — "Make it warmer", "bedtime mode" via OpenAI
- **Web dashboard** — Metrics, light control, schedule, bedtime recommendations

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

Copy the template and add your credentials:

```bash
cp config/.env.example config/.env
# Edit config/.env with your values
```

| Variable | Purpose |
|----------|---------|
| `TAPO_IP`, `TAPO_EMAIL`, `TAPO_PASSWORD` | TP-Link Tapo bulb |
| `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET` | [developer.whoop.com](https://developer.whoop.com) |
| `OPENAI_API_KEY` | Natural language commands |
| `WEATHER_API_KEY`, `WEATHER_LOCATION` | [weatherapi.com](https://weatherapi.com) (optional) |

OAuth runs automatically on first run if WHOOP tokens are missing.

---

## Usage

### Option 1: CLI commands (after `pip install -e .`)

```bash
soma-scheduler    # Automation + interactive CLI
soma-dashboard    # Web UI at http://localhost:8000
soma-light on     # Direct light control (no WHOOP)
soma-light status
```

### Option 2: Scripts

```bash
./run_scheduler.sh   # or ./scripts/run_scheduler.sh
./run_dashboard.sh
./run_light.sh on
```

### Option 3: Python module

```bash
python -m soma.scheduler
python -m uvicorn soma.server:app --host 0.0.0.0 --port 8000
python -m soma.light_control status
```

---

## Project Structure

```
SOMA-/
├── config/           # .env.example
├── data/             # WHOOP history cache (gitignored)
├── docs/             # FEATURES.md
├── frontend/         # Dashboard UI
├── scripts/         # run_scheduler, run_dashboard, run_light
├── src/
│   └── soma/         # Main package
│       ├── config.py
│       ├── core.py, modes.py
│       ├── auth.py, whoop_api.py, baselines.py, data.py
│       ├── light.py, devices.py, weather.py, calendar.py
│       ├── decider.py, sleep_prep.py, wake.py, mood.py
│       ├── scheduler.py, server.py, light_control.py
├── tests/
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SOMA Decision Loop                        │
│  READ (WHOOP, calendar, weather, mood) → SCORE (vs baselines)   │
│  → PRESCRIBE (mode from table) → ACT (light, fan placeholder)   │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
   ┌──────────┐        ┌──────────────┐      ┌─────────────┐
   │  WHOOP   │        │  Tapo L530   │      │  FastAPI    │
   │  API     │        │  Smart Bulb  │      │  Dashboard  │
   └──────────┘        └──────────────┘      └─────────────┘
```

**Tech stack:** Python 3.10+, FastAPI, python-kasa (Tapo), OpenAI, WHOOP v2 API

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

## Documentation

- [docs/FEATURES.md](docs/FEATURES.md) — Full feature reference, API, modes
