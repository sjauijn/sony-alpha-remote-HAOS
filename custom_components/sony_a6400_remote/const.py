"""Constants for the Sony Camera BLE Remote integration.

Protocol reverse-engineered by Coral (https://github.com/coral/freemote),
Greg Leeds (https://gregleeds.com/reverse-engineering-sony-camera-bluetooth/)
and Mark Kirschenbaum, and re-derived here from the alpharemote Android app
(https://github.com/Staacks/alpharemote), released under GPL-3.0.

IMPORTANT: This BLE protocol only emulates physical remote-control button
presses. There is NO command to change the camera's focus mode (AF-S / AF-C
/ DMF / MF) -- that is a hardware switch on the camera/lens and is not
exposed over Bluetooth. What IS available:
  - Shutter (half-press / full-press)
  - AF-On (the "hold to focus" button)
  - Record (video)
  - C1 (custom button)
  - Zoom in/out (jog, stepped)
  - Focus near/far (jog, stepped -- manual focus nudge, requires the
    camera/lens to already be in MF or DMF mode via the physical switch)
"""
from __future__ import annotations

DOMAIN = "sony_a6400_remote"

CONF_MAC = "mac"

# GATT UUIDs
SERVICE_UUID = "8000ff00-ff00-ffff-ffff-ffffffffffff"
COMMAND_CHAR_UUID = "0000ff01-0000-1000-8000-00805f9b34fb"
STATUS_CHAR_UUID = "0000ff02-0000-1000-8000-00805f9b34fb"

# -- Button codes (single byte, OR'd with 0x01 when pressed) ---------------
BTN_SHUTTER_HALF = 0x06
BTN_SHUTTER_FULL = 0x08
BTN_RECORD = 0x0E
BTN_AF_ON = 0x14
BTN_C1 = 0x20

# -- Jog codes (zoom / manual focus nudge) ----------------------------------
JOG_ZOOM_IN = 0x44
JOG_ZOOM_OUT = 0x46
JOG_FOCUS_NEAR = 0x6A
JOG_FOCUS_FAR = 0x6C

# Default step (speed) used for jog commands, range is roughly 0x10-0x7f
DEFAULT_JOG_STEP = 0x40

# How long a "click" (press+release) holds the button down, in seconds
CLICK_HOLD_SECONDS = 0.15
