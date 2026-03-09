#!/usr/bin/env bash
# Direct light control (hardware testing, no WHOOP)
cd "$(dirname "$0")/.."
python3 -m soma.light_control "$@"
