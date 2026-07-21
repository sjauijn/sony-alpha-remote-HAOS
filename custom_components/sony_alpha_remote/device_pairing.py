"""BLE pairing/bonding helper.

The camera prompts for confirmation on its own screen (a "Pair with
<host>?" dialog) during pairing. For BlueZ to deliver that prompt to
anything, an Agent must be registered on org.bluez.AgentManager1 --
normally provided as a side effect of running `bluetoothctl` or opening a
desktop Bluetooth settings panel. On a headless Home Assistant OS host,
neither is running, so bleak's `BleakClient.pair()` fails outright with
`org.bluez.Error.AuthenticationFailed`: BlueZ has no agent to ask.

This module registers a minimal, temporary agent (see bluez_agent.py) for
the duration of the pairing attempt, so the whole flow works from the UI
with no SSH/bluetoothctl step required.

Note: BleakClient.pair() returns None on success and raises on failure
(it does not return a boolean) as of bleak >= 1.0. A failed attempt can
leave a half-bonded device entry in BlueZ, which would make a retry
confusing (e.g. "already paired" when it plainly isn't usable), so on
failure this module also calls unpair() to remove that stale entry.
"""
from __future__ import annotations

import asyncio
import logging

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from .bluez_agent import bluez_pairing_agent

_LOGGER = logging.getLogger(__name__)

PAIR_TIMEOUT = 30.0


class CameraPairingError(Exception):
    """Raised when pairing/bonding with the camera fails."""


async def async_pair_camera(ble_device: BLEDevice) -> None:
    """Pair (bond) with the camera over BLE.

    Registers a temporary auto-accept BlueZ pairing agent for the duration
    of the call so the confirmation prompt shown on the camera's screen can
    actually be answered, then calls BleakClient.pair() -- the same D-Bus
    Pair() call `bluetoothctl pair` makes under the hood.

    Raises CameraPairingError with a human-readable reason on failure.
    """
    client = BleakClient(ble_device)
    connected = False
    try:
        async with asyncio.timeout(PAIR_TIMEOUT):
            async with bluez_pairing_agent():
                await client.connect()
                connected = True
                try:
                    await client.pair()
                except NotImplementedError as err:
                    # Non-BlueZ backends may not implement pair() at all;
                    # connecting may already be enough to trigger bonding
                    # on the peripheral side in that case.
                    _LOGGER.debug(
                        "pair() not implemented on this backend: %s", err
                    )
    except TimeoutError as err:
        await _async_cleanup_failed_pairing(client, connected)
        raise CameraPairingError(
            "Timed out while pairing. If the camera showed a confirmation "
            "prompt, make sure to accept it there within a few seconds. "
            "Otherwise, make sure the camera is turned on, awake, and "
            "within range."
        ) from err
    except BleakError as err:
        await _async_cleanup_failed_pairing(client, connected)
        raise CameraPairingError(f"Bluetooth error while pairing: {err}") from err
    else:
        try:
            await client.disconnect()
        except BleakError:
            pass


async def _async_cleanup_failed_pairing(client: BleakClient, connected: bool) -> None:
    """Best-effort cleanup so a retry doesn't get stuck on a stale bond."""
    if not connected:
        return
    try:
        await client.unpair()
    except (BleakError, NotImplementedError, AttributeError):
        # unpair() may not exist on all bleak versions/backends; that's
        # fine, it's only a best-effort cleanup so retries are clean.
        pass
    try:
        await client.disconnect()
    except BleakError:
        pass
