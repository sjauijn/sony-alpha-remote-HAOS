from __future__ import annotations

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

    VERSION = 1

    def __init__(self) -> None:
        self._mac: str | None = None
        self._name: str | None = None

    async def _async_do_pair(self) -> ConfigFlowResult:
        ble_device = async_ble_device_from_address(
            self.hass, self._mac, connectable=True
        )
        if ble_device is None:
            return self.async_show_form(
                step_id="pair",
                errors={"base": "not_found"},
                description_placeholders={"name": self._name or self._mac},
            )

        try:
            await async_pair_camera(ble_device)
        except CameraPairingError as err:
            _LOGGER.warning("Pairing with %s failed: %s", self._mac, err)
            return self.async_show_form(
                step_id="pair",
                errors={"base": "pairing_failed"},
                description_placeholders={
                    "name": self._name or self._mac,
                    "error": str(err),
                },
            )

        return self.async_create_entry(
            title=self._name or f"Sony Camera ({self._mac})",
            data={CONF_MAC: self._mac},
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(format_mac(discovery_info.address))
        self._abort_if_unique_id_configured()
        self._mac = discovery_info.address
        self._name = discovery_info.name or discovery_info.address
        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id="bluetooth_confirm",
                description_placeholders={"name": self._name},
            )
        return await self.async_step_pair()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
        if user_input is None:

            return self.async_show_form(
                step_id="pair",
                description_placeholders={"name": self._name or self._mac},
            )
        return await self._async_do_pair()

