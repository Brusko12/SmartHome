from dataclasses import dataclass

import pytest

from app.core.config import Settings
from app.database.initialize import initialize_database
from app.database.session import Database
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


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, data_dir=tmp_path / "persistent-data", background_tasks=False)


@pytest.fixture
def database(settings):
    database = Database(settings.database_path)
    initialize_database(settings, database)
    yield database
    database.close()


@dataclass
class Graph:
    user_id: int
    home_id: int
    room_id: int
    integration_id: int
    device_id: int
    automation_id: int
    schedule_id: int
    event_id: int


@pytest.fixture
def graph(database):
    with database.sessions.begin() as session:
        user = User(username="test-user", password_hash="$test$not-a-real-credential")
        session.add(user)
        session.flush()
        home = Home(owner_id=user.id, name="Тестовый дом")
        session.add(home)
        session.flush()
        room = Room(home_id=home.id, name="Гостиная")
        integration = Integration(home_id=home.id, name="Виртуальная", adapter_type="virtual")
        session.add_all([room, integration])
        session.flush()
        device = Device(
            home_id=home.id,
            room_id=room.id,
            integration_id=integration.id,
            name="Лампа",
            device_type="light",
        )
        scenario = Automation(
            home_id=home.id,
            name="Ночь",
            kind="scenario",
            actions=[{"device_id": 1, "command": "off", "params": {}}],
        )
        session.add_all([device, scenario])
        session.flush()
        state = DeviceState(device_id=device.id, values={"power": True, "brightness": 60})
        schedule = Schedule(
            home_id=home.id,
            automation_id=scenario.id,
            name="Вечер",
            hour=22,
            minute=30,
            weekdays=[6, 0],
        )
        event = EventLog(
            home_id=home.id,
            device_id=device.id,
            event_type="device.created",
            source="test",
            description="Создана лампа",
            details={"device_name": device.name},
        )
        session.add_all([state, schedule, event])
        session.flush()
        return Graph(
            user.id,
            home.id,
            room.id,
            integration.id,
            device.id,
            scenario.id,
            schedule.id,
            event.id,
        )
