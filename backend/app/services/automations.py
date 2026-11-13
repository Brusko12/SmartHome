from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.registry import AdapterRegistry
from app.core.errors import Conflict, InvalidCommand, NotFound
from app.database.transactions import write_transaction
from app.models import Automation, Schedule
from app.repositories.entities import require_device, require_home
from app.schemas.automations import (
    AutomationInput,
    AutomationPage,
    AutomationPatch,
    AutomationRead,
    CommandAction,
    DeviceTrigger,
    ScenarioAction,
    ThresholdTrigger,
)
from app.schemas.devices import STATE_TYPES
from app.services.events import record_event


def require_automation(session: Session, automation_id: int) -> Automation:
    row = session.get(Automation, automation_id)
    if row is None:
        raise NotFound("Сценарий или автоматизация не найдены.")
    return row


def payload_dict(row: Automation) -> dict:
    return {key: getattr(row, key) for key in AutomationInput.model_fields}


def response(row: Automation) -> AutomationRead:
    return AutomationRead(
        **payload_dict(row), id=row.id, last_run_at=row.last_run_at, updated_at=row.updated_at
    )


def validate_definition(session: Session, adapters: AdapterRegistry, payload: AutomationInput):
    require_home(session, payload.home_id)

    def device(device_id):
        row = require_device(session, device_id)
        if row.home_id != payload.home_id:
            raise Conflict("Все устройства правила должны принадлежать его дому.")
        return row

    for action in payload.actions:
        if isinstance(action, CommandAction):
            try:
                row = device(action.device_id)
            except NotFound:
                if action.optional:
                    continue
                raise
            adapters.get(row.adapter_type).validate_command(
                row.device_type, action.command, action.params
            )
        elif isinstance(action, ScenarioAction):
            target = require_automation(session, action.automation_id)
            if target.home_id != payload.home_id or target.kind != "scenario":
                raise Conflict("Действие может запускать только сценарий этого дома.")
    for condition in payload.conditions:
        row = device(condition.device_id)
        defaults = STATE_TYPES[row.device_type]().model_dump(mode="json")
        if condition.field not in defaults:
            raise InvalidCommand("Условие использует неизвестный параметр состояния.")
        current = defaults[condition.field]
        if condition.op in {"gt", "lt", "between"}:
            if type(current) not in (float, int) or type(condition.value) not in (float, int):
                raise InvalidCommand("Числовое условие требует числовой параметр и порог.")
            if condition.op == "between" and (
                condition.upper is None or condition.upper < condition.value
            ):
                raise InvalidCommand("Укажите корректную верхнюю границу диапазона.")
        elif type(condition.value) is not type(current) and not (
            type(current) is float and type(condition.value) in (float, int)
        ):
            raise InvalidCommand("Тип значения условия не соответствует параметру устройства.")
    trigger = payload.trigger
    if isinstance(trigger, (DeviceTrigger, ThresholdTrigger)):
        row = device(trigger.device_id)
        defaults = STATE_TYPES[row.device_type]().model_dump(mode="json")
        if trigger.type == "motion" and row.device_type != "motion_sensor":
            raise InvalidCommand("Триггер движения требует датчик движения.")
        if trigger.field is not None and trigger.field not in defaults:
            raise InvalidCommand("Триггер использует неизвестный параметр.")
        if isinstance(trigger, ThresholdTrigger) and type(defaults[trigger.field]) not in (
            int,
            float,
        ):
            raise InvalidCommand("Пересечение порога требует числовой параметр.")


def create(session: Session, adapters: AdapterRegistry, payload: AutomationInput) -> AutomationRead:
    with write_transaction(session):
        validate_definition(session, adapters, payload)
        row = Automation(**payload.model_dump(mode="json"))
        session.add(row)
        session.flush()
        record_event(
            session,
            home_id=row.home_id,
            event_type="automation.created",
            description=f"Создано правило/сценарий «{row.name}».",
            details={"automation_id": row.id},
        )
        result = response(row)
    return result


def update(session: Session, adapters: AdapterRegistry, automation_id: int, patch: AutomationPatch):
    with write_transaction(session):
        row = require_automation(session, automation_id)
        try:
            payload = AutomationInput.model_validate(
                {**payload_dict(row), **patch.model_dump(mode="json", exclude_unset=True)}
            )
        except ValidationError as error:
            raise InvalidCommand("Некорректная конфигурация правила или сценария.") from error
        if patch.model_fields_set - {"name", "enabled"} or patch.enabled is True:
            validate_definition(session, adapters, payload)
        for key, value in payload.model_dump(mode="json").items():
            setattr(row, key, value)
        session.flush()
        record_event(
            session,
            home_id=row.home_id,
            event_type="automation.updated",
            description=f"Изменено правило/сценарий «{row.name}».",
            details={"automation_id": row.id},
        )
        result = response(row)
    return result


def remove(session: Session, automation_id: int):
    with write_transaction(session):
        row = require_automation(session, automation_id)
        if session.scalar(select(Schedule.id).where(Schedule.automation_id == row.id).limit(1)):
            raise Conflict("Сначала удалите связанные расписания.")
        record_event(
            session,
            home_id=row.home_id,
            event_type="automation.deleted",
            description=f"Удалено правило/сценарий «{row.name}».",
            details={"automation_id": row.id},
        )
        session.delete(row)


def list_rows(session: Session, home_id: int, kind: str | None, limit: int, offset: int):
    require_home(session, home_id)
    query = select(Automation).where(Automation.home_id == home_id)
    if kind is not None:
        query = query.where(Automation.kind == kind)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rows = session.scalars(query.order_by(Automation.id).offset(offset).limit(limit)).all()
    return AutomationPage(
        items=[response(row) for row in rows], total=total, limit=limit, offset=offset
    )
