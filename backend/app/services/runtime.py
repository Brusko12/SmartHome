import asyncio
import logging
from contextlib import nullcontext
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.orm.attributes import flag_modified

from app.database.base import utc_now
from app.database.transactions import write_transaction
from app.models import Automation, Device, DeviceState, Home, Schedule
from app.schemas.automations import AutomationInput, TimeTrigger
from app.schemas.schedules import ScheduleInput
from app.schemas.settings import HomeSettings
from app.services import automation_engine
from app.services.automations import payload_dict
from app.services.devices import snapshot
from app.services.events import record_event
from app.services.schedules import data, next_occurrence
from app.services.simulation import advance

logger = logging.getLogger(__name__)


class RuntimeWorker:
    def __init__(self, database, adapters, started_at: datetime | None = None, gate=None):
        self.database = database
        self.adapters = adapters
        self.started_at = started_at or utc_now()
        self.last_home_tick = {}
        self.last_error = None
        self.gate = gate

    def recover(self, now):
        with self.database.sessions() as session, write_transaction(session):
            session.execute(
                update(DeviceState).values(simulated_at=now, updated_at=DeviceState.updated_at)
            )
            for row in session.scalars(select(Schedule).where(Schedule.enabled.is_(True))):
                home = session.get(Home, row.home_id)
                row.next_run_at = next_occurrence(
                    now, home.timezone, row.hour, row.minute, row.weekdays
                )

    def tick(self, now):
        self.simulate(now)
        self.run_schedules(now)
        self.run_time_rules(now)

    def simulate(self, now):
        changes = []
        with self.database.sessions() as session, write_transaction(session):
            for home in session.scalars(select(Home)):
                config = HomeSettings.model_validate(home.settings)
                previous = self.last_home_tick.get(home.id, self.started_at)
                elapsed = max(0, (now - previous).total_seconds())
                if config.simulation_enabled and elapsed < config.simulation_interval:
                    continue
                self.last_home_tick[home.id] = now
                for device in session.scalars(
                    select(Device).where(
                        Device.home_id == home.id, Device.adapter_type == "virtual"
                    )
                ):
                    if device.state is None:
                        continue
                    before = self.adapters.get(device.adapter_type).get_state(snapshot(device))
                    anchor = device.state.simulated_at or previous
                    after = advance(
                        device.device_type,
                        device.id,
                        before,
                        max(0, (now - anchor).total_seconds()),
                        now,
                        config,
                    )
                    old_updated = device.state.updated_at
                    device.state.simulated_at = now
                    if after != before:
                        device.state.values = after
                        device.state.updated_at = now
                        device.updated_at = now
                        device.state.source = "simulation"
                        record_event(
                            session,
                            home_id=home.id,
                            device_id=device.id,
                            event_type="device.simulated",
                            source="simulation",
                            description=f"Изменение виртуального устройства «{device.name}».",
                            details={"device_name": device.name, "before": before, "after": after},
                        )
                        changes.append((home.id, device.id, before, after))
                    else:
                        device.state.updated_at = old_updated
                        flag_modified(device.state, "updated_at")
        for home_id, device_id, before, after in changes:
            automation_engine.process_change(
                self.database.engine, self.adapters, home_id, device_id, before, after
            )

    def run_schedules(self, now):
        jobs = []
        with self.database.sessions() as session, write_transaction(session):
            for row in session.scalars(
                select(Schedule).where(Schedule.enabled.is_(True), Schedule.next_run_at <= now)
            ):
                home = session.get(Home, row.home_id)
                payload = ScheduleInput.model_validate(data(row))
                due = row.next_run_at
                row.last_run_at = due
                row.next_run_at = next_occurrence(
                    now, home.timezone, row.hour, row.minute, row.weekdays
                )
                record_event(
                    session,
                    home_id=home.id,
                    event_type="schedule.started",
                    source="schedule",
                    description=f"Запуск расписания «{row.name}».",
                    details={"schedule_id": row.id, "due_at": due.isoformat()},
                )
                jobs.append((row.id, home.id, payload))
        for schedule_id, home_id, payload in jobs:
            try:
                if payload.automation_id is not None:
                    result = automation_engine.execute(
                        self.database.engine,
                        self.adapters,
                        payload.automation_id,
                        f"schedule:{schedule_id}",
                    ).model_dump(mode="json")
                    failed = result["status"] not in {"success", "skipped"}
                else:
                    steps, failed = automation_engine.perform_actions(
                        self.database.engine,
                        self.adapters,
                        payload.actions,
                        automation_engine.ExecutionContext(source="schedule"),
                        f"schedule:{schedule_id}",
                    )
                    result = {"actions": [s.model_dump(mode="json") for s in steps]}
                with self.database.sessions() as session, write_transaction(session):
                    record_event(
                        session,
                        home_id=home_id,
                        event_type="schedule.finished",
                        source="schedule",
                        status="error" if failed else "success",
                        description=f"Завершено расписание «{payload.name}».",
                        details={"schedule_id": schedule_id, **result},
                    )
            except Exception:
                logger.exception("Schedule execution failed")
                with self.database.sessions() as session, write_transaction(session):
                    record_event(
                        session,
                        home_id=home_id,
                        event_type="schedule.error",
                        source="schedule",
                        status="error",
                        description="Ошибка выполнения расписания.",
                        details={"schedule_id": schedule_id},
                    )

    def run_time_rules(self, now):
        jobs = []
        with self.database.sessions() as session:
            for row in session.scalars(
                select(Automation).where(Automation.enabled.is_(True), Automation.kind == "rule")
            ):
                payload = AutomationInput.model_validate(payload_dict(row))
                trigger = payload.trigger
                if not isinstance(trigger, TimeTrigger):
                    continue
                home = session.get(Home, row.home_id)
                zone = ZoneInfo(home.timezone)
                local = now.astimezone(zone)
                if local.weekday() not in trigger.weekdays or (local.hour, local.minute) != (
                    trigger.hour,
                    trigger.minute,
                ):
                    continue
                if now.replace(second=0, microsecond=0) < self.started_at:
                    continue
                last = row.last_run_at.astimezone(zone) if row.last_run_at else None
                if last and (last.date(), last.hour, last.minute) == (
                    local.date(),
                    local.hour,
                    local.minute,
                ):
                    continue
                jobs.append(row.id)
        for automation_id in jobs:
            automation_engine.execute(
                self.database.engine, self.adapters, automation_id, "clock", run_at=now
            )

    async def run(self, stop: asyncio.Event):
        while not stop.is_set():
            try:
                await asyncio.to_thread(self.locked_tick)
            except Exception as error:
                self.last_error = type(error).__name__
                logger.exception("Background runtime tick failed")
            try:
                await asyncio.wait_for(stop.wait(), timeout=0.5)
            except TimeoutError:
                pass

    def locked_tick(self):
        with self.gate if self.gate is not None else nullcontext():
            self.tick(utc_now())
