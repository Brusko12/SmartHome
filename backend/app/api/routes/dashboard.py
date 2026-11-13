from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.api.dependencies import SessionDep
from app.schemas.settings import HomeSettings
from app.services import dashboard as service

router = APIRouter(tags=["dashboard"])


class HomeRead(BaseModel):
    id: int
    name: str
    timezone: str
    settings: HomeSettings = Field(default_factory=HomeSettings)


class RecentEvent(BaseModel):
    id: int
    description: str
    status: str
    created_at: str


class DashboardRead(BaseModel):
    home: HomeRead
    rooms: int
    devices: int
    powered_devices: int
    active_automations: int
    temperature: float | None
    recent_events: list[RecentEvent]


@router.get("/homes", response_model=list[HomeRead])
def homes(session: SessionDep):
    return service.homes(session)


@router.get("/dashboard", response_model=DashboardRead)
def dashboard(session: SessionDep, home_id: int = Query(gt=0)):
    return service.dashboard(session, home_id)
