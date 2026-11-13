from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.schemas.automations import Action
from app.schemas.entities import EntityId, InputModel, Name
from app.schemas.json_data import WeekdaysJSON


class ScheduleInput(InputModel):
    home_id: EntityId
    name: Name
    enabled: bool = False
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    weekdays: list[int] = Field(min_length=1)
    automation_id: EntityId | None = None
    actions: list[Action] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def valid_target(self) -> Self:
        self.weekdays = WeekdaysJSON().adapter.validate_python(self.weekdays)
        if (self.automation_id is not None) == bool(self.actions):
            raise ValueError("Выберите сценарий или собственные действия.")
        return self


class SchedulePatch(InputModel):
    name: Name | None = None
    enabled: bool | None = None
    hour: int | None = Field(default=None, ge=0, le=23)
    minute: int | None = Field(default=None, ge=0, le=59)
    weekdays: list[int] | None = None
    automation_id: EntityId | None = None
    actions: list[Action] | None = None

    @model_validator(mode="after")
    def changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Укажите изменяемые поля.")
        if any(getattr(self, k) is None for k in self.model_fields_set - {"automation_id"}):
            raise ValueError("Изменяемое поле не может быть null.")
        return self


class ScheduleRead(ScheduleInput):
    id: int
    last_run_at: datetime | None
    next_run_at: datetime | None


class SchedulePage(BaseModel):
    items: list[ScheduleRead]
    total: int
    limit: int
    offset: int
