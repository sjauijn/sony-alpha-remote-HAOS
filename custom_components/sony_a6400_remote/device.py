"""BLE device wrapper for a Sony Camera Remote (A6400 and compatible models).

Mirrors the connection/write pattern used by the app's original Android
implementation (CameraBLE.kt): connect to a GATT server that must already be
*bonded* at the OS level, write single-byte-prefixed commands to the command
characteristic, and (optionally) subscribe to the status characteristic for
focus/shutter/recording state.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import (
    BTN_AF_ON,
    BTN_C1,
    BTN_RECORD,
    BTN_SHUTTER_FULL,
    BTN_SHUTTER_HALF,
    CLICK_HOLD_SECONDS,
    COMMAND_CHAR_UUID,
    DEFAULT_JOG_STEP,
    JOG_FOCUS_FAR,
    JOG_FOCUS_NEAR,
    JOG_ZOOM_IN,
    JOG_ZOOM_OUT,
    STATUS_CHAR_UUID,
)

_LOGGER = logging.getLogger(__name__)


class SonyCameraState:
    """In-memory state of the camera, filled in from status notifications."""

    def __init__(self) -> None:
        self.connected: bool = False
        self.focus_acquired: bool = False
        self.shutter_open: bool = False
        self.recording: bool = False


class SonyCameraDevice:
    """Manages the BLE connection and command dispatch to the camera."""

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device
        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()
        self.state = SonyCameraState()
        self.on_update: Callable[[], None] | None = None

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device

    async def _ensure_connected(self) -> BleakClientWithServiceCache:
        if self._client is not None and self._client.is_connected:
            return self._client
        _LOGGER.debug("Connecting to %s", self._ble_device.address)
        client = await establish_connection(
            BleakClientWithServiceCache,
            self._ble_device,
            self._ble_device.address,
        )
        self._client = client
        try:
            await client.start_notify(
                STATUS_CHAR_UUID, self._handle_status_notification
            )
        except BleakError as err:
            # Not fatal: button presses still work without status feedback.
            _LOGGER.debug("Could not subscribe to status characteristic: %s", err)
        self.state.connected = True
        self._notify()
        return client

    def _handle_status_notification(self, _handle: int, data: bytearray) -> None:
        # Byte 1 identifies which piece of state changed, bit 0x20 of byte 2
        # is the boolean value. See CameraBLE.kt::onCameraStatusUpdate.
        if len(data) < 3:
            return
        tag = data[1]
        value = bool(data[2] & 0x20)
        if tag == 0x3F:
            self.state.focus_acquired = value
        elif tag == 0xA0:
            self.state.shutter_open = value
        elif tag == 0xD5:
            self.state.recording = value
        else:
            return
        self._notify()

    async def _write(self, data: bytes) -> None:
        async with self._lock:
            client = await self._ensure_connected()
            await client.write_gatt_char(COMMAND_CHAR_UUID, data, response=False)

    def _notify(self) -> None:
        if self.on_update is not None:
            self.on_update()

    async def async_disconnect(self) -> None:
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()
        self._client = None
        self.state.connected = False

    # -- Low level button / jog primitives -----------------------------------

    async def _button(self, code: int, pressed: bool) -> None:
        await self._write(bytes([0x01, code | (0x01 if pressed else 0x00)]))

    async def _jog(self, code: int, pressed: bool, step: int = DEFAULT_JOG_STEP) -> None:
        await self._write(
            bytes([0x02, code | (0x01 if pressed else 0x00), step if pressed else 0x00])
        )

    async def _click_button(self, code: int) -> None:
        await self._button(code, True)
        await asyncio.sleep(CLICK_HOLD_SECONDS)
        await self._button(code, False)

    # -- High level camera actions --------------------------------------------

    async def async_shutter(self) -> None:
        """Full shutter press: half-press then full-press then release."""
        await self._button(BTN_SHUTTER_HALF, True)
        await self._button(BTN_SHUTTER_FULL, True)
        await asyncio.sleep(CLICK_HOLD_SECONDS)
        await self._button(BTN_SHUTTER_FULL, False)
        await self._button(BTN_SHUTTER_HALF, False)

    async def async_af_on(self) -> None:
        """Emulate holding the AF-On button briefly (autofocus trigger)."""
        await self._click_button(BTN_AF_ON)

    async def async_record_toggle(self) -> None:
        """Emulate the record button (start/stop video recording)."""
        await self._click_button(BTN_RECORD)

    async def async_c1(self) -> None:
        """Emulate the C1 custom button."""
        await self._click_button(BTN_C1)

    async def async_zoom_in(self, step: int = DEFAULT_JOG_STEP) -> None:
        await self._jog(JOG_ZOOM_IN, True, step)
        await asyncio.sleep(CLICK_HOLD_SECONDS)
        await self._jog(JOG_ZOOM_IN, False)

    async def async_zoom_out(self, step: int = DEFAULT_JOG_STEP) -> None:
        await self._jog(JOG_ZOOM_OUT, True, step)
        await asyncio.sleep(CLICK_HOLD_SECONDS)
        await self._jog(JOG_ZOOM_OUT, False)

    async def async_focus_near(self, step: int = DEFAULT_JOG_STEP) -> None:
        """Nudge manual focus nearer. Camera/lens must already be in MF/DMF."""
        await self._jog(JOG_FOCUS_NEAR, True, step)
        await asyncio.sleep(CLICK_HOLD_SECONDS)
        await self._jog(JOG_FOCUS_NEAR, False)

    async def async_focus_far(self, step: int = DEFAULT_JOG_STEP) -> None:
        """Nudge manual focus farther. Camera/lens must already be in MF/DMF."""
        await self._jog(JOG_FOCUS_FAR, True, step)
        await asyncio.sleep(CLICK_HOLD_SECONDS)
        await self._jog(JOG_FOCUS_FAR, False)
