"""Tests for SOMA decision engine."""
import pytest

from soma import score_inputs, select_mode, get_mode_prescription, infer_calendar_mode


def test_score_inputs():
    """Score inputs returns expected tiers."""
    today = {"recovery_score": 74, "hrv": 68, "day_strain": 4.2}
    baselines = {"hrv_mean": 62, "hrv_std": 15, "recovery_mean": 68, "avg_strain": 10, "sleep_mean": 7}
    scores = score_inputs(today, baselines)
    assert scores["recovery_tier"] in ("HIGH", "NORMAL", "LOW")
    assert scores["hrv_tier"] in ("ABOVE", "AT", "BELOW")
    assert scores["strain_tier"] in ("LIGHT", "NORMAL", "HEAVY")


def test_infer_calendar_mode():
    """Calendar mode inferred from time."""
    assert infer_calendar_mode([], 7, 45) == "WORKOUT_MODE"
    assert infer_calendar_mode([], 10, 30) == "DEEP_FOCUS"
    assert infer_calendar_mode([], 20, 30) == "WIND_DOWN"
    assert infer_calendar_mode([], 22, 15) == "SLEEP_PREP"


def test_get_mode_prescription():
    """Mode prescription returns light/fan/ac/sound."""
    rx = get_mode_prescription("DEEP_FOCUS", None)
    assert "light" in rx
    assert rx["light"]["color_temp"] == 5200
    assert rx["light"]["brightness"] == 88
    assert rx["fan"] == 0
