"""Config flow for Sony Camera BLE Remote integration.

Pairing/bonding with the camera is performed here, from the UI, using BLE's
"Just Works" bonding (Sony's remote protocol needs no PIN). No SSH or
bluetoothctl required.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.device_registry import format_mac

from .const import CONF_MAC, DOMAIN
from .device_pairing import CameraPairingError, async_pair_camera

_LOGGER = logging.getLogger(__name__)


class SonyCameraConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sony Camera BLE Remote."""

    VERSION = 1

    def __init__(self) -> None:
        self._mac: str | None = None
        self._name: str | None = None
        self._pair_task: asyncio.Task[None] | None = None
        self._pair_error: CameraPairingError | None = None

    async def _async_pair_task(self) -> None:
        """Background task that does the actual pairing (runs for up to
        PAIR_TIMEOUT seconds), so the HTTP/WS request that triggers a step
        doesn't have to stay open that long. Home Assistant's frontend
        gives up on a step submission after ~10s; without show_progress the
        pairing attempt kept running in the background with nothing to
        show the result to, which is why Submit appeared to do nothing.
        """
        self._pair_error = None
        ble_device = async_ble_device_from_address(
            self.hass, self._mac, connectable=True
        )
        if ble_device is None:
            self._pair_error = CameraPairingError("not_found")
            return
        try:
            await async_pair_camera(ble_device)
        except CameraPairingError as err:
            _LOGGER.warning("Pairing with %s failed: %s", self._mac, err)
            self._pair_error = err

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle discovery via Bluetooth."""
        await self.async_set_unique_id(format_mac(discovery_info.address))
        self._abort_if_unique_id_configured()
        self._mac = discovery_info.address
        self._name = discovery_info.name or discovery_info.address
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovered device, then move to pairing."""
        if user_input is None:
            return self.async_show_form(
                step_id="bluetooth_confirm",
                description_placeholders={"name": self._name},
            )
        return await self.async_step_pair()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user: pick or type in a MAC."""
        errors: dict[str, str] = {}

        discovered: dict[str, str] = {}
        for info in async_discovered_service_info(self.hass, connectable=True):
            name = (info.name or "").upper()
            if name.startswith("ILCE-"):
                discovered[info.address] = f"{info.name} ({info.address})"

        if user_input is not None:
            mac = user_input[CONF_MAC].strip().upper()
            await self.async_set_unique_id(format_mac(mac))
            self._abort_if_unique_id_configured()
            self._mac = mac
            self._name = discovered.get(mac)
            return await self.async_step_pair()

        if discovered:
            schema = vol.Schema({vol.Required(CONF_MAC): vol.In(discovered)})
        else:
            schema = vol.Schema({vol.Required(CONF_MAC): str})

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    async def async_step_pair(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Perform BLE pairing/bonding with the camera.

        This is where the actual bonding happens -- equivalent to
        `bluetoothctl pair <mac>` but triggered from the UI. Sony's remote
        protocol uses Just Works bonding, so no PIN entry step is needed;
        the only requirement is that the camera has 'Bluetooth Rmt Ctrl'
        enabled and is awake/in range.
        """
        if user_input is None:
            # First visit to this step: show a confirmation form, then
            # move to the progress step once the user submits it.
            return self.async_show_form(
                step_id="pair",
                description_placeholders={"name": self._name or self._mac},
            )
        return await self.async_step_pair_progress()

    async def async_step_pair_progress(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show a progress screen while pairing runs in the background.

        Pairing can take several seconds (BLE connect, then the actual
        bond) and Home Assistant's frontend stops waiting on a step
        submission after about 10 seconds. Running the work as a tracked
        background task and returning async_show_progress keeps the UI
        updated instead of the Submit button silently doing nothing.
        """
        if self._pair_task is None:
            self._pair_task = self.hass.async_create_task(self._async_pair_task())

        if not self._pair_task.done():
            return self.async_show_progress(
                progress_action="pair",
                progress_task=self._pair_task,
                description_placeholders={"name": self._name or self._mac},
            )

        self._pair_task = None

        if self._pair_error is not None:
            return self.async_show_progress_done(next_step_id="pair_failed")

        return self.async_show_progress_done(next_step_id="pair_done")

    async def async_step_pair_done(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pairing succeeded: create the config entry."""
        return self.async_create_entry(
            title=self._name or f"Sony Camera ({self._mac})",
            data={CONF_MAC: self._mac},
        )

    async def async_step_pair_failed(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pairing failed: show the error and let the user retry."""
        error = self._pair_error
        self._pair_error = None
        error_key = "not_found" if str(error) == "not_found" else "pairing_failed"
        placeholders = {"name": self._name or self._mac}
        if error_key == "pairing_failed":
            placeholders["error"] = str(error)
        return self.async_show_form(
            step_id="pair",
            errors={"base": error_key},
            description_placeholders=placeholders,
        )
