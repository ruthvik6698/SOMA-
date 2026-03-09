"""
Centralized configuration. Loads from config/.env.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Project root (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / "config" / ".env"

# Load once at import
load_dotenv(ENV_PATH)

# Paths
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
HISTORY_FILE = DATA_DIR / "whoop_history.json"
SCHEDULER_LOG = LOGS_DIR / "scheduler.log"
SOMA_LOG = LOGS_DIR / "soma.log"


def get(key: str, default: str | None = None) -> str | None:
    """Get config value by key."""
    return os.getenv(key, default)


def require(*keys: str) -> dict[str, str]:
    """Get required config values. Raises if any missing."""
    values = {}
    missing = []
    for k in keys:
        v = os.getenv(k)
        if not v:
            missing.append(k)
        else:
            values[k] = v
    if missing:
        raise ValueError(f"Missing config: {', '.join(missing)}. Set in config/.env")
    return values
