from typing import Protocol

from pydantic import JsonValue


class DeviceAdapter(Protocol):
    """Transport boundary. Services own validation, persistence and event logging."""

    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def get_state(self, device_id: int) -> dict[str, JsonValue]: ...

    def execute_command(
        self, device_id: int, command: str, params: dict[str, JsonValue]
    ) -> dict[str, JsonValue]: ...

    def get_connection_status(self) -> bool: ...
