import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.registry import AdapterRegistry
from app.core.errors import DomainError, InvalidCommand, NotFound
from app.database.base import utc_now
from app.database.transactions import write_transaction
from app.models import Automation
from app.repositories.entities import require_device
from app.schemas.automations import (
    ActionResult,
    AutomationInput,
    CommandAction,
    DeviceTrigger,
    ExecutionResult,
    ThresholdTrigger,
)
from app.schemas.entities import CommandRequest
from app.services.automations import payload_dict, require_automation
from app.services.events import record_event

logger = logging.getLogger(__name__)


@dataclass
class Budget:
    remaining: int = 64


@dataclass
class ExecutionContext:
    path: tuple[int, ...] = ()
    budget: Budget = field(default_factory=Budget)
    source: str = "automation"


def conditions_match(session: Session, conditions) -> bool:
    for condition in conditions:
        try:
            device = require_device(session, condition.device_id)
        except DomainError:
            return False
        current = device.state.values.get(condition.field)
        target = condition.value
        if condition.op == "eq":
            match = type(current) is type(target) and current == target
            if type(current) in (int, float) and type(target) in (int, float):
                match = current == target
        elif condition.op == "ne":
            match = current != target
        elif type(current) not in (int, float) or type(target) not in (int, float):
            match = False
        elif condition.op == "gt":
            match = current > target
        elif condition.op == "lt":
            match = current < target
        else:
            match = condition.upper is not None and target <= current <= condition.upper
        if not match:
            return False
    return True


def execute(
    bind,
    adapters: AdapterRegistry,
    automation_id: int,
    reason="manual",
    context: ExecutionContext | None = None,
    run_at=None,
) -> ExecutionResult:
    context = context or ExecutionContext()
    result = ExecutionResult(automation_id=automation_id, status="skipped", reason=reason)
    with Session(bind=bind, expire_on_commit=False) as session, write_transaction(session):
        row = require_automation(session, automation_id)
        if automation_id in context.path or len(context.path) >= 8 or context.budget.remaining <= 0:
            result.status = "error"
            result.reason = "cycle_or_budget_limit"
            record_event(
                session,
                home_id=row.home_id,
                event_type="automation.blocked",
                status="error",
                source="automation",
                description="Остановлен цикл или превышен лимит действий.",
                details={"automation_id": row.id, "path": list(context.path)},
            )
            return result
        payload = AutomationInput.model_validate(payload_dict(row))
        if not row.enabled:
            result.reason = "disabled"
            return result
        if not conditions_match(session, payload.conditions):
            result.reason = "conditions_not_met"
            record_event(
                session,
                home_id=row.home_id,
                event_type="automation.skipped",
                source="automation",
                description=f"Условия «{row.name}» не выполнены.",
                details={"automation_id": row.id},
            )
            return result
        now = run_at or utc_now()
        if (
            reason.startswith("device:")
            and row.last_run_at
            and (now - row.last_run_at).total_seconds() < 1
        ):
            result.reason = "cooldown"
            return result
        row.last_run_at = now
        home_id, name = row.home_id, row.name
        record_event(
            session,
            home_id=home_id,
            event_type="automation.started",
            source="automation",
            description=f"Запуск «{name}».",
            details={"automation_id": row.id, "reason": reason, "path": list(context.path)},
        )
    child = ExecutionContext(context.path + (automation_id,), context.budget)
    result.actions, failed = perform_actions(
        bind, adapters, payload.actions, child, f"scenario:{automation_id}"
    )
    result.status = (
        ("partial" if any(r.status == "success" for r in result.actions) else "error")
        if failed
        else "success"
    )
    with Session(bind=bind) as session, write_transaction(session):
        record_event(
            session,
            home_id=home_id,
            event_type="automation.finished",
            source="automation",
            status="error" if failed else "success",
            description=f"Результат «{name}»: {result.status}.",
            details=result.model_dump(mode="json"),
        )
    return result


