"""
Tapo L530 light control via python-kasa.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from kasa import Discover, Module


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / "config" / ".env")

TAPO_IP = os.getenv("TAPO_IP") or os.getenv("TAPO_DEVICE_IP")
TAPO_EMAIL = os.getenv("TAPO_EMAIL")
TAPO_PASSWORD = os.getenv("TAPO_PASSWORD")


async def connect_light():
    """Connect to Tapo L530. Returns device. Uses try_connect_all for reliability (bypasses UDP discovery)."""
    from kasa import Credentials
    creds = Credentials(username=TAPO_EMAIL, password=TAPO_PASSWORD)
    dev = await Discover.try_connect_all(TAPO_IP, credentials=creds, timeout=10)
    if not dev:
        raise ConnectionError(f"Could not connect to Tapo at {TAPO_IP}. Check IP, credentials, and network.")
    await dev.update()
    return dev


async def set_light(device, color_temp=None, hue=None, saturation=None, brightness=None):
    """Set light. Use color_temp OR hue+saturation, never both. Clamps to device limits."""
    light_mod = device.modules.get(Module.Light) or device.modules.get("Light")
    if not light_mod:
        return
    await device.turn_on()
    # Tapo L530: color_temp 2500–6500K, brightness 1–100
    if color_temp is not None:
        color_temp = max(2500, min(6500, int(color_temp)))
    if brightness is not None:
        brightness = max(1, min(100, int(brightness)))
    if hue is not None and saturation is not None:
        await light_mod.set_hsv(hue, saturation, brightness if brightness else 100)
    elif color_temp is not None:
        # Set color_temp and brightness in one call (recommended for Tapo; avoids race/overwrite)
        await light_mod.set_color_temp(color_temp, brightness=brightness)
    elif brightness is not None:
        await light_mod.set_brightness(brightness)
    await device.update()


async def turn_off(device):
    """Turn light off."""
    await device.turn_off()
    await device.update()


async def disconnect_light(device):
    """Disconnect from device."""
    await device.disconnect()
