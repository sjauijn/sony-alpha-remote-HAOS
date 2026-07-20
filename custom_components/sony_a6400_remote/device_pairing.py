"""BLE pairing/bonding helper.

Sony's camera BLE remote protocol uses "Just Works" Secure Simple Pairing:
no PIN, no numeric comparison, no button press needed on either side beyond
what the camera itself requires (having Bluetooth Rmt Ctrl turned on and
being in range). This means bonding can be triggered programmatically from
within the config flow instead of requiring the user to run bluetoothctl by
hand.

On Linux/BlueZ, bleak's BleakClient.pair() issues the D-Bus Pair() call on
the org.bluez.Device1 interface, which is exactly what `bluetoothctl pair`
does under the hood. This module wraps that in a small helper with timeouts
and clear exceptions so the config flow can surface useful errors to the UI.
"""
from __future__ import annotations

import asyncio
import logging

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

_LOGGER = logging.getLogger(__name__)

PAIR_TIMEOUT = 20.0


class CameraPairingError(Exception):
    """Raised when pairing/bonding with the camera fails."""


async def async_pair_camera(ble_device: BLEDevice) -> None:
    """Pair (bond) with the camera over BLE using BlueZ's Just Works flow.

    Raises CameraPairingError with a human-readable reason on failure.
    """
    client = BleakClient(ble_device)
    try:
        async with asyncio.timeout(PAIR_TIMEOUT):
            await client.connect()
            try:
                paired = await client.pair()
            except NotImplementedError as err:
                # Non-BlueZ backends (e.g. some embedded platforms) may not
                # implement pair() at all; connecting may already be enough
                # to trigger bonding on the peripheral side in that case.
                _LOGGER.debug("pair() not implemented on this backend: %s", err)
                paired = True
            if not paired:
                raise CameraPairingError(
                    "The camera rejected the pairing request. Make sure "
                    "'Bluetooth Rmt Ctrl' is enabled in the camera's menu "
                    "and that no other device is currently connected to it."
                )
    except TimeoutError as err:
        raise CameraPairingError(
            "Timed out while pairing. Make sure the camera is turned on, "
            "awake, and within range."
        ) from err
    except BleakError as err:
        raise CameraPairingError(f"Bluetooth error while pairing: {err}") from err
    finally:
        try:
            await client.disconnect()
        except BleakError:
            pass
