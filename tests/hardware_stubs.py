"""Let the flight modules import on a laptop.

CircuitPython supplies `board`, `busio` and friends on the device itself. They
do not exist in ordinary Python, so we put empty stand-ins in their place. Only
modules that never touch real hardware can be tested this way - anything that
actually calls into `busio` will fail, which is the point.
"""

import os
import sys
import types

FLIGHT_CODE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "src", "circuitpy_code"
)

if FLIGHT_CODE not in sys.path:
    sys.path.insert(0, FLIGHT_CODE)

for _name in (
    "board",
    "busio",
    "digitalio",
    "neopixel",
    "analogio",
    "microcontroller",
    "adafruit_gps",
    "adafruit_bmp280",
):
    if _name not in sys.modules:
        sys.modules[_name] = types.ModuleType(_name)
