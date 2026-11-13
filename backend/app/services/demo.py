from sqlalchemy import select

from app.database.base import utc_now
from app.database.transactions import write_transaction
from app.models import Automation, Device, DeviceState, Room, Schedule
from app.repositories.entities import require_home
from app.schemas.automations import AutomationInput
from app.schemas.settings import HomeSettings
from app.services.automations import validate_definition
from app.services.events import record_event
from app.services.schedules import next_occurrence


def seed(session, adapters, home_id):
    with write_transaction(session):
        home = require_home(session, home_id)
        config = HomeSettings.model_validate(home.settings)
        if config.demo_choice == "created":
            return {"created": False, "message": "Демонстрационный дом уже создан."}
        adapter = adapters.get("virtual")
        rooms = {}
        devices = {}
        definitions = [
            (
                "Гостиная",
                "sofa",
                [
                    ("light", "Основная лампа"),
                    ("tv", "Телевизор"),
                    ("motion_sensor", "Датчик движения"),
                    ("thermostat", "Термостат"),
                ],
            ),
            (
                "Спальня",
                "bed",
                [
                    ("light", "Основная лампа"),
                    ("light", "Ночная лампа"),
                    ("climate_sensor", "Датчик температуры и влажности"),
                ],
            ),
            ("Кухня", "cooking-pot", [("outlet", "Умная розетка"), ("light", "Лампа")]),
            (
                "Ванная",
                "bath",
                [("light", "Лампа"), ("climate_sensor", "Датчик температуры и влажности")],
            ),
        ]
        for name, icon, specs in definitions:
            room = session.scalar(select(Room).where(Room.home_id == home_id, Room.name == name))
            if room is None:
                room = Room(home_id=home_id, name=name, icon=icon)
                session.add(room)
                session.flush()
            rooms[name] = room
            for index, (kind, device_name) in enumerate(specs):
                device = Device(
                    home_id=home_id,
                    room_id=room.id,
                    name=device_name,
                    device_type=kind,
                    adapter_type="virtual",
                    parameters=adapter.validate_parameters(kind, {}),
                )
                device.state = DeviceState(values=adapter.initial_state(kind))
                session.add(device)
                session.flush()
                devices[(name, index)] = device

        def command(key, name, params=None):
            return {
                "type": "command",
                "device_id": devices[key].id,
                "command": name,
                "params": params or {},
                "optional": True,
            }

        lamps = [key for key, d in devices.items() if d.device_type == "light"]
        away = [command(key, "turn_off") for key in lamps] + [
            command(("Кухня", 0), "turn_off"),
            command(("Гостиная", 3), "set_mode", {"mode": "Eco"}),
        ]
        morning = [
            command(("Спальня", 0), "turn_on"),
            command(("Спальня", 0), "set_brightness", {"brightness": 60}),
            command(("Гостиная", 3), "set_mode", {"mode": "Auto"}),
            command(("Гостиная", 3), "set_target_temperature", {"temperature": 22}),
        ]
        night = [command(key, "turn_off") for key in lamps if key != ("Спальня", 1)] + [
            command(("Спальня", 1), "turn_on"),
            command(("Спальня", 1), "set_brightness", {"brightness": 15}),
            command(("Гостиная", 3), "set_mode", {"mode": "Eco"}),
        ]
        scenarios = {}
        for name, actions in [("Я ушёл", away), ("Доброе утро", morning), ("Ночной режим", night)]:
            payload = AutomationInput(
                home_id=home_id, name=name, kind="scenario", enabled=True, actions=actions
            )
            validate_definition(session, adapters, payload)
            row = Automation(**payload.model_dump(mode="json"))
            session.add(row)
            session.flush()
            scenarios[name] = row
        lamp = devices[("Гостиная", 0)]
        motion = devices[("Гостиная", 2)]
        rule = AutomationInput(
            home_id=home_id,
            name="Движение в гостиной",
            kind="rule",
            enabled=True,
            trigger={"type": "motion", "device_id": motion.id},
            conditions=[{"device_id": lamp.id, "field": "power", "op": "eq", "value": False}],
            actions=[command(("Гостиная", 0), "turn_on")],
        )
        validate_definition(session, adapters, rule)
        session.add(Automation(**rule.model_dump(mode="json")))
        schedule = Schedule(
            home_id=home_id,
            name="Утренний сценарий",
            enabled=True,
            hour=7,
            minute=0,
            weekdays=list(range(7)),
            automation_id=scenarios["Доброе утро"].id,
            actions=[],
        )
        schedule.next_run_at = next_occurrence(utc_now(), home.timezone, 7, 0, list(range(7)))
        session.add(schedule)
        home.settings = {**config.model_dump(mode="json"), "demo_choice": "created"}
        record_event(
            session,
            home_id=home_id,
            event_type="demo.created",
            source="initialization",
            description="Создан демонстрационный умный дом: 11 устройств, "
            "3 сценария, правило и расписание.",
        )
    return {"created": True, "devices": 11, "scenarios": 3}


def skip(session, home_id):
    with write_transaction(session):
        home = require_home(session, home_id)
        config = HomeSettings.model_validate(home.settings)
        if config.demo_choice == "pending":
            home.settings = {**config.model_dump(mode="json"), "demo_choice": "skipped"}
