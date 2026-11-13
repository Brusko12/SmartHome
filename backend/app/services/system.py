from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import ValidationError
from sqlalchemy import func, or_, select, text, update

from app import __version__
from app.core.errors import InvalidCommand, NotFound
from app.database.base import utc_now
from app.database.transactions import write_transaction
from app.models import Device, DeviceState, EventLog, Room, Schedule
from app.repositories.entities import require_home
from app.schemas.settings import HomeSettings
from app.schemas.system import DatabaseStatus, EventPage, EventRead, SettingsRead, SystemStatus
from app.services.events import record_event
from app.services.schedules import next_occurrence


def get_settings(session, home_id, configuration):
    home = require_home(session, home_id)
    return SettingsRead(
        home_id=home.id,
        name=home.name,
        timezone=home.timezone,
        config=HomeSettings.model_validate(home.settings),
        version=__version__,
        database_path=str(configuration.database_path),
    )


def update_settings(session, home_id, payload, configuration):
    with write_transaction(session):
        home = require_home(session, home_id)
        changes = payload.model_dump(exclude_unset=True)
        if "timezone" in changes:
            try:
                ZoneInfo(changes["timezone"])
            except (ZoneInfoNotFoundError, ValueError) as error:
                raise InvalidCommand("Неизвестный часовой пояс.") from error
            home.timezone = changes["timezone"]
        if "name" in changes:
            home.name = changes["name"]
        if "config" in changes:
            if "demo_choice" in changes["config"]:
                raise InvalidCommand("Статус демонстрации меняется отдельной командой.")
            try:
                config = HomeSettings.model_validate({**home.settings, **changes["config"]})
            except ValidationError as error:
                raise InvalidCommand("Некорректные настройки симуляции или обновления.") from error
            home.settings = config.model_dump(mode="json")
            ids = select(Device.id).where(Device.home_id == home.id)
            session.execute(
                update(DeviceState)
                .where(DeviceState.device_id.in_(ids))
                .values(simulated_at=utc_now(), updated_at=DeviceState.updated_at)
            )
        if "timezone" in changes:
            for row in session.scalars(
                select(Schedule).where(Schedule.home_id == home.id, Schedule.enabled.is_(True))
            ):
                row.next_run_at = next_occurrence(
                    utc_now(), home.timezone, row.hour, row.minute, row.weekdays
                )
        record_event(
            session,
            home_id=home.id,
            event_type="settings.updated",
            description="Изменены настройки дома.",
        )
        session.flush()
        result = get_settings(session, home.id, configuration)
    return result


def list_events(
    session, home_id, device_id, event_type, date_from, date_to, order, limit, offset, status=None
):
    home = require_home(session, home_id)
    query = select(EventLog).where(EventLog.home_id == home_id)
    if device_id is not None:
        query = query.where(
            or_(
                EventLog.device_id == device_id,
                EventLog.details["device_id"].as_integer() == device_id,
            )
        )
    if event_type:
        query = query.where(EventLog.event_type == event_type)
    if status:
        query = query.where(EventLog.status == status)
    if date_from and date_to and date_from > date_to:
        raise InvalidCommand("Начальная дата должна быть не позже конечной.")
    zone = ZoneInfo(home.timezone)
    if date_from:
        query = query.where(
            EventLog.created_at >= datetime.combine(date_from, time.min, zone).astimezone(UTC)
        )
    if date_to:
        query = query.where(
            EventLog.created_at
            < datetime.combine(date_to + timedelta(days=1), time.min, zone).astimezone(UTC)
        )
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    sort = EventLog.created_at.desc() if order == "desc" else EventLog.created_at.asc()
    by_id = EventLog.id.desc() if order == "desc" else EventLog.id.asc()
    rows = session.scalars(query.order_by(sort, by_id).offset(offset).limit(limit)).all()
    return EventPage(
        items=[EventRead.model_validate(r) for r in rows], total=total, limit=limit, offset=offset
    )


def event(session, event_id):
    row = session.get(EventLog, event_id)
    if row is None:
        raise NotFound("Событие не найдено.")
    return EventRead.model_validate(row)


def event_types(session, home_id):
    require_home(session, home_id)
    return list(
        session.scalars(
            select(EventLog.event_type)
            .where(EventLog.home_id == home_id)
            .distinct()
            .order_by(EventLog.event_type)
        )
    )


def event_devices(session, home_id):
    require_home(session, home_id)
    identifier = func.coalesce(EventLog.device_id, EventLog.details["device_id"].as_integer())
    name = func.max(EventLog.details["device_name"].as_string())
    rows = session.execute(
        select(identifier, name)
        .where(EventLog.home_id == home_id)
        .group_by(identifier)
        .having(identifier.is_not(None))
    ).all()
    return [{"id": row[0], "name": row[1] or f"Устройство #{row[0]}"} for row in rows]


def database_status(session, configuration):
    integrity = session.execute(text("PRAGMA quick_check")).scalar_one()
    revision = session.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
    return DatabaseStatus(
        status="ok" if integrity == "ok" else "error",
        path=str(configuration.database_path),
        revision=revision,
        integrity=integrity,
    )


def system_status(session, state):
    def count(model):
        return session.scalar(select(func.count()).select_from(model))

    errors = session.scalars(
        select(EventLog).where(EventLog.status == "error").order_by(EventLog.id.desc()).limit(5)
    ).all()
    task = state.runtime_task
    return SystemStatus(
        backend="ok",
        version=__version__,
        started_at=state.started_at,
        database=database_status(session, state.configuration),
        rooms=count(Room),
        devices=count(Device),
        events=count(EventLog),
        runtime_running=bool(task and not task.done()),
        last_runtime_error=state.runtime.last_error,
        recent_errors=[EventRead.model_validate(e) for e in errors],
    )
