from app.adapters.contracts import DeviceAdapter
from app.adapters.virtual import VirtualDeviceAdapter
from app.core.errors import Unavailable


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, DeviceAdapter] = {"virtual": VirtualDeviceAdapter()}

    def connect(self) -> None:
        for adapter in self._adapters.values():
            adapter.connect()

    def disconnect(self) -> None:
        for adapter in self._adapters.values():
            adapter.disconnect()

    def get(self, adapter_type: str) -> DeviceAdapter:
        adapter = self._adapters.get(adapter_type)
        if adapter is None or not adapter.get_connection_status():
            raise Unavailable("Адаптер устройства недоступен.")
        return adapter
