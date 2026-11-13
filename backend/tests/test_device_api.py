from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.adapters.contracts import DeviceSnapshot
from app.adapters.registry import AdapterRegistry
from app.adapters.virtual import VirtualDeviceAdapter
from app.core.errors import Unavailable
from app.database.base import utc_now
from app.main import create_app
from app.models import DeviceState, EventLog, Home, User
from app.schemas.entities import CommandRequest
from app.services.devices import execute_command


@pytest.fixture
def api(settings):
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        with client.app.state.database.sessions.begin() as session:
            user = User(username="api-test", password_hash="$test$not-a-real-password")
            session.add(user)
            session.flush()
            home = Home(owner_id=user.id, name="Дом")
            session.add(home)
            session.flush()
            client.app.state.test_home_id = home.id
        yield client


@pytest.fixture
def home_id(api):
    return api.app.state.test_home_id


@pytest.fixture
def room(api, home_id):
    response = api.post("/api/rooms", json={"home_id": home_id, "name": "Гостиная"})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def make_device(api, room):
    def create(device_type="light", parameters=None, name="Устройство"):
        response = api.post(
            "/api/devices",
            json={
                "room_id": room["id"],
                "name": name,
                "device_type": device_type,
                "parameters": parameters or {},
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    return create


def command(api, device, name, params=None):
    return api.post(
        f"/api/devices/{device['id']}/command", json={"command": name, "params": params or {}}
    )


def test_room_crud_counts_and_pagination(api, home_id, room, make_device):
    make_device()
    assert api.get(f"/api/rooms/{room['id']}").json()["device_count"] == 1
    response = api.patch(f"/api/rooms/{room['id']}", json={"name": " Зал ", "icon": "sofa"})
    assert response.status_code == 200
    assert response.json()["name"] == "Зал"
    assert response.json()["icon"] == "sofa"
    page = api.get(f"/api/rooms?home_id={home_id}&limit=1&offset=1").json()
    assert page["total"] == 1 and page["items"] == []
    assert api.delete(f"/api/rooms/{room['id']}").status_code == 409
    assert api.get(f"/api/rooms/{room['id']}").status_code == 200


def test_empty_room_deletion(api, room):
    response = api.delete(f"/api/rooms/{room['id']}")
    assert response.status_code == 204 and response.content == b""
    assert api.get(f"/api/rooms/{room['id']}").status_code == 404


def test_room_deletion_moves_devices_without_losing_state(api, home_id, room, make_device):
    device = make_device()
    assert command(api, device, "turn_on").status_code == 200
    target = api.post("/api/rooms", json={"home_id": home_id, "name": "Спальня"}).json()
    response = api.delete(f"/api/rooms/{room['id']}?move_devices_to={target['id']}")
    assert response.status_code == 204, response.text
    moved = api.get(f"/api/devices/{device['id']}").json()
    assert moved["room_id"] == target["id"]
    assert moved["state"]["values"]["power"] is True
    assert api.get(f"/api/rooms/{target['id']}").json()["device_count"] == 1


def test_room_unique_names(api, home_id, room):
    assert (
        api.post("/api/rooms", json={"home_id": home_id, "name": room["name"]}).status_code == 409
    )
    other = api.post("/api/rooms", json={"home_id": home_id, "name": "Кухня"}).json()
    assert api.patch(f"/api/rooms/{other['id']}", json={"name": room["name"]}).status_code == 409
    assert api.get(f"/api/rooms/{other['id']}").json()["name"] == "Кухня"


def test_device_crud_and_journal_survives_deletion(api, home_id, room, make_device):
    device = make_device()
    assert device["state"]["values"]["power"] is False
    response = api.patch(f"/api/devices/{device['id']}", json={"name": "Лампа"})
    assert response.status_code == 200
    assert response.json()["name"] == "Лампа"
    assert command(api, device, "turn_on").status_code == 200
    assert api.get(f"/api/devices?room_id={room['id']}&device_type=light").json()["total"] == 1
    assert api.delete(f"/api/devices/{device['id']}").status_code == 204
    assert api.get(f"/api/devices/{device['id']}").status_code == 404
    assert api.get(f"/api/rooms/{room['id']}").json()["device_count"] == 0
    with api.app.state.database.sessions() as session:
        assert session.scalar(select(func.count()).select_from(DeviceState)) == 0
        logs = session.scalars(select(EventLog).where(EventLog.home_id == home_id)).all()
        assert {log.event_type for log in logs} >= {
            "device.created",
            "device.updated",
            "device.state_changed",
            "device.deleted",
        }
        assert all(log.device_id is None for log in logs)
        deleted = next(log for log in logs if log.event_type == "device.deleted")
        assert deleted.details["device_name"] == "Лампа"
        assert deleted.details["last_state"]["power"] is True


COMMAND_CASES = [
    ("light", "turn_on", {}, "power", True),
    ("light", "turn_off", {}, "power", False),
    ("light", "set_brightness", {"brightness": 0}, "brightness", 0),
    ("light", "set_brightness", {"brightness": 100}, "brightness", 100),
    ("light", "set_color", {"color": "#aa00ff"}, "color", "#AA00FF"),
    ("thermostat", "set_target_temperature", {"temperature": 24}, "target_temperature", 24),
    ("thermostat", "set_mode", {"mode": "Eco"}, "mode", "Eco"),
    ("outlet", "turn_on", {}, "current_power_w", 60.0),
    ("outlet", "turn_off", {}, "current_power_w", 0.0),
    ("motion_sensor", "simulate_motion", {}, "motion", True),
    ("motion_sensor", "reset_motion", {}, "motion", False),
    ("climate_sensor", "simulate_reading", {"temperature": 25.5, "humidity": 80}, "humidity", 80),
    ("tv", "turn_on", {}, "power", True),
    ("tv", "turn_off", {}, "power", False),
    ("tv", "set_volume", {"volume": 90}, "volume", 90),
    ("tv", "mute", {"muted": True}, "muted", True),
]


@pytest.mark.parametrize("device_type,name,params,key,value", COMMAND_CASES)
def test_commands_are_persisted_for_each_device_type(
    api, make_device, device_type, name, params, key, value
):
    device = make_device(device_type)
    response = command(api, device, name, params)
    assert response.status_code == 200, response.text
    assert response.json()["values"][key] == value
    fetched = api.get(f"/api/devices/{device['id']}/state")
    assert fetched.json() == response.json()
    with api.app.state.database.sessions() as session:
        assert (
            session.scalar(select(DeviceState).where(DeviceState.device_id == device["id"])).values[
                key
            ]
            == value
        )


INVALID_COMMANDS = [
    ("light", "set_brightness", {"brightness": -1}),
    ("light", "set_brightness", {"brightness": 101}),
    ("light", "set_brightness", {"brightness": True}),
    ("light", "set_brightness", {"brightness": "60"}),
    ("light", "set_brightness", {"brightness": 60, "power": True}),
    ("light", "set_brightness", {}),
    ("light", "set_color", {"color": "red"}),
    ("light", "turn_on", {"power": False}),
    ("light", "set_volume", {"volume": 10}),
    ("thermostat", "set_target_temperature", {"temperature": 50}),
    ("thermostat", "set_mode", {"mode": "unsupported"}),
    ("outlet", "set_brightness", {"brightness": 50}),
    ("motion_sensor", "simulate_motion", {"motion": True}),
    ("climate_sensor", "simulate_reading", {"temperature": 20, "humidity": 101}),
    ("tv", "set_volume", {"volume": -1}),
    ("tv", "mute", {"muted": "true"}),
]


@pytest.mark.parametrize("device_type,name,params", INVALID_COMMANDS)
def test_invalid_commands_preserve_state_and_log_error(api, make_device, device_type, name, params):
    device = make_device(device_type)
    before = api.get(f"/api/devices/{device['id']}/state").json()
    response = command(api, device, name, params)
    assert response.status_code == 422, response.text
    assert api.get(f"/api/devices/{device['id']}/state").json() == before
    with api.app.state.database.sessions() as session:
        event = session.scalar(
            select(EventLog).where(EventLog.event_type == "device.command_failed")
        )
        assert event.status == "error" and event.device_id == device["id"]


def test_state_survives_new_application_instance(api, settings, make_device):
    device = make_device("motion_sensor")
    response = command(api, device, "simulate_motion")
    assert response.status_code == 200, response.text
    expected = response.json()
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as reopened:
        assert reopened.get(f"/api/devices/{device['id']}/state").json() == expected
    assert expected["source"] == "manual_simulation"
    assert expected["values"]["last_motion_at"] is not None
    assert expected["values"]["reset_at"] is not None


def test_parameter_updates_recalculate_outlet_power(api, make_device):
    device = make_device("outlet", {"nominal_power_w": 150})
    assert command(api, device, "turn_on").json()["values"]["current_power_w"] == 150
    response = api.patch(
        f"/api/devices/{device['id']}", json={"parameters": {"nominal_power_w": 90}}
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"]["values"]["current_power_w"] == 90
    assert response.json()["state"]["values"]["energy_kwh"] == 0


@pytest.mark.parametrize(
    "device_type,parameters",
    [
        ("light", {"unsupported": True}),
        ("outlet", {"nominal_power_w": -5}),
        ("motion_sensor", {"reset_after_seconds": 0}),
        ("tv", {"volume": 20}),
    ],
)
def test_invalid_device_parameters_do_not_create_devices(api, room, device_type, parameters):
    response = api.post(
        "/api/devices",
        json={
            "room_id": room["id"],
            "name": "Bad",
            "device_type": device_type,
            "parameters": parameters,
        },
    )
    assert response.status_code == 422
    assert api.get("/api/devices").json()["total"] == 0


@pytest.mark.parametrize(
    "patch",
    [
        {},
        {"name": None},
        {"room_id": None},
        {"state": {}},
        {"device_type": "tv"},
        {"adapter_type": "mqtt"},
    ],
)
def test_invalid_patch_fields_are_rejected(api, make_device, patch):
    device = make_device()
    assert api.patch(f"/api/devices/{device['id']}", json=patch).status_code == 422


def test_cross_home_moves_and_deletions_are_atomic(api, home_id, room, make_device):
    device = make_device()
    with api.app.state.database.sessions.begin() as session:
        home = session.get(Home, home_id)
        other_home = Home(owner_id=home.owner_id, name="Другой дом")
        session.add(other_home)
        session.flush()
        other_home_id = other_home.id
    target = api.post("/api/rooms", json={"home_id": other_home_id, "name": "Другая"}).json()
    assert (
        api.patch(f"/api/devices/{device['id']}", json={"room_id": target["id"]}).status_code == 409
    )
    assert api.delete(f"/api/rooms/{room['id']}?move_devices_to={target['id']}").status_code == 409
    assert api.delete(f"/api/rooms/{room['id']}?move_devices_to={room['id']}").status_code == 422
    assert api.get(f"/api/devices/{device['id']}").json()["room_id"] == room["id"]


def test_not_found_and_query_validation(api):
    for path in ["/api/rooms/999", "/api/devices/999", "/api/devices/999/state"]:
        assert api.get(path).status_code == 404
    for path in [
        "/api/rooms?limit=101",
        "/api/devices?limit=0",
        "/api/devices?offset=-1",
        "/api/devices?device_type=unknown",
        "/api/rooms/0",
    ]:
        assert api.get(path).status_code == 422
    assert api.post("/api/rooms", json={"home_id": 999, "name": "X"}).status_code == 404
    assert (
        api.post(
            "/api/devices", json={"room_id": 999, "name": "X", "device_type": "light"}
        ).status_code
        == 404
    )


def test_disconnected_adapter_is_an_error(api, make_device):
    device = make_device()
    api.app.state.adapters.disconnect()
    assert command(api, device, "turn_on").status_code == 503
    api.app.state.adapters.connect()
    assert api.get(f"/api/devices/{device['id']}/state").json()["values"]["power"] is False


def test_nonfinite_input_returns_validation_error_instead_of_server_error(api, room):
    bodies = [
        '{"room_id":NaN,"name":"bad","device_type":"light"}',
        '{"room_id":ROOM_ID,"name":"bad","device_type":"outlet",'
        '"parameters":{"nominal_power_w":Infinity}}',
    ]
    for body in bodies:
        response = api.post(
            "/api/devices",
            content=body.replace("ROOM_ID", str(room["id"])),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422, response.text
        assert isinstance(response.json()["detail"], list)
    assert api.get("/api/devices").json()["total"] == 0


def test_dashboard_uses_saved_devices_and_sensor_readings(api, home_id, make_device):
    lamp = make_device()
    sensor = make_device("climate_sensor")
    assert command(api, lamp, "turn_on").status_code == 200
    assert (
        command(api, sensor, "simulate_reading", {"temperature": 23.5, "humidity": 40}).status_code
        == 200
    )
    result = api.get(f"/api/dashboard?home_id={home_id}")
    assert result.status_code == 200
    assert result.json()["devices"] == 2
    assert result.json()["powered_devices"] == 1
    assert result.json()["temperature"] == 23.5
    assert result.json()["recent_events"]


def test_adapter_does_not_mutate_input_or_work_when_disconnected():
    adapter = VirtualDeviceAdapter()
    with pytest.raises(Unavailable):
        adapter.initial_state("light")
    adapter.connect()
    values = adapter.initial_state("light")
    result = adapter.execute_command(
        DeviceSnapshot(1, "light", {}, values), "turn_on", {}, utc_now()
    )
    assert values["power"] is False and result["power"] is True
    adapter.disconnect()
    assert not adapter.get_connection_status()


def test_event_failure_rolls_back_state(api, make_device, monkeypatch):
    from app.services import devices

    device = make_device()
    before = api.get(f"/api/devices/{device['id']}/state").json()
    original = devices.record_event

    def broken_event(session, **kwargs):
        original(session, **{**kwargs, "event_type": None})

    monkeypatch.setattr(devices, "record_event", broken_event)
    assert command(api, device, "turn_on").status_code == 409
    assert api.get(f"/api/devices/{device['id']}/state").json() == before


def test_concurrent_commands_do_not_lose_independent_fields(api, make_device):
    device = make_device()
    barrier = Barrier(2)
    registry = AdapterRegistry()
    registry.connect()

    def worker(name, params):
        with api.app.state.database.sessions() as session:
            barrier.wait(timeout=5)
            return execute_command(
                session, registry, device["id"], CommandRequest(command=name, params=params)
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(worker, "set_brightness", {"brightness": 37})
            second = executor.submit(worker, "set_color", {"color": "#123abc"})
            first.result(timeout=15)
            second.result(timeout=15)
    finally:
        registry.disconnect()
    state = api.get(f"/api/devices/{device['id']}/state").json()["values"]
    assert state["brightness"] == 37 and state["color"] == "#123ABC"
