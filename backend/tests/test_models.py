import math
from datetime import datetime

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, StatementError

from app.models import (
    Automation,
    Device,
    DeviceState,
    EventLog,
    Home,
    Integration,
    Room,
    Schedule,
    User,
)


def test_all_relationships_load(database, graph):
    with database.sessions() as session:
        user = session.get(User, graph.user_id)
        home = user.homes[0]
        assert home.owner is user
        assert home.rooms[0].devices[0].id == graph.device_id
        device = home.devices[0]
        assert device.room.home is home
        assert device.integration is home.integrations[0]
        assert device.state.device is device
        assert device.events[0].id == graph.event_id
        assert home.events[0].device is device
        assert home.automations[0].schedules[0] is home.schedules[0]
        assert home.schedules[0].weekdays == [0, 6]
        assert home.schedules[0].automation.id == graph.automation_id


@pytest.mark.parametrize(
    "model,key",
    [
        (User, "user_id"),
        (Home, "home_id"),
        (Room, "room_id"),
        (Integration, "integration_id"),
        (Automation, "automation_id"),
    ],
)
def test_deletion_with_dependents_is_restricted(database, graph, model, key):
    with database.sessions() as session, pytest.raises(IntegrityError):
        session.delete(session.get(model, getattr(graph, key)))
        session.commit()


def test_device_deletion_cascades_state_but_retains_events(database, graph):
    with database.sessions.begin() as session:
        session.execute(delete(Device).where(Device.id == graph.device_id))
    with database.sessions() as session:
        assert session.scalars(select(DeviceState)).all() == []
        event = session.get(EventLog, graph.event_id)
        assert event.device_id is None
        assert event.details["device_name"] == "Лампа"


def test_deleted_device_identity_is_never_reused(database, graph):
    with database.sessions.begin() as session:
        session.execute(delete(Device).where(Device.id == graph.device_id))
        replacement = Device(
            home_id=graph.home_id,
            room_id=graph.room_id,
            name="Другая лампа",
            device_type="light",
        )
        session.add(replacement)
        session.flush()
        assert replacement.id > graph.device_id


def test_only_one_current_state_per_device(database, graph):
    with database.sessions.begin() as session, pytest.raises(IntegrityError):
        session.add(DeviceState(device_id=graph.device_id, values={}))
        session.flush()


def test_cross_home_room_and_integration_are_rejected(database, graph):
    with database.sessions.begin() as session:
        other = Home(owner_id=graph.user_id, name="Другой дом")
        session.add(other)
        session.flush()
        room = Room(home_id=other.id, name="Спальня")
        integration = Integration(home_id=other.id, name="Другая", adapter_type="virtual")
        session.add_all([room, integration])
        session.flush()
        room_id, integration_id = room.id, integration.id
    for kwargs in [{"room_id": room_id}, {"integration_id": integration_id}]:
        with database.sessions.begin() as session, pytest.raises(IntegrityError):
            device = session.get(Device, graph.device_id)
            for key, value in kwargs.items():
                setattr(device, key, value)
            session.flush()


def test_direct_action_schedule_and_ordered_scenario(database, graph):
    actions = [{"command": "on"}, {"command": "set_brightness", "params": {"brightness": 60}}]
    with database.sessions.begin() as session:
        scenario = session.get(Automation, graph.automation_id)
        scenario.actions = actions
        schedule = Schedule(
            home_id=graph.home_id,
            name="Команда",
            hour=7,
            minute=0,
            weekdays=[0, 1, 2, 3, 4],
            actions=actions,
        )
        session.add(schedule)
    with database.sessions() as session:
        assert session.get(Automation, graph.automation_id).actions == actions


@pytest.mark.parametrize("weekdays", [[], [7], [-1], [0, 0], [True], ["1"]])
def test_invalid_weekdays_are_rejected(database, graph, weekdays):
    with database.sessions.begin() as session, pytest.raises(StatementError):
        session.add(
            Schedule(
                home_id=graph.home_id,
                automation_id=graph.automation_id,
                name="Ошибка",
                hour=7,
                minute=0,
                weekdays=weekdays,
            )
        )
        session.flush()


@pytest.mark.parametrize(
    "changes",
    [
        {"hour": 24},
        {"minute": 60},
        {"automation_id": None},
        {"actions": [{"command": "on"}]},
    ],
)
def test_invalid_schedule_is_rejected(database, graph, changes):
    with database.sessions.begin() as session, pytest.raises(IntegrityError):
        schedule = session.get(Schedule, graph.schedule_id)
        for key, value in changes.items():
            setattr(schedule, key, value)
        session.flush()


@pytest.mark.parametrize("values", [[], {"bad": object()}, {"bad": math.nan}, {"bad": math.inf}])
def test_non_json_state_is_rejected(database, graph, values):
    with database.sessions.begin() as session, pytest.raises(StatementError):
        session.get(Device, graph.device_id).state.values = values
        session.flush()


def test_rule_requires_trigger(database, graph):
    with database.sessions.begin() as session, pytest.raises(IntegrityError):
        session.add(Automation(home_id=graph.home_id, name="Правило", kind="rule"))
        session.flush()


def test_unsupported_device_type_is_rejected(database, graph):
    with database.sessions.begin() as session, pytest.raises(IntegrityError):
        session.get(Device, graph.device_id).device_type = "unsupported"
        session.flush()


def test_naive_timestamp_is_rejected(database, graph):
    with database.sessions.begin() as session, pytest.raises(StatementError):
        session.get(Device, graph.device_id).updated_at = datetime(2026, 1, 1)
        session.flush()
