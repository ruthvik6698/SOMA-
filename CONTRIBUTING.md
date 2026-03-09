# Contributing to SOMA

## Setup

```bash
git clone https://github.com/ruthvik6698/SOMA-.git
cd SOMA-
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e ".[dev]"
cp config/.env.example config/.env
# Edit config/.env with your credentials
```

## Running

- **Scheduler:** `soma-scheduler` or `./run_scheduler.sh`
- **Dashboard:** `soma-dashboard` or `./run_dashboard.sh`
- **Light:** `soma-light on|off|status` or `./run_light.sh`

## Tests

```bash
pytest tests/ -v
```

## Code layout

- `src/soma/` — main package; `config.py` holds paths and env
- `tests/` — pytest; `conftest.py` adds `src` to path
- `docs/FEATURES.md` — feature reference and API
