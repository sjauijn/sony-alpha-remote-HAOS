from __future__ import annotations

import asyncio
import logging

from bleak import BleakClient
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from dbus_fast import BusType
from dbus_fast.aio import MessageBus
from dbus_fast.errors import DBusError

from .bluez_agent import bluez_pairing_agent

_LOGGER = logging.getLogger(__name__)

PAIR_TIMEOUT = 30.0
UNPAIR_TIMEOUT = 10.0

class CameraPairingError(Exception):
    pass

async def async_pair_camera(ble_device: BLEDevice) -> None:
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
    if not connected:
        return
    try:
        await client.unpair()
    except (BleakError, NotImplementedError, AttributeError):

        pass
    try:
        await client.disconnect()
    except BleakError:
        pass

async def async_forget_camera(mac: str) -> None:
    bus: MessageBus | None = None
    try:
        async with asyncio.timeout(UNPAIR_TIMEOUT):
            bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

            root_introspection = await bus.introspect("org.bluez", "/")
            root_proxy = bus.get_proxy_object("org.bluez", "/", root_introspection)
            om = root_proxy.get_interface("org.freedesktop.DBus.ObjectManager")
            objects = await om.call_get_managed_objects()

            mac_path_fragment = "dev_" + mac.upper().replace(":", "_")
            device_path = None
            adapter_path = None
            for path, interfaces in objects.items():
                if "org.bluez.Device1" in interfaces and path.endswith(
                    mac_path_fragment
                ):
                    device_path = path

                    adapter_path = path.rsplit("/", 1)[0]
                    break

            if device_path is None or adapter_path is None:
                _LOGGER.debug(
                    "No BlueZ device entry found for %s, nothing to remove", mac
                )
                return

            adapter_introspection = await bus.introspect("org.bluez", adapter_path)
            adapter_proxy = bus.get_proxy_object(
                "org.bluez", adapter_path, adapter_introspection
            )
            adapter = adapter_proxy.get_interface("org.bluez.Adapter1")
            await adapter.call_remove_device(device_path)
            _LOGGER.debug("Removed BlueZ device entry for %s", mac)
    except TimeoutError:
        _LOGGER.warning("Timed out removing BlueZ pairing for %s", mac)
    except DBusError as err:
        _LOGGER.warning("Could not remove BlueZ pairing for %s: %s", mac, err)
    except Exception:

        _LOGGER.exception("Unexpected error removing BlueZ pairing for %s", mac)
    finally:
        if bus is not None:
            bus.disconnect()

