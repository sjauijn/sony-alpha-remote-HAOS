from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
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
    device: SonyCameraDevice = entry.runtime_data
    async_add_entities([SonyCameraSelfTimerNumber(device, entry)])

class SonyCameraSelfTimerNumber(NumberEntity):

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 1
    _attr_native_max_value = 60
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "s"
    _attr_translation_key = "self_timer_seconds"

    def __init__(self, device: SonyCameraDevice, entry: ConfigEntry) -> None:
        self._device = device
        mac = entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_self_timer_seconds"
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
    def native_value(self) -> float:
        return self._device.state.self_timer_seconds

    async def async_set_native_value(self, value: float) -> None:
        self._device.set_self_timer_seconds(round(value))

