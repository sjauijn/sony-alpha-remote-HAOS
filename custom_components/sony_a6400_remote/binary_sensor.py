"""Binary sensor platform for Sony Camera BLE Remote.

Exposes the three pieces of state the camera actually reports over BLE
notifications: autofocus acquired, shutter open, and recording. Plus a
connectivity sensor for the BLE link itself.
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
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
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
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.connected,
    ),
    SonyCameraBinarySensorDescription(
        key="focus_acquired",
        translation_key="focus_acquired",
        value_fn=lambda state: state.focus_acquired,
    ),
    SonyCameraBinarySensorDescription(
        key="shutter_open",
        translation_key="shutter_open",
        value_fn=lambda state: state.shutter_open,
    ),
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
        self._device.on_update = self.async_write_ha_state

    async def async_will_remove_from_hass(self) -> None:
        self._device.on_update = None

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self._device.state)
