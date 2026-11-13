from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.errors import Conflict, InvalidCommand, NotFound
from app.database.base import utc_now
from app.database.transactions import write_transaction
from app.models import Schedule
from app.repositories.entities import require_home
from app.schemas.automations import AutomationInput
from app.schemas.schedules import ScheduleInput, SchedulePage, SchedulePatch, ScheduleRead
from app.services.automations import require_automation, validate_definition
from app.services.events import record_event


def next_occurrence(
    after: datetime, timezone: str, hour: int, minute: int, weekdays: list[int]
) -> datetime:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise InvalidCommand("Неизвестный часовой пояс дома.") from error
    local = after.astimezone(zone)
    for offset in range(9):
        date = (local + timedelta(days=offset)).date()
        if date.weekday() not in weekdays:
            continue
        wall = datetime(date.year, date.month, date.day, hour, minute)
        candidates = []
        for fold in (0, 1):
            candidate = wall.replace(tzinfo=zone, fold=fold).astimezone(UTC)
            if candidate.astimezone(zone).replace(tzinfo=None) == wall:
                candidates.append(candidate)
        # Execute an ambiguous wall-clock time only once, at its first occurrence.
        if candidates and min(candidates) > after:
            return min(candidates)
    raise InvalidCommand("Не удалось вычислить следующее выполнение.")


def require_schedule(session, schedule_id):
    row = session.get(Schedule, schedule_id)
    if row is None:
        raise NotFound("Расписание не найдено.")
    return row


def data(row):
    return {k: getattr(row, k) for k in ScheduleInput.model_fields}


def response(row):
    return ScheduleRead(
        **data(row), id=row.id, last_run_at=row.last_run_at, next_run_at=row.next_run_at
    )


def validate(session, adapters, payload):
    home = require_home(session, payload.home_id)
    if payload.automation_id is not None:
        target = require_automation(session, payload.automation_id)
        if target.home_id != home.id or target.kind != "scenario":
            raise Conflict("Расписание может запускать сценарий этого дома.")
    else:
        validate_definition(
            session,
            adapters,
            AutomationInput(
                home_id=home.id, name=payload.name, kind="scenario", actions=payload.actions
            ),
        )
    return home


def create(session, adapters, payload: ScheduleInput):
    with write_transaction(session):
        home = validate(session, adapters, payload)
        row = Schedule(**payload.model_dump(mode="json"))
        if row.enabled:
            row.next_run_at = next_occurrence(
                utc_now(), home.timezone, row.hour, row.minute, row.weekdays
            )
        session.add(row)
        session.flush()
        record_event(
            session,
            home_id=home.id,
            event_type="schedule.created",
            description=f"Создано расписание «{row.name}».",
        )
        result = response(row)
    return result


def update(session, adapters, schedule_id, patch: SchedulePatch):
    with write_transaction(session):
        row = require_schedule(session, schedule_id)
        try:
            payload = ScheduleInput.model_validate(
                {**data(row), **patch.model_dump(mode="json", exclude_unset=True)}
            )
        except ValidationError as error:
            raise InvalidCommand("Некорректное расписание.") from error
        home = require_home(session, row.home_id)
        if patch.model_fields_set - {"name", "enabled"} or patch.enabled is True:
            validate(session, adapters, payload)
        for key, value in payload.model_dump(mode="json").items():
            setattr(row, key, value)
        row.next_run_at = (
            next_occurrence(utc_now(), home.timezone, row.hour, row.minute, row.weekdays)
            if row.enabled
            else None
        )
        session.flush()
        record_event(
            session,
            home_id=home.id,
            event_type="schedule.updated",
            description=f"Изменено расписание «{row.name}».",
        )
        result = response(row)
    return result


def remove(session, schedule_id):
    with write_transaction(session):
        row = require_schedule(session, schedule_id)
        record_event(
            session,
            home_id=row.home_id,
            event_type="schedule.deleted",
            description=f"Удалено расписание «{row.name}».",
        )
        session.delete(row)


def list_rows(session, home_id, limit, offset):
    require_home(session, home_id)
    query = select(Schedule).where(Schedule.home_id == home_id)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    return SchedulePage(
        items=[
            response(r)
            for r in session.scalars(query.order_by(Schedule.id).offset(offset).limit(limit))
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
