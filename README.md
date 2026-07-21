# Sony Alpha Remote BT — Home Assistant Integration

Custom Home Assistant integration for **Sony Alpha (ILCE-*) cameras** with
Bluetooth remote control, connected directly over Bluetooth LE — no phone,
no official Sony app required. Protocol reverse engineered by
[Coral](https://github.com/coral/freemote),
[Greg Leeds](https://gregleeds.com/reverse-engineering-sony-camera-bluetooth/)
and Mark Kirschenbaum, and re-derived here from the
[alpharemote](https://github.com/Staacks/alpharemote) .

## Features

- **Button entities** — Shutter, AF On, Record, C1, Zoom in/out,
  Focus near/far
- **Self-timer** — set a delay (1–60s) and fire the shutter after it
  counts down, same as the self-timer in the reference app
- **Binary sensor** — Recording status

There is no "focus mode" control (AF-S/AF-C/MF) because the camera does not
expose that switch over Bluetooth — only AF-On and manual focus near/far
nudges are available, and manual focus nudges require the camera/lens to
already be in MF or DMF mode via the physical switch.

## Compatibility

This integration should work with any camera that is compatible with Sony's
small physical **Bluetooth** (not IR!) remote control.

So far, this has been confirmed for the following models:

ILCE-6400 (α6400), ILCE-6600 (α6600), ILCE-6700 (α6700), ILCE-7M3 (α7 III),
ILCE-7CM2 (α7C II), ILCE-7M4 (α7 IV), ILCE-7RM3 (α7R III), ILCE-7RM4 (α7R IV),
ILCE-7RM5 (α7R V), ILCE-9 (α9), ZV-E10

It is expected to also work with the following models:

DSC-RX100M7, DSC-RX100M7G, ZV-1, ILCE-7M4K, ILCE-7RM4A, ZV-E10, ZV-E10L,
ILCE-1, ILCE-7C, ILCE-7CL, ILCE-7SM3, ILCE-9M2, ILCE-6100, ILCE-6100L,
ILCE-6100Y, ILCE-6600M, ILCE-6400L, ILCE-6400M, ILCE-7M3, ILCE-7M3K,
ILCE-7RM3, ILCE-9, ILME-FX2, ILME-FX3, ILME-FX3A, ILX-LR1

Please let me know if your camera works if it has not yet been confirmed
here.

## Installation via HACS (custom repository)

1. HACS → Integrations → ⋮ menu (top right) → **Custom repositories**
2. Add this repository URL, category **Integration**
3. Install **Sony Alpha Remote BT**, restart Home Assistant

## Setup

1. In the camera's menu, enable **Bluetooth Rmt Ctrl** (Menu > Network >
   Bluetooth) and keep the camera awake and nearby
2. Settings → Devices & services → **Add Integration** → search for "Sony
   Alpha Remote BT"
3. If discovered, confirm your camera; otherwise pick it from the list or
   enter its Bluetooth address manually
4. Home Assistant will pair (bond) with the camera — press Submit and
   accept the confirmation prompt shown on the camera's own screen, if any

## Requirements

- Home Assistant instance with Bluetooth support (built-in adapter or a
  [Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html))
  within range of the camera
- A Sony Alpha camera with Bluetooth Remote Control support, with that
  feature enabled in its menu

## Disclaimer

This is an unofficial, reverse-engineered integration and is not
affiliated with or endorsed by Sony.
