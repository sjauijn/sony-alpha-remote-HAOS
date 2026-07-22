import logging
from contextlib import asynccontextmanager

from dbus_fast import BusType
from dbus_fast.aio import MessageBus
from dbus_fast.service import ServiceInterface, method

_LOGGER = logging.getLogger(__name__)

AGENT_PATH = "/org/bluez/agent/sony_alpha_remote"
AGENT_MANAGER_IFACE = "org.bluez.AgentManager1"
AGENT_MANAGER_PATH = "/org/bluez"

AGENT_CAPABILITY = "NoInputNoOutput"

class _AutoAcceptAgent(ServiceInterface):

    def __init__(self) -> None:
        super().__init__("org.bluez.Agent1")

    @method()
    def Release(self) -> None:
        pass

    @method()
    def RequestPinCode(self, device: "o") -> "s":
        return "0000"

    @method()
    def DisplayPinCode(self, device: "o", pincode: "s") -> None:
        pass

    @method()
    def RequestPasskey(self, device: "o") -> "u":
        return 0

    @method()
    def DisplayPasskey(self, device: "o", passkey: "u", entered: "q") -> None:
        pass

    @method()
    def RequestConfirmation(self, device: "o", passkey: "u") -> None:

        _LOGGER.debug("Auto-confirming pairing for %s", device)

    @method()
    def RequestAuthorization(self, device: "o") -> None:
        pass

    @method()
    def AuthorizeService(self, device: "o", uuid: "s") -> None:
        pass

    @method()
    def Cancel(self) -> None:
        pass

@asynccontextmanager
async def bluez_pairing_agent():
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    agent = _AutoAcceptAgent()
    bus.export(AGENT_PATH, agent)

    introspection = await bus.introspect("org.bluez", AGENT_MANAGER_PATH)
    proxy = bus.get_proxy_object("org.bluez", AGENT_MANAGER_PATH, introspection)
    agent_manager = proxy.get_interface(AGENT_MANAGER_IFACE)

    await agent_manager.call_register_agent(AGENT_PATH, AGENT_CAPABILITY)
    try:
        await agent_manager.call_request_default_agent(AGENT_PATH)
    except Exception:

        _LOGGER.debug("Could not request default agent", exc_info=True)

    try:
        yield
    finally:
        try:
            await agent_manager.call_unregister_agent(AGENT_PATH)
        except Exception:
            _LOGGER.debug("Could not unregister pairing agent", exc_info=True)
        bus.unexport(AGENT_PATH)
        bus.disconnect()

