"""Minimal BlueZ pairing agent, registered over D-Bus.

Why this exists: BlueZ's bluetoothd requires an Agent object registered on
org.bluez.AgentManager1 to handle pairing confirmation prompts. Normally
`bluetoothctl` or a desktop environment's Bluetooth settings panel provides
this agent as a side effect of being open. On a headless Home Assistant OS
host, nothing provides it, so a bare `BleakClient.pair()` call fails with
`org.bluez.Error.AuthenticationFailed` -- BlueZ has nowhere to send the
confirmation request (the "Pair with <this host>?" prompt on the camera)
and gives up.

This module implements just enough of org.bluez.Agent1 to auto-accept
confirmation/authorization requests, mirroring what `bluetoothctl`'s
built-in agent (or `bt-agent --capability=NoInputNoOutput`) does. It is
registered for the duration of a single pairing attempt and unregistered
immediately after, so it does not interfere with pairing flows for other
integrations or the Bluetooth settings UI.

See: https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/org.bluez.Agent.rst

IMPORTANT: this module must NOT use `from __future__ import annotations`.
dbus_fast's @method() decorator reads parameter annotations at class-body
execution time to build the D-Bus method signature (e.g. "o", "u", "s").
With postponed evaluation of annotations enabled, those annotations become
plain strings *containing quote characters* instead of the raw signature
characters, which dbus_fast cannot parse, and class definition fails with
`TypeError: Argument 'signature' has incorrect type`.
"""

import logging
from contextlib import asynccontextmanager

from dbus_fast import BusType
from dbus_fast.aio import MessageBus
from dbus_fast.service import ServiceInterface, method

_LOGGER = logging.getLogger(__name__)

AGENT_PATH = "/org/bluez/agent/sony_alpha_remote"
AGENT_MANAGER_IFACE = "org.bluez.AgentManager1"
AGENT_MANAGER_PATH = "/org/bluez"

# NoInputNoOutput tells BlueZ this agent cannot show a passkey or accept
# keyboard input, so BlueZ (and the peer) fall back to Just Works /
# auto-confirm flows wherever the peer allows it. This matches what the
# camera actually asks for (a plain yes/no prompt on its own screen, no
# passkey exchange), and is the same capability `bluetoothctl agent
# NoInputNoOutput` registers.
AGENT_CAPABILITY = "NoInputNoOutput"


class _AutoAcceptAgent(ServiceInterface):
    """Implements org.bluez.Agent1, auto-accepting all requests.

    This is intentionally permissive: it is only registered as the default
    agent for the few seconds a single, user-initiated pairing attempt
    takes, for a device address the user explicitly chose in the config
    flow. It is not left running.
    """

    def __init__(self) -> None:
        super().__init__("org.bluez.Agent1")

    @method()
    def Release(self) -> None:  # noqa: N802 - D-Bus method name
        pass

    @method()
    def RequestPinCode(self, device: "o") -> "s":  # noqa: N802,F821
        return "0000"

    @method()
    def DisplayPinCode(self, device: "o", pincode: "s") -> None:  # noqa: N802,F821
        pass

    @method()
    def RequestPasskey(self, device: "o") -> "u":  # noqa: N802,F821
        return 0

    @method()
    def DisplayPasskey(self, device: "o", passkey: "u", entered: "q") -> None:  # noqa: N802,F821
        pass

    @method()
    def RequestConfirmation(self, device: "o", passkey: "u") -> None:  # noqa: N802,F821
        # Auto-confirm. This is the call BlueZ makes for the "Pair with
        # <host>?" style prompt shown on the camera's own screen.
        _LOGGER.debug("Auto-confirming pairing for %s", device)

    @method()
    def RequestAuthorization(self, device: "o") -> None:  # noqa: N802,F821
        pass

    @method()
    def AuthorizeService(self, device: "o", uuid: "s") -> None:  # noqa: N802,F821
        pass

    @method()
    def Cancel(self) -> None:  # noqa: N802 - D-Bus method name
        pass


@asynccontextmanager
async def bluez_pairing_agent():
    """Register a temporary auto-accept agent as BlueZ's default agent.

    Usage:
        async with bluez_pairing_agent():
            await client.pair()

    On exit, unregisters the agent and closes the D-Bus connection used
    for it. Any failure to unregister is logged, not raised, so it never
    masks the real pairing result.
    """
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    agent = _AutoAcceptAgent()
    bus.export(AGENT_PATH, agent)

    introspection = await bus.introspect("org.bluez", AGENT_MANAGER_PATH)
    proxy = bus.get_proxy_object("org.bluez", AGENT_MANAGER_PATH, introspection)
    agent_manager = proxy.get_interface(AGENT_MANAGER_IFACE)

    await agent_manager.call_register_agent(AGENT_PATH, AGENT_CAPABILITY)
    try:
        await agent_manager.call_request_default_agent(AGENT_PATH)
    except Exception:  # noqa: BLE001
        # Not fatal -- pairing may still work if another suitable agent is
        # already default, but this is unexpected, so log it.
        _LOGGER.debug("Could not request default agent", exc_info=True)

    try:
        yield
    finally:
        try:
            await agent_manager.call_unregister_agent(AGENT_PATH)
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not unregister pairing agent", exc_info=True)
        bus.unexport(AGENT_PATH)
        bus.disconnect()
