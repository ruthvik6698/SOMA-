"""
Weather fetch via WeatherAPI.com. Cached for 10 minutes.
"""
import os
import time
import requests

from .config import get

_CACHE = {"data": None, "fetched_at": 0}
_CACHE_TTL = 600  # 10 minutes


def get_weather() -> dict:
    """
    Fetch current weather for location. Returns temp_c, condition, is_day.
    Cached for 10 minutes.
    """
    now = time.time()
    if _CACHE["data"] is not None and (now - _CACHE["fetched_at"]) < _CACHE_TTL:
        return _CACHE["data"]

    key = get("WEATHER_API_KEY")
    location = get("WEATHER_LOCATION") or "Hyderabad"
    if not key:
        return {"temp_c": None, "condition": "unknown", "is_day": 1}

    try:
        resp = requests.get(
            "https://api.weatherapi.com/v1/current.json",
            params={"key": key, "q": location},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current", {})
        result = {
            "temp_c": current.get("temp_c"),
            "condition": current.get("condition", {}).get("text", "unknown"),
            "is_day": current.get("is_day", 1),
        }
        _CACHE["data"] = result
        _CACHE["fetched_at"] = now
        return result
    except Exception:
        return {"temp_c": None, "condition": "unknown", "is_day": 1}
