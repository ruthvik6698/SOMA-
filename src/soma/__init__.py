"""
SOMA — Intelligent biometric environment controller.
Decision loop: READ → SCORE → PRESCRIBE → ACT.
"""

from .core import (
    run_decision_loop,
    score_inputs,
    select_mode,
    get_mode_prescription,
    infer_calendar_mode,
)
from .modes import MODE_PRESCRIPTIONS, ENVIRONMENT_MODES

__all__ = [
    "run_decision_loop",
    "score_inputs",
    "select_mode",
    "get_mode_prescription",
    "infer_calendar_mode",
    "MODE_PRESCRIPTIONS",
    "ENVIRONMENT_MODES",
]
