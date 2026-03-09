#!/usr/bin/env python3
"""
Tapo L530 Light Control - CLI for hardware testing only.
NOT used in production. SOMA uses src/light.py + scheduler/server.
Commands: on, off, status, brightness N, colortemp N, hsv, scene.
"""
import argparse
import asyncio

from kasa import Module

from .light import connect_light, disconnect_light


async def _get_device():
    return await connect_light()


# --- Commands ---

async def cmd_on(dev):
    await dev.turn_on()
    print("Light: ON")


async def cmd_off(dev):
    await dev.turn_off()
    print("Light: OFF")


async def cmd_status(dev):
    state = "ON" if dev.is_on else "OFF"
    print(f"Light: {state} | Alias: {dev.alias} | Model: {dev.model}")
    if dev.is_on and Module.Light in dev.modules:
        light = dev.modules[Module.Light]
        if hasattr(light, "brightness"):
            print(f"  Brightness: {light.brightness}%")


async def cmd_brightness(dev, value: int):
    light = dev.modules[Module.Light]
    await light.set_brightness(value)
    await dev.update()
    print(f"Brightness set to {value}%")


async def cmd_color_temp(dev, value: int):
    light = dev.modules[Module.Light]
    await light.set_color_temp(value)
    await dev.update()
    print(f"Color temp set to {value}K (2500=warm, 6500=cool)")


async def cmd_hsv(dev, hue: int, saturation: int, value: int):
    light = dev.modules[Module.Light]
    await light.set_hsv(hue, saturation, value)
    await dev.update()
    print(f"Color set: HSV({hue}, {saturation}%, {value}%)")


async def cmd_scene(dev, scene: str):
    """Preset scenes: warm, cool, reading, party, relax"""
    scenes = {
        "warm": (0, 0, 100, 2700),      # warm white
        "cool": (0, 0, 100, 6500),      # cool white
        "reading": (40, 10, 90, 4000),  # soft warm
        "party": (280, 100, 100, None),  # purple
        "relax": (30, 40, 60, None),    # soft amber
    }
    if scene not in scenes:
        print(f"Unknown scene. Available: {', '.join(scenes)}")
        return
    h, s, v, ct = scenes[scene]
    light = dev.modules[Module.Light]
    if ct is not None:
        await light.set_color_temp(ct)
        await light.set_brightness(v)
    else:
        await light.set_hsv(h, s, v)
    await dev.update()
    print(f"Scene '{scene}' applied")


async def run_command(cmd_fn, *args, **kwargs):
    dev = await _get_device()
    try:
        if args or kwargs:
            await cmd_fn(dev, *args, **kwargs)
        else:
            await cmd_fn(dev)
    finally:
        await disconnect_light(dev)


def main():
    parser = argparse.ArgumentParser(description="Control Tapo L530 light")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("on", help="Turn light on")
    sub.add_parser("off", help="Turn light off")
    sub.add_parser("status", help="Show current state")

    b = sub.add_parser("brightness", help="Set brightness 0-100")
    b.add_argument("value", type=int, choices=range(0, 101), metavar="0-100")

    c = sub.add_parser("colortemp", help="Set color temp 2500-6500K")
    c.add_argument("value", type=int, choices=range(2500, 6501), metavar="2500-6500")

    h = sub.add_parser("hsv", help="Set HSV color")
    h.add_argument("hue", type=int, choices=range(0, 361), metavar="0-360")
    h.add_argument("saturation", type=int, choices=range(0, 101), metavar="0-100")
    h.add_argument("value", type=int, choices=range(0, 101), metavar="0-100")

    s = sub.add_parser("scene", help="Apply preset scene")
    s.add_argument("name", choices=["warm", "cool", "reading", "party", "relax"])

    args = parser.parse_args()

    if args.command == "on":
        asyncio.run(run_command(cmd_on))
    elif args.command == "off":
        asyncio.run(run_command(cmd_off))
    elif args.command == "status":
        asyncio.run(run_command(cmd_status))
    elif args.command == "brightness":
        asyncio.run(run_command(cmd_brightness, args.value))
    elif args.command == "colortemp":
        asyncio.run(run_command(cmd_color_temp, args.value))
    elif args.command == "hsv":
        asyncio.run(run_command(cmd_hsv, args.hue, args.saturation, args.value))
    elif args.command == "scene":
        asyncio.run(run_command(cmd_scene, args.name))


if __name__ == "__main__":
    main()
