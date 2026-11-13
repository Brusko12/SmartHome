from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_automations import action
from test_automations import create as create_automation
from test_device_api import api as api
from test_device_api import command
from test_device_api import home_id as home_id
from test_device_api import make_device as make_device
from test_device_api import room as room

from app.core.config import Settings
from app.core.errors import Unavailable
from app.database.base import utc_now
from app.database.lock import DatabaseLock
from app.main import create_app
from app.models import Device, EventLog, Home, Schedule
from app.schemas.settings import HomeSettings
from app.services.schedules import next_occurrence
from app.services.simulation import advance


def test_power_time_energy_and_off_state():
    now = utc_now()
    config = HomeSettings()
    values = {"power": True, "current_power_w": 600.0, "energy_kwh": 0.2}
    assert advance("outlet", 1, values, 3600, now, config)["energy_kwh"] == pytest.approx(0.8)
    values.update(power=False, current_power_w=0)
    assert advance("outlet", 1, values, 3600, now, config)["energy_kwh"] == 0.2
    assert advance("outlet", 1, values, 3600, now, HomeSettings(simulation_enabled=False)) == values


@pytest.mark.parametrize(
    "mode,target,expected",
    [
        ("Heating", 25, 21.6),
        ("Cooling", 18, 20.4),
        ("Auto", 24, 21.6),
        ("Off", 24, 20.95),
        ("Eco", 24, 20.7),
    ],
)
def test_thermostat_deterministic_modes(mode, target, expected):
    result = advance(
        "thermostat",
        1,
        {"current_temperature": 21.0, "target_temperature": target, "mode": mode},
        60,
        utc_now(),
        HomeSettings(),
    )
    assert result["current_temperature"] == pytest.approx(expected)


def test_motion_deadline_and_deterministic_sensor():
    now = utc_now()
    config = HomeSettings()
    state = {
        "motion": True,
        "last_motion_at": (now - timedelta(seconds=5)).isoformat(),
        "reset_at": now.isoformat(),
    }
    assert advance("motion_sensor", 1, state, 5, now, config)["motion"] is False
    first = advance("climate_sensor", 7, {"temperature": 21.0, "humidity": 45.0}, 10, now, config)
    assert first == advance(
        "climate_sensor", 7, {"temperature": 21.0, "humidity": 45.0}, 10, now, config
    )
    assert 18.5 <= first["temperature"] <= 21.5 and 35 <= first["humidity"] <= 55


def test_timezones_dst_gap_and_no_duplicate_ambiguous_hour():
    assert next_occurrence(
        datetime(2026, 11, 12, 21, 59, tzinfo=UTC), "Asia/Yakutsk", 7, 0, list(range(7))
    ) == datetime(2026, 11, 12, 22, 0, tzinfo=UTC)
    assert next_occurrence(
        datetime(2026, 3, 8, 5, 0, tzinfo=UTC), "America/New_York", 2, 30, list(range(7))
    ) == datetime(2026, 3, 9, 6, 30, tzinfo=UTC)
    assert next_occurrence(
        datetime(2026, 11, 1, 5, 31, tzinfo=UTC), "America/New_York", 1, 30, list(range(7))
    ) == datetime(2026, 11, 2, 6, 30, tzinfo=UTC)


def test_schedule_claim_execute_once_and_restart_recomputes(api, home_id, make_device):
    lamp = make_device()
    response = api.post(
        "/api/schedules",
        json={
            "home_id": home_id,
            "name": "Утро",
            "enabled": True,
            "hour": 7,
            "minute": 0,
            "weekdays": list(range(7)),
            "actions": [action(lamp)],
        },
    )
    assert response.status_code == 201, response.text
    schedule_id = response.json()["id"]
    now = utc_now()
    with api.app.state.database.sessions.begin() as session:
        session.get(Schedule, schedule_id).next_run_at = now - timedelta(seconds=1)
    worker = api.app.state.runtime
    worker.run_schedules(now)
    worker.run_schedules(now)
    assert api.get(f"/api/devices/{lamp['id']}/state").json()["values"]["power"] is True
    worker.recover(now + timedelta(days=2))
    worker.run_schedules(now + timedelta(days=2))
    with api.app.state.database.sessions() as session:
        assert (
            len(
                session.scalars(
                    select(EventLog).where(EventLog.event_type == "schedule.started")
                ).all()
            )
            == 1
        )
        assert session.get(Schedule, schedule_id).next_run_at > now + timedelta(days=2)
    assert (
        api.patch(f"/api/schedules/{schedule_id}", json={"enabled": False}).json()["next_run_at"]
        is None
    )
    assert api.delete(f"/api/schedules/{schedule_id}").status_code == 204


def test_time_trigger_only_once_per_minute(api, home_id, make_device):
    lamp = make_device()
    now = utc_now().replace(second=5, microsecond=0)
    create_automation(
        api,
        home_id,
        [action(lamp)],
        kind="rule",
        trigger={
            "type": "time",
            "hour": now.hour,
            "minute": now.minute,
            "weekdays": list(range(7)),
        },
    )
    worker = api.app.state.runtime
    worker.started_at = now - timedelta(minutes=1)
    worker.run_time_rules(now)
    worker.run_time_rules(now + timedelta(seconds=10))
    with api.app.state.database.sessions() as session:
        assert (
            len(
                session.scalars(
                    select(EventLog).where(EventLog.event_type == "automation.finished")
                ).all()
            )
            == 1
        )


def test_turn_off_accounts_for_energy_before_command(api, home_id, make_device):
    outlet = make_device("outlet", {"nominal_power_w": 600})
    with api.app.state.database.sessions.begin() as session:
        session.get(Home, home_id).settings = {"simulation_enabled": True}
        device = session.get(Device, outlet["id"])
        device.state.values = {"power": True, "current_power_w": 600.0, "energy_kwh": 0.0}
        device.state.simulated_at = utc_now() - timedelta(hours=1)
    result = command(api, outlet, "turn_off")
    assert result.status_code == 200, result.text
    assert result.json()["values"]["energy_kwh"] == pytest.approx(0.6, abs=0.001)
    assert result.json()["values"]["current_power_w"] == 0


def test_lock_rejects_second_worker_and_releases(tmp_path):
    first, second = DatabaseLock(tmp_path / "home.db"), DatabaseLock(tmp_path / "home.db")
    first.acquire()
    try:
        with pytest.raises(Unavailable):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()


def test_background_lifecycle_and_second_instance_guard(tmp_path):
    settings = Settings(_env_file=None, data_dir=tmp_path / "runtime", background_tasks=True)
    app = create_app(settings)
    with TestClient(app, base_url="http://127.0.0.1") as first:
        assert first.get("/api/health").status_code == 200
        with pytest.raises(Unavailable):
            with TestClient(create_app(settings), base_url="http://127.0.0.1"):
                pass
    assert app.state.runtime_task.done()
