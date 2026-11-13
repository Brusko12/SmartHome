import json
from datetime import datetime, timedelta

from pydantic import ValidationError

from app.adapters.contracts import DeviceSnapshot
from app.core.errors import InvalidCommand, Unavailable
from app.schemas.devices import (
    STATE_TYPES,
    BrightnessCommand,
    ColorCommand,
    EmptyParameters,
    ModeCommand,
    MotionParameters,
    MuteCommand,
    OutletParameters,
    ReadingCommand,
    TemperatureCommand,
    VolumeCommand,
)

PARAMETER_TYPES = {"outlet": OutletParameters, "motion_sensor": MotionParameters}
COMMANDS = {
    "light": {"turn_on", "turn_off", "set_brightness", "set_color"},
    "thermostat": {"set_target_temperature", "set_mode"},
    "outlet": {"turn_on", "turn_off"},
    "motion_sensor": {"simulate_motion", "reset_motion"},
    "climate_sensor": {"simulate_reading"},
    "tv": {"turn_on", "turn_off", "set_volume", "mute"},
}
COMMAND_PARAMETERS = {
    "set_brightness": BrightnessCommand,
    "set_color": ColorCommand,
    "set_target_temperature": TemperatureCommand,
    "set_mode": ModeCommand,
    "set_volume": VolumeCommand,
    "mute": MuteCommand,
    "simulate_reading": ReadingCommand,
}


class VirtualDeviceAdapter:
    """Deterministic commands. Periodic simulation is a separate stage 5 service."""

    def __init__(self) -> None:
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def get_connection_status(self) -> bool:
        return self._connected

    def _require_connection(self) -> None:
        if not self._connected:
            raise Unavailable("Виртуальный адаптер не подключён.")

    def validate_parameters(self, device_type: str, parameters: dict) -> dict:
        self._require_connection()
        if device_type not in STATE_TYPES:
            raise InvalidCommand("Неподдерживаемый тип устройства.")
        schema = PARAMETER_TYPES.get(device_type, EmptyParameters)
        try:
            return schema.model_validate(parameters).model_dump(mode="json")
        except ValidationError as error:
            raise InvalidCommand(
                "Некорректные или неподдерживаемые параметры устройства."
            ) from error

    def initial_state(self, device_type: str) -> dict:
        self._require_connection()
        if device_type not in STATE_TYPES:
            raise InvalidCommand("Неподдерживаемый тип устройства.")
        return STATE_TYPES[device_type]().model_dump(mode="json")

    def get_state(self, device: DeviceSnapshot) -> dict:
        self._require_connection()
        if device.device_type not in STATE_TYPES:
            raise InvalidCommand("Неподдерживаемый тип устройства.")
        try:
            state = (
                STATE_TYPES[device.device_type]
                .model_validate_json(json.dumps(device.values, allow_nan=False))
                .model_dump(mode="json")
            )
        except (ValidationError, ValueError, TypeError) as error:
            raise InvalidCommand("Сохранённое состояние устройства некорректно.") from error
        if device.device_type == "outlet":
            parameters = self.validate_parameters(device.device_type, device.parameters)
            state["current_power_w"] = parameters["nominal_power_w"] if state["power"] else 0.0
        return state

    def execute_command(
        self, device: DeviceSnapshot, command: str, params: dict, now: datetime
    ) -> dict:
        state = self.get_state(device)
        if command not in COMMANDS.get(device.device_type, set()):
            raise InvalidCommand("Команда не поддерживается этим типом устройства.")
        schema = COMMAND_PARAMETERS.get(command, EmptyParameters)
        try:
            values = schema.model_validate(params).model_dump(mode="json")
        except ValidationError as error:
            raise InvalidCommand("Некорректные или неподдерживаемые параметры команды.") from error
        if command in {"turn_on", "turn_off"}:
            state["power"] = command == "turn_on"
        elif command == "set_brightness":
            state["brightness"] = values["brightness"]
        elif command == "set_color":
            state["color"] = values["color"].upper()
        elif command == "set_target_temperature":
            state["target_temperature"] = values["temperature"]
        elif command == "set_mode":
            state["mode"] = values["mode"]
        elif command == "set_volume":
            state["volume"] = values["volume"]
        elif command == "mute":
            state["muted"] = values["muted"]
        elif command == "simulate_reading":
            state.update(values)
        elif command == "simulate_motion":
            parameters = self.validate_parameters(device.device_type, device.parameters)
            state.update(
                {
                    "motion": True,
                    "last_motion_at": now.isoformat(),
                    "reset_at": (
                        now + timedelta(seconds=parameters["reset_after_seconds"])
                    ).isoformat(),
                }
            )
        elif command == "reset_motion":
            state.update({"motion": False, "reset_at": None})
        return self.get_state(
            DeviceSnapshot(device.device_id, device.device_type, device.parameters, state)
        )
