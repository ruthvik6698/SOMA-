#!/usr/bin/env bash
# Run SOMA dashboard (web UI)
cd "$(dirname "$0")/.."
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
