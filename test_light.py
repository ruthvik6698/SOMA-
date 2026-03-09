#!/usr/bin/env python3
"""
Test script to verify Tapo L530 light connection and control.
Run: python3 test_light.py
"""
import asyncio

from soma.config import get

TAPO_IP = get("TAPO_IP") or get("TAPO_DEVICE_IP")
TAPO_EMAIL = get("TAPO_EMAIL")
TAPO_PASSWORD = get("TAPO_PASSWORD")


async def test_connection():
    """Test different connection methods and verify light responds."""
    if not all([TAPO_IP, TAPO_EMAIL, TAPO_PASSWORD]):
        print("Missing TAPO_IP, TAPO_EMAIL, or TAPO_PASSWORD in config/.env")
        return

    print(f"Testing connection to {TAPO_IP}...")
    print()

    # Method 1: try_connect_all (tries all protocols, works when UDP discovery fails)
    from kasa import Discover, Credentials

    creds = Credentials(username=TAPO_EMAIL or "", password=TAPO_PASSWORD or "")

    print("1. Trying Discover.try_connect_all (bypasses UDP discovery)...")
    try:
        dev = await Discover.try_connect_all(TAPO_IP or "", credentials=creds, timeout=10)
        if dev:
            print("   SUCCESS: Connected via try_connect_all")
            await dev.update()
            print(f"   Device: {dev.model} @ {dev.host}")
            print(f"   Is on: {dev.is_on}")
            if hasattr(dev, "modules") and dev.modules:
                light = dev.modules.get("Light")
                if light:
                    print(f"   Light module: {light}")
            # Quick test: turn on, set brightness, turn off
            print("\n   Testing commands...")
            await dev.turn_on()
            await asyncio.sleep(1)
            light_mod = dev.modules.get("Light") or dev.modules.get("kasa.Module.Light")
            if light_mod:
                await light_mod.set_brightness(50)
                await light_mod.set_color_temp(4000)
                await asyncio.sleep(2)
            await dev.turn_off()
            await asyncio.sleep(1)
            print("   Commands executed. Did the light change?")
            await dev.disconnect()
        else:
            print("   FAILED: try_connect_all returned None")
    except Exception as e:
        print(f"   FAILED: {e}")

    print()

    # Method 2: discover_single
    print("2. Trying Discover.discover_single...")
    try:
        dev = await Discover.discover_single(
            TAPO_IP or "", username=TAPO_EMAIL or "", password=TAPO_PASSWORD or "", discovery_timeout=10
        )
        if dev:
            print("   SUCCESS: Connected via discover_single")
            await dev.update()
            print(f"   Device: {dev.model} @ {dev.host}")
            await dev.disconnect()
        else:
            print("   FAILED: discover_single returned None")
    except Exception as e:
        print(f"   FAILED: {e}")

    print()
    print("Done. If both failed, check: IP correct, bulb powered, same network, credentials valid.")


if __name__ == "__main__":
    asyncio.run(test_connection())
