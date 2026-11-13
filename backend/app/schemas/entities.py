from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator

Name = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=200, pattern=r"^[^\x00-\x1f\x7f]+$"
    ),
]
EntityId = Annotated[int, Field(strict=True, gt=0)]
DeviceType = Literal["light", "thermostat", "outlet", "motion_sensor", "climate_sensor", "tv"]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class RoomCreate(InputModel):
    home_id: EntityId
    name: Name
    icon: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]{0,63}$")] = "house"


class PatchModel(InputModel):
    @model_validator(mode="after")
    def nonempty_without_nulls(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Укажите хотя бы одно изменяемое поле.")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Изменяемые поля не могут быть null.")
        return self


class RoomPatch(PatchModel):
    name: Name | None = None
    icon: Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]{0,63}$")] | None = None


class RoomRead(BaseModel):
    id: int
    home_id: int
    name: str
    icon: str
    device_count: int
    created_at: datetime
    updated_at: datetime


class RoomPage(BaseModel):
    items: list[RoomRead]
    total: int
    limit: int
    offset: int


class DeviceCreate(InputModel):
    room_id: EntityId
    name: Name
    device_type: DeviceType
    parameters: dict[str, JsonValue] = Field(default_factory=dict)


class DevicePatch(PatchModel):
    name: Name | None = None
    room_id: EntityId | None = None
    parameters: dict[str, JsonValue] | None = None


class CommandRequest(InputModel):
    command: Annotated[str, StringConstraints(min_length=1, max_length=64)]
    params: dict[str, JsonValue] = Field(default_factory=dict)
