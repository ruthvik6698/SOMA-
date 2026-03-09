"""
Mood input for SOMA: voice, text, quick-tap buttons.
Mood overrides all scheduled settings; expires after 90 minutes.
"""
import time

VALID_MOODS = frozenset({"stressed", "flat", "focused", "winding_down", "energised"})


def set_mood_override(state: dict, mood: str) -> bool:
    """
    Set mood override. Returns True if valid.
    mood: stressed | flat | focused | winding_down | energised
    """
    mood = (mood or "").strip().lower().replace(" ", "_")
    if mood in VALID_MOODS:
        state["mood_override"] = mood
        state["mood_override_at"] = time.time()
        return True
    # Aliases
    aliases = {
        "winding down": "winding_down",
        "low energy": "flat",
        "need to focus": "focused",
        "focus": "focused",
    }
    if mood in aliases:
        state["mood_override"] = aliases[mood]
        state["mood_override_at"] = time.time()
        return True
    return False


def clear_mood_override(state: dict):
    """Clear mood override."""
    state["mood_override"] = None
    state["mood_override_at"] = None


def infer_mood_from_hrv_dip(state: dict, history_hrv: list[float]) -> str | None:
    """
    If HRV drops >15% mid-day with no calendar event, infer stress.
    Returns "stressed" or None.
    """
    today = state.get("today") or {}
    baselines = state.get("baselines") or {}
    hrv = today.get("hrv")
    hrv_mean = baselines.get("hrv_mean")
    if hrv is None or hrv_mean is None:
        return None
    if hrv < hrv_mean * 0.85:
        # Mid-day: 10:00–19:00
        from datetime import datetime
        import pytz
        now = datetime.now(pytz.timezone("Asia/Kolkata"))
        if 10 <= now.hour < 19:
            return "stressed"
    return None
