from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.entities import DeviceType, InputModel

Percent = Annotated[int, Field(ge=0, le=100)]
Temperature = Annotated[float, Field(ge=-40, le=125)]
TargetTemperature = Annotated[float, Field(ge=5, le=35)]
Color = Annotated[str, StringConstraints(pattern=r"^#[0-9a-fA-F]{6}$")]
Mode = Literal["Off", "Heating", "Cooling", "Auto", "Eco"]


class EmptyParameters(InputModel):
    pass


class OutletParameters(InputModel):
    nominal_power_w: Annotated[float, Field(gt=0, le=10000)] = 60.0


class MotionParameters(InputModel):
    reset_after_seconds: Annotated[int, Field(ge=1, le=3600)] = 30


class LightState(InputModel):
    power: bool = False
    brightness: Percent = 100
    color: Color = "#FFFFFF"


class ThermostatState(InputModel):
    current_temperature: Temperature = 21.0
    target_temperature: TargetTemperature = 22.0
    mode: Mode = "Off"


class OutletState(InputModel):
    power: bool = False
    current_power_w: Annotated[float, Field(ge=0, le=10000)] = 0.0
    energy_kwh: Annotated[float, Field(ge=0)] = 0.0


class MotionState(InputModel):
    motion: bool = False
    last_motion_at: datetime | None = None
    reset_at: datetime | None = None


class ClimateState(InputModel):
    temperature: Temperature = 21.0
    humidity: Annotated[float, Field(ge=0, le=100)] = 45.0


class TVState(InputModel):
    power: bool = False
    volume: Percent = 20
    muted: bool = False


StateValues = LightState | ThermostatState | OutletState | MotionState | ClimateState | TVState

STATE_TYPES = {
    "light": LightState,
    "thermostat": ThermostatState,
    "outlet": OutletState,
    "motion_sensor": MotionState,
    "climate_sensor": ClimateState,
    "tv": TVState,
}


class StateRead(BaseModel):
    device_id: int
    device_type: DeviceType
    values: StateValues
    source: str
    updated_at: datetime


class DeviceRead(BaseModel):
    id: int
    home_id: int
    room_id: int
    name: str
    device_type: DeviceType
    adapter_type: str
    parameters: dict
    state: StateRead
    created_at: datetime
    updated_at: datetime


class DevicePage(BaseModel):
    items: list[DeviceRead]
    total: int
    limit: int
    offset: int


class BrightnessCommand(InputModel):
    brightness: Percent


class ColorCommand(InputModel):
    color: Color


class TemperatureCommand(InputModel):
    temperature: TargetTemperature


class ModeCommand(InputModel):
    mode: Mode


class VolumeCommand(InputModel):
    volume: Percent


class MuteCommand(InputModel):
    muted: bool


class ReadingCommand(InputModel):
    temperature: Temperature
    humidity: Annotated[float, Field(ge=0, le=100)]
