from datetime import date
from typing import Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.api.dependencies import SessionDep
from app.api.errors import ERROR_RESPONSES
from app.core.errors import Conflict
from app.schemas.system import (
    DatabaseStatus,
    EventPage,
    EventRead,
    SettingsPatch,
    SettingsRead,
    SystemStatus,
)
from app.services import system

router = APIRouter(tags=["system"], responses=ERROR_RESPONSES)


class ShutdownRead(BaseModel):
    stopping: bool


@router.post("/system/shutdown", response_model=ShutdownRead)
def shutdown(request: Request, session: SessionDep):
    callback = request.app.state.shutdown_callback
    if callback is None:
        raise Conflict("Этот сервер запущен в режиме разработки; завершите его в терминале.")
    callback()
    return {"stopping": True}


class EventDevice(BaseModel):
    id: int
    name: str


@router.get("/event-types", response_model=list[str])
def event_types(session: SessionDep, home_id: int = Query(gt=0)):
    return system.event_types(session, home_id)


@router.get("/event-devices", response_model=list[EventDevice])
def event_devices(session: SessionDep, home_id: int = Query(gt=0)):
    return system.event_devices(session, home_id)


@router.get("/settings", response_model=SettingsRead)
def settings(request: Request, session: SessionDep, home_id: int = Query(gt=0)):
    return system.get_settings(session, home_id, request.app.state.configuration)


@router.patch("/settings", response_model=SettingsRead)
def update_settings(
    payload: SettingsPatch, request: Request, session: SessionDep, home_id: int = Query(gt=0)
):
    return system.update_settings(session, home_id, payload, request.app.state.configuration)


@router.get("/events", response_model=EventPage)
def events(
    session: SessionDep,
    home_id: int = Query(gt=0),
    device_id: int | None = Query(default=None, gt=0),
    event_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Literal["success", "info", "error"] | None = None,
):
    return system.list_events(
        session, home_id, device_id, event_type, date_from, date_to, order, limit, offset, status
    )


@router.get("/events/{event_id}", response_model=EventRead)
def event(event_id: int, session: SessionDep):
    return system.event(session, event_id)


@router.get("/system/status", response_model=SystemStatus)
def status(request: Request, session: SessionDep):
    return system.system_status(session, request.app.state)


@router.get("/system/database", response_model=DatabaseStatus)
def database(request: Request, session: SessionDep):
    return system.database_status(session, request.app.state.configuration)
