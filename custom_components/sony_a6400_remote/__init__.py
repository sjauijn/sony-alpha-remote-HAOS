"""The Sony Camera BLE Remote integration."""
from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_MAC, DOMAIN
from .device import SonyCameraDevice

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.BINARY_SENSOR]

type SonyCameraConfigEntry = ConfigEntry[SonyCameraDevice]


async def async_setup_entry(hass: HomeAssistant, entry: SonyCameraConfigEntry) -> bool:
    """Set up Sony Camera BLE Remote from a config entry."""
    mac = entry.data[CONF_MAC]

    ble_device = bluetooth.async_ble_device_from_address(
        hass, mac, connectable=True
    )
    if ble_device is None:
        raise ConfigEntryNotReady(
            f"Could not find camera with address {mac}. "
            "Make sure the camera is turned on, Bluetooth remote control is "
            "enabled in its menu, and it is paired/bonded with this host."
        )

    device = SonyCameraDevice(ble_device)
    entry.runtime_data = device

    @callback
    def _async_update_ble(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        device.set_ble_device(service_info.device)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_update_ble,
            {"address": mac},
            bluetooth.BluetoothScanningMode.PASSIVE,
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SonyCameraConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and entry.runtime_data is not None:
        await entry.runtime_data.async_disconnect()
    return unload_ok
