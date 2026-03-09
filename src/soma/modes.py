"""
SOMA environment mode prescriptions.
Light (Tapo L530), Fan (0-5), AC (placeholder), Sound (placeholder).
"""

# Mode names
ENVIRONMENT_MODES = [
    "PEAK_FOCUS",
    "DEEP_FOCUS",
    "GENTLE_FOCUS",
    "RECOVERY_MODE",
    "WORKOUT_MODE",
    "MEETING_MODE",
    "BREAK_MODE",
    "HEAVY_DAY_WIND_DOWN",
    "WIND_DOWN",
    "SLEEP_PREP",
    "SLEEP_SIGNAL",
    "SUNRISE_SIMULATION",
    "MORNING_ACTIVE",
    "POST_WORKOUT_RECOVERY",
    "TRANSITION",
]

# Full prescriptions: light (color_temp, brightness), fan (0-5), ac (°C), sound (mode name)
MODE_PRESCRIPTIONS = {
    "PEAK_FOCUS": {
        "light": {"color_temp": 5500, "brightness": 95},
        "fan": 0,
        "ac": 22,
        "sound": "40Hz binaural",
    },
    "DEEP_FOCUS": {
        "light": {"color_temp": 5200, "brightness": 88},
        "fan": 0,
        "ac": 22,
        "sound": "40Hz binaural",
    },
    "GENTLE_FOCUS": {
        "light": {"color_temp": 4500, "brightness": 75},
        "fan": 1,
        "ac": 22,
        "sound": "10Hz alpha",
    },
    "RECOVERY_MODE": {
        "light": {"color_temp": 3500, "brightness": 40},
        "fan": 1,
        "ac": 21,
        "sound": "432Hz solfeggio",
    },
    "WORKOUT_MODE": {
        "light": {"color_temp": 5500, "brightness": 100},
        "fan": 4,
        "ac": 20,
        "sound": "workout",
    },
    "MEETING_MODE": {
        "light": {"color_temp": 5000, "brightness": 80},
        "fan": 0,
        "ac": 22,
        "sound": "off",
    },
    "BREAK_MODE": {
        "light": {"color_temp": 3200, "brightness": 45},
        "fan": 1,
        "ac": 22,
        "sound": "432Hz solfeggio",
    },
    "HEAVY_DAY_WIND_DOWN": {
        "light": {"color_temp": 3000, "brightness": 35},
        "fan": 1,
        "ac": 20,
        "sound": "432Hz solfeggio",
    },
    "WIND_DOWN": {
        "light": {"color_temp": 2700, "brightness": 20},
        "fan": 0,
        "ac": 20,
        "sound": "174Hz grounding",
    },
    "SLEEP_PREP": {
        "light": {"color_temp": 2500, "brightness": 10},
        "fan": 0,
        "ac": 19,
        "sound": "174Hz grounding",
    },
    "SLEEP_SIGNAL": {
        "light": {"color_temp": 2500, "brightness": 0},  # off after blink
        "fan": 0,
        "ac": 18,
        "sound": "off",
    },
    "SUNRISE_SIMULATION": {
        "light": {"color_temp": 2500, "brightness": 5},
        "fan": 1,
        "ac": 20,
        "sound": "off",
    },
    "MORNING_ACTIVE": {
        "light": {"color_temp": 5500, "brightness": 90},
        "fan": 2,
        "ac": 22,
        "sound": "off",
    },
    "POST_WORKOUT_RECOVERY": {
        "light": {"color_temp": 4500, "brightness": 70},
        "fan": 2,
        "ac": 22,
        "sound": "off",
    },
    "TRANSITION": {
        "light": {"color_temp": 4000, "brightness": 60},
        "fan": 1,
        "ac": 22,
        "sound": "432Hz solfeggio",
    },
}

# Mood override → prescription (immediate override)
MOOD_PRESCRIPTIONS = {
    "stressed": {"light": {"color_temp": 3000, "brightness": 30}, "fan": 1, "ac": 23, "sound": "432Hz solfeggio"},
    "flat": {"light": {"color_temp": 5500, "brightness": 95}, "fan": 2, "ac": 22, "sound": "40Hz gamma"},
    "focused": {"light": {"color_temp": 5200, "brightness": 90}, "fan": 0, "ac": 22, "sound": "40Hz binaural"},
    "winding_down": {"light": {"color_temp": 2700, "brightness": 20}, "fan": 0, "ac": 19, "sound": "174Hz grounding"},
    "energised": {"light": {"color_temp": 5500, "brightness": 80}, "fan": 1, "ac": 22, "sound": "off"},
}