def trigger_matches(trigger, device_id: int, before: dict, after: dict) -> bool:
    if trigger is None or trigger.type == "time" or trigger.device_id != device_id:
        return False
    if isinstance(trigger, DeviceTrigger):
        if trigger.type == "motion":
            return after.get("motion") is True and (
                before.get("motion") is not True
                or before.get("last_motion_at") != after.get("last_motion_at")
            )
        return (
            before != after
            if trigger.field is None
            else before.get(trigger.field) != after.get(trigger.field)
        )
    if isinstance(trigger, ThresholdTrigger):
        old, new = before.get(trigger.field), after.get(trigger.field)
        if type(old) not in (int, float) or type(new) not in (int, float):
            return False
        return (
            old <= trigger.value < new
            if trigger.direction == "above"
            else old >= trigger.value > new
        )
    return False


def process_change(
    bind,
    adapters: AdapterRegistry,
    home_id: int,
    device_id: int,
    before: dict,
    after: dict,
    context: ExecutionContext | None = None,
):
    if before == after:
        return
    context = context or ExecutionContext()
    with Session(bind=bind) as session:
        ids = list(
            session.scalars(
                select(Automation.id)
                .where(
                    Automation.home_id == home_id,
                    Automation.kind == "rule",
                    Automation.enabled.is_(True),
                )
                .order_by(Automation.id)
            )
        )
    for automation_id in ids:
        try:
            with Session(bind=bind) as session:
                row = require_automation(session, automation_id)
                payload = AutomationInput.model_validate(payload_dict(row))
                match = trigger_matches(payload.trigger, device_id, before, after)
            if match:
                execute(bind, adapters, automation_id, f"device:{device_id}", context)
        except Exception:
            # The originating command has committed. A broken rule must not
            # turn a successful device command into a misleading HTTP error.
            logger.exception("Automatic rule failed", extra={"automation_id": automation_id})
            try:
                with Session(bind=bind) as session, write_transaction(session):
                    record_event(
                        session,
                        home_id=home_id,
                        event_type="automation.error",
                        source="automation",
                        status="error",
                        description="Ошибка автоматизации.",
                        details={"automation_id": automation_id, "device_id": device_id},
                    )
            except Exception:
                logger.exception("Could not persist automation failure")


def perform_actions(bind, adapters, actions, context=None, reason="schedule"):
    context = context or ExecutionContext()
    steps = []
    failed = False
    for index, action in enumerate(actions):
        if failed:
            steps.append(
                ActionResult(
                    index=index,
                    status="skipped",
                    message="Предыдущее действие завершилось ошибкой.",
                )
            )
            continue
        try:
            if context.budget.remaining <= 0:
                raise InvalidCommand("Превышен общий лимит 64 действий и запусков.")
            context.budget.remaining -= 1
            if isinstance(action, CommandAction):
                from app.services.devices import execute_command

                with Session(bind=bind, expire_on_commit=False) as session:
                    execute_command(
                        session,
                        adapters,
                        action.device_id,
                        CommandRequest(command=action.command, params=action.params),
                        context=context,
                    )
            else:
                nested = execute(bind, adapters, action.automation_id, reason, context)
                if nested.status != "success":
                    raise InvalidCommand(f"Вложенный сценарий: {nested.reason} ({nested.status}).")
            steps.append(ActionResult(index=index, status="success"))
        except NotFound as error:
            if action.optional:
                steps.append(ActionResult(index=index, status="skipped", message=str(error)))
            else:
                failed = True
                steps.append(ActionResult(index=index, status="error", message=str(error)))
        except DomainError as error:
            failed = True
            steps.append(ActionResult(index=index, status="error", message=str(error)))
        except Exception:
            logger.exception("Automation action failed")
            failed = True
            steps.append(
                ActionResult(
                    index=index,
                    status="error",
                    message="Ошибка выполнения действия; подробности в журнале сервера.",
                )
            )
    return steps, failed
