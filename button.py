from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_MAC, DOMAIN
from .device import SonyCameraDevice

PARALLEL_UPDATES = 0

@dataclass(frozen=True, kw_only=True)
class SonyCameraButtonDescription(ButtonEntityDescription):

    action: Callable[[SonyCameraDevice], Awaitable[None]]

BUTTON_DESCRIPTIONS: tuple[SonyCameraButtonDescription, ...] = (
    SonyCameraButtonDescription(
        key="shutter",
        translation_key="shutter",
        action=lambda device: device.async_shutter(),
    ),
    SonyCameraButtonDescription(
        key="af_on",
        translation_key="af_on",
        action=lambda device: device.async_af_on(),
    ),
    SonyCameraButtonDescription(
        key="record",
        translation_key="record",
        action=lambda device: device.async_record_toggle(),
    ),
    SonyCameraButtonDescription(
        key="c1",
        translation_key="c1",
        action=lambda device: device.async_c1(),
    ),
    SonyCameraButtonDescription(
        key="zoom_in",
        translation_key="zoom_in",
        action=lambda device: device.async_zoom_in(),
    ),
    SonyCameraButtonDescription(
        key="zoom_out",
        translation_key="zoom_out",
        action=lambda device: device.async_zoom_out(),
    ),
    SonyCameraButtonDescription(
        key="focus_near",
        translation_key="focus_near",
        action=lambda device: device.async_focus_near(),
    ),
    SonyCameraButtonDescription(
        key="focus_far",
        translation_key="focus_far",
        action=lambda device: device.async_focus_far(),
    ),
    SonyCameraButtonDescription(
        key="self_timer_shutter",
        translation_key="self_timer_shutter",
        action=lambda device: device.async_start_self_timer(),
    ),
    SonyCameraButtonDescription(
        key="self_timer_cancel",
        translation_key="self_timer_cancel",
        action=lambda device: device.async_cancel_self_timer(),
    ),
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    device: SonyCameraDevice = entry.runtime_data
    async_add_entities(
        SonyCameraButton(device, entry, description)
        for description in BUTTON_DESCRIPTIONS
    )

class SonyCameraButton(ButtonEntity):

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: SonyCameraButtonDescription

    def __init__(
        self,
        device: SonyCameraDevice,
        entry: ConfigEntry,
        description: SonyCameraButtonDescription,
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

    async def async_press(self) -> None:
        await self.entity_description.action(self._device)

