from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from pydantic import JsonValue


@dataclass(frozen=True)
class DeviceSnapshot:
    """Persisted data supplied by services; adapters do not own a state store."""

    device_id: int
    device_type: str
    parameters: dict[str, JsonValue]
    values: dict[str, JsonValue]


class DeviceAdapter(Protocol):
    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def validate_parameters(self, device_type: str, parameters: dict) -> dict: ...

    def initial_state(self, device_type: str) -> dict: ...

    def validate_command(self, device_type: str, command: str, params: dict) -> dict: ...

    def get_state(self, device: DeviceSnapshot) -> dict: ...

    def execute_command(
        self, device: DeviceSnapshot, command: str, params: dict, now: datetime
    ) -> dict: ...

    def get_connection_status(self) -> bool: ...
