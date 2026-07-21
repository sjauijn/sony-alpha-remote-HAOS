"""Binary sensor platform for Sony Camera BLE Remote.

Exposes the recording status the camera reports over BLE notifications.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MAC, DOMAIN
from .device import SonyCameraDevice, SonyCameraState

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SonyCameraBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a Sony camera status binary sensor."""

    value_fn: Callable[[SonyCameraState], bool]


SENSOR_DESCRIPTIONS: tuple[SonyCameraBinarySensorDescription, ...] = (
    SonyCameraBinarySensorDescription(
        key="recording",
        translation_key="recording",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        value_fn=lambda state: state.recording,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    device: SonyCameraDevice = entry.runtime_data
    async_add_entities(
        SonyCameraBinarySensor(device, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class SonyCameraBinarySensor(BinarySensorEntity):
    """Representation of a camera status flag."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: SonyCameraBinarySensorDescription

    def __init__(
        self,
        device: SonyCameraDevice,
        entry: ConfigEntry,
        description: SonyCameraBinarySensorDescription,
    ) -> None:
        self._device = device
        self.entity_description = description
        mac = entry.data[CONF_MAC]
        self._attr_unique_id = f"{mac}_{description.key}"
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
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self._device.state)
