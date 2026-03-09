"""
Device layer: light (Tapo), fan (placeholder), AC (planned), speaker (planned).
"""
from typing import Any


async def set_fan_speed(device: Any | None, level: int) -> bool:
    """
    Set fan speed 0–5.
    Placeholder: no-op until Tapo or similar fan API is integrated.
    """
    if device is None:
        return False
    # TODO: Tapo fan API
    return True


def connect_fan() -> Any | None:
    """Connect to smart fan. Placeholder: returns None."""
    return None
