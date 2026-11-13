from fastapi import APIRouter, Query, Response

from app.api.dependencies import AdaptersDep, SessionDep
from app.api.errors import ERROR_RESPONSES
from app.schemas.schedules import ScheduleInput, SchedulePage, SchedulePatch, ScheduleRead
from app.services import schedules

router = APIRouter(prefix="/schedules", tags=["schedules"], responses=ERROR_RESPONSES)


@router.get("", response_model=SchedulePage)
def list_rows(
    session: SessionDep,
    home_id: int = Query(gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return schedules.list_rows(session, home_id, limit, offset)


@router.post("", response_model=ScheduleRead, status_code=201)
def create(payload: ScheduleInput, session: SessionDep, adapters: AdaptersDep):
    return schedules.create(session, adapters, payload)


@router.get("/{schedule_id}", response_model=ScheduleRead)
def get(schedule_id: int, session: SessionDep):
    return schedules.response(schedules.require_schedule(session, schedule_id))


@router.patch("/{schedule_id}", response_model=ScheduleRead)
def update(schedule_id: int, payload: SchedulePatch, session: SessionDep, adapters: AdaptersDep):
    return schedules.update(session, adapters, schedule_id, payload)


@router.delete("/{schedule_id}", status_code=204)
def remove(schedule_id: int, session: SessionDep):
    schedules.remove(session, schedule_id)
    return Response(status_code=204)
