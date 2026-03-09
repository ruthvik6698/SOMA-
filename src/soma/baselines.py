"""
Compute personal baselines from Whoop history.
"""
import statistics
from datetime import datetime, timedelta


def compute_baselines(history: list) -> dict:
    """
    Takes list of cycle dicts from whoop_history.json.
    Returns personal baseline dict.
    Falls back to population defaults if < 5 data points.
    """
    cutoff_30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    cutoff_7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    last_30 = [c for c in history if c.get("date", "") >= cutoff_30 and c.get("recovery_score") is not None]
    recent_7 = [c for c in history if c.get("date", "") >= cutoff_7]

    defaults = {
        "hrv_mean": 60, "hrv_std": 15, "rhr_mean": 58, "rhr_std": 5,
        "recovery_mean": 50, "avg_strain": 10, "sleep_mean": 7.0,
        "data_points": 0, "recovery_trend": "stable", "sleep_trend": "stable", "strain_trend": "stable",
    }

    if len(last_30) < 5:
        return defaults

    hrv_vals = [c["hrv"] for c in last_30 if c.get("hrv") is not None]
    rhr_vals = [c["resting_hr"] for c in last_30 if c.get("resting_hr") is not None]
    rec_vals = [c["recovery_score"] for c in last_30 if c.get("recovery_score") is not None]
    strain_vals = [c["day_strain"] for c in last_30 if c.get("day_strain") is not None]
    sleep_vals = [c["sleep_duration_hrs"] for c in last_30 if c.get("sleep_duration_hrs") is not None]

    baselines = {
        "hrv_mean": statistics.mean(hrv_vals) if hrv_vals else 60,
        "hrv_std": statistics.stdev(hrv_vals) if len(hrv_vals) > 1 else 15,
        "rhr_mean": statistics.mean(rhr_vals) if rhr_vals else 58,
        "rhr_std": statistics.stdev(rhr_vals) if len(rhr_vals) > 1 else 5,
        "recovery_mean": statistics.mean(rec_vals) if rec_vals else 50,
        "avg_strain": statistics.mean(strain_vals) if strain_vals else 10,
        "sleep_mean": statistics.mean(sleep_vals) if sleep_vals else 7.0,
        "data_points": len(last_30),
    }

    rec_7 = [c["recovery_score"] for c in recent_7 if c.get("recovery_score") is not None]
    sleep_7 = [c["sleep_duration_hrs"] for c in recent_7 if c.get("sleep_duration_hrs") is not None]
    strain_7 = [c["day_strain"] for c in recent_7 if c.get("day_strain") is not None]

    recent_rec = statistics.mean(rec_7) if rec_7 else baselines["recovery_mean"]
    recent_sleep = statistics.mean(sleep_7) if sleep_7 else baselines["sleep_mean"]
    recent_strain = statistics.mean(strain_7) if strain_7 else baselines["avg_strain"]

    def _trend(recent, baseline, higher_is_better=True):
        if not recent or baseline == 0:
            return "stable"
        pct = (recent - baseline) / baseline * 100 if baseline else 0
        if higher_is_better:
            return "improving" if pct > 5 else "declining" if pct < -5 else "stable"
        return "declining" if pct > 5 else "improving" if pct < -5 else "stable"

    baselines["recovery_trend"] = _trend(recent_rec, baselines["recovery_mean"])
    baselines["sleep_trend"] = _trend(recent_sleep, baselines["sleep_mean"])
    baselines["strain_trend"] = _trend(recent_strain, baselines["avg_strain"], higher_is_better=False)

    return baselines
