from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, JsonValue, model_validator

from app.schemas.entities import EntityId, InputModel, Name
from app.schemas.json_data import WeekdaysJSON


class CommandAction(InputModel):
    type: Literal["command"] = "command"
    device_id: EntityId
    command: str = Field(min_length=1, max_length=64)
    params: dict[str, JsonValue] = Field(default_factory=dict)
    optional: bool = False


class ScenarioAction(InputModel):
    type: Literal["scenario"]
    automation_id: EntityId
    optional: bool = False


Action = Annotated[CommandAction | ScenarioAction, Field(discriminator="type")]


class DeviceTrigger(InputModel):
    type: Literal["state_changed", "motion"]
    device_id: EntityId
    field: str | None = None


class ThresholdTrigger(InputModel):
    type: Literal["threshold"]
    device_id: EntityId
    field: str
    direction: Literal["above", "below"]
    value: float


class TimeTrigger(InputModel):
    type: Literal["time"]
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    weekdays: list[int] = Field(default_factory=lambda: list(range(7)))

    @model_validator(mode="after")
    def days(self) -> Self:
        self.weekdays = WeekdaysJSON().adapter.validate_python(self.weekdays)
        return self


Trigger = Annotated[DeviceTrigger | ThresholdTrigger | TimeTrigger, Field(discriminator="type")]


class Condition(InputModel):
    device_id: EntityId
    field: str
    op: Literal["eq", "ne", "gt", "lt", "between"]
    value: JsonValue
    upper: float | None = None


class AutomationInput(InputModel):
    home_id: EntityId
    name: Name
    kind: Literal["scenario", "rule"]
    enabled: bool = False
    trigger: Trigger | None = None
    conditions: list[Condition] = Field(default_factory=list, max_length=32)
    actions: list[Action] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def kind_matches_trigger(self) -> Self:
        if (self.kind == "rule") != (self.trigger is not None):
            raise ValueError("Правилу нужен триггер; ручной сценарий не имеет триггера.")
        return self


class AutomationPatch(InputModel):
    name: Name | None = None
    kind: Literal["scenario", "rule"] | None = None
    enabled: bool | None = None
    trigger: Trigger | None = None
    conditions: list[Condition] | None = None
    actions: list[Action] | None = None

    @model_validator(mode="after")
    def changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Укажите изменяемые поля.")
        if any(getattr(self, name) is None for name in self.model_fields_set - {"trigger"}):
            raise ValueError("Изменяемое поле не может быть null.")
        return self


class AutomationRead(AutomationInput):
    id: int
    last_run_at: datetime | None
    updated_at: datetime


class AutomationPage(BaseModel):
    items: list[AutomationRead]
    total: int
    limit: int
    offset: int


class ActionResult(BaseModel):
    index: int
    status: Literal["success", "error", "skipped"]
    message: str = ""


class ExecutionResult(BaseModel):
    automation_id: int
    status: Literal["success", "partial", "error", "skipped"]
    reason: str
    actions: list[ActionResult] = Field(default_factory=list)
