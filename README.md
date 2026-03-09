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

## Quick Start

```bash
# Clone and setup
git clone https://github.com/YOUR_USERNAME/whoop.git
cd whoop

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure (copy template, fill credentials)
cp config/.env.example config/.env
# Edit config/.env with TAPO_*, WHOOP_*, OPENAI_API_KEY

# Run scheduler (automation + CLI)
./run_scheduler.sh
# or: ./scripts/run_scheduler.sh

# Or run dashboard (web UI)
./run_dashboard.sh
# → http://localhost:8000
```

---

## Project Structure

```
whoop/
├── config/          # .env.example (template)
├── data/            # WHOOP history cache (gitignored)
├── docs/            # FEATURES.md
├── frontend/        # Dashboard UI
├── scripts/         # run_scheduler, run_dashboard, run_light
├── src/
│   ├── soma/        # Decision engine (core, modes)
│   ├── auth.py      # WHOOP OAuth
│   ├── whoop_api.py # WHOOP v2 client
│   ├── light.py     # Tapo control
│   └── ...
├── scheduler.py     # Main automation entry
├── server.py        # FastAPI backend
└── requirements.txt
```

---

## Configuration

| Variable | Purpose |
|----------|---------|
| `TAPO_IP`, `TAPO_EMAIL`, `TAPO_PASSWORD` | TP-Link Tapo bulb |
| `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET` | [developer.whoop.com](https://developer.whoop.com) |
| `OPENAI_API_KEY` | Natural language commands |
| `WEATHER_API_KEY`, `WEATHER_LOCATION` | [weatherapi.com](https://weatherapi.com) (optional) |

OAuth runs automatically on first run if WHOOP tokens are missing.

---

## Scripts

| Script | Description |
|--------|-------------|
| `./run_scheduler.sh` | SOMA automation, sunrise, wind-down, interactive CLI |
| `./run_dashboard.sh` | Web dashboard (port 8000) |
| `./run_light.sh on \| off \| status \| brightness 80` | Direct light control (no WHOOP) |
| `python3 test_light.py` | Verify Tapo connection |

---

## Schedule (IST)

| Time | Job |
|------|-----|
| 05:30–05:45 | Sunrise simulation (recovery-adjusted) |
| 05:45 | Alarm pulse |
| Hourly | SOMA decision loop |
| 20:00–22:00 | Wind-down |
| 22:00 | Hard floor (2500K, 10%) |
| 22:30 | Bedtime recommendation |
| 23:00+ | Bedtime signal (blink) |

---

## License

MIT — see [LICENSE](LICENSE)

---

## Documentation

- [docs/FEATURES.md](docs/FEATURES.md) — Full feature reference, API, modes
