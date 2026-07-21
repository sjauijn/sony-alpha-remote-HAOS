"""Sensor platform for Sony Camera BLE Remote.

Exposes the self-timer countdown as it runs, so it can be shown on a
dashboard or used in automations (e.g. to know when the shutter is about
to fire).
"""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MAC, DOMAIN
from .device import SonyCameraDevice

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    device: SonyCameraDevice = entry.runtime_data
    async_add_entities([SonyCameraSelfTimerRemainingSensor(device, entry)])


class SonyCameraSelfTimerRemainingSensor(SensorEntity):
    """Seconds remaining on an active self-timer countdown, if any."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_native_unit_of_measurement = "s"
    _attr_translation_key = "self_timer_remaining"

    def __init__(self, device: SonyCameraDevice, entry: ConfigEntry) -> None:
        self._device = device
        mac = entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_self_timer_remaining"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=entry.title,
            manufacturer="Sony",
            model="Camera Remote (BLE)",
        )

    async def async_added_to_hass(self) -> None:
        self._device.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._device.remove_callback(self.async_write_ha_state)

    @property
    def available(self) -> bool:
        return self._device.available

    @property
    def native_value(self) -> int | None:
        return self._device.state.self_timer_remaining
