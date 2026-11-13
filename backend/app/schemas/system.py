from datetime import datetime

from pydantic import BaseModel, JsonValue

from app.schemas.entities import Name, PatchModel
from app.schemas.settings import HomeSettings


class SettingsRead(BaseModel):
    home_id: int
    name: str
    timezone: str
    config: HomeSettings
    version: str
    database_path: str


class SettingsPatch(PatchModel):
    name: Name | None = None
    timezone: str | None = None
    config: dict[str, JsonValue] | None = None


class EventRead(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    home_id: int
    device_id: int | None
    event_type: str
    source: str
    status: str
    description: str
    details: dict[str, JsonValue]
    created_at: datetime


class EventPage(BaseModel):
    items: list[EventRead]
    total: int
    limit: int
    offset: int


class DatabaseStatus(BaseModel):
    status: str
    path: str
    revision: str | None
    integrity: str


class SystemStatus(BaseModel):
    backend: str
    version: str
    started_at: datetime
    database: DatabaseStatus
    rooms: int
    devices: int
    events: int
    runtime_running: bool
    last_runtime_error: str | None
    recent_errors: list[EventRead]
    can_shutdown: bool


class ConfirmInput(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    confirm: bool
