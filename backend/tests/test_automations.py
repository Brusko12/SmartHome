from sqlalchemy import select
from test_device_api import api as api
from test_device_api import command
from test_device_api import home_id as home_id
from test_device_api import make_device as make_device
from test_device_api import room as room

from app.models import EventLog


def action(device, name="turn_on", params=None, optional=False):
    return {
        "type": "command",
        "device_id": device["id"],
        "command": name,
        "params": params or {},
        "optional": optional,
    }


def create(api, home_id, actions, **kwargs):
    response = api.post(
        "/api/automations",
        json={
            "home_id": home_id,
            "name": "Правило",
            "kind": "scenario",
            "enabled": True,
            "actions": actions,
            **kwargs,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_scenario_order_and_crud(api, home_id, make_device):
    lamp = make_device()
    scenario = create(
        api, home_id, [action(lamp, "set_brightness", {"brightness": 35}), action(lamp)]
    )
    assert api.get(f"/api/devices/{lamp['id']}/state").json()["values"]["power"] is False
    result = api.post(f"/api/automations/{scenario['id']}/execute").json()
    assert result["status"] == "success" and [r["status"] for r in result["actions"]] == [
        "success",
        "success",
    ]
    state = api.get(f"/api/devices/{lamp['id']}/state").json()
    assert state["values"]["brightness"] == 35 and state["values"]["power"] is True
    assert state["source"] == "automation"
    assert api.get(f"/api/automations/{scenario['id']}").json()["last_run_at"]
    assert api.get(f"/api/automations?home_id={home_id}&kind=scenario").json()["total"] == 1
    assert (
        api.patch(f"/api/automations/{scenario['id']}", json={"enabled": False}).status_code == 200
    )
    assert api.post(f"/api/automations/{scenario['id']}/execute").json()["reason"] == "disabled"
    assert api.delete(f"/api/automations/{scenario['id']}").status_code == 204


def test_motion_trigger_and_conditions(api, home_id, make_device):
    lamp, motion = make_device(), make_device("motion_sensor")
    create(
        api,
        home_id,
        [action(lamp)],
        kind="rule",
        trigger={"type": "motion", "device_id": motion["id"]},
        conditions=[{"device_id": lamp["id"], "field": "power", "op": "eq", "value": False}],
    )
    assert command(api, motion, "simulate_motion").status_code == 200
    assert api.get(f"/api/devices/{lamp['id']}/state").json()["values"]["power"] is True


def test_threshold_crossing_not_every_update(api, home_id, make_device):
    lamp, sensor = make_device(), make_device("climate_sensor")
    create(
        api,
        home_id,
        [action(lamp)],
        kind="rule",
        trigger={
            "type": "threshold",
            "device_id": sensor["id"],
            "field": "temperature",
            "direction": "above",
            "value": 22.5,
        },
    )
    assert (
        command(api, sensor, "simulate_reading", {"temperature": 25, "humidity": 40}).status_code
        == 200
    )
    assert (
        command(api, sensor, "simulate_reading", {"temperature": 26, "humidity": 40}).status_code
        == 200
    )
    with api.app.state.database.sessions() as session:
        assert (
            len(
                session.scalars(
                    select(EventLog).where(EventLog.event_type == "automation.finished")
                ).all()
            )
            == 1
        )


def test_false_conditions_skip_actions(api, home_id, make_device):
    lamp = make_device()
    scenario = create(
        api,
        home_id,
        [action(lamp)],
        conditions=[
            {
                "device_id": lamp["id"],
                "field": "brightness",
                "op": "between",
                "value": 10,
                "upper": 20,
            }
        ],
    )
    assert (
        api.post(f"/api/automations/{scenario['id']}/execute").json()["reason"]
        == "conditions_not_met"
    )
    assert api.get(f"/api/devices/{lamp['id']}/state").json()["values"]["power"] is False


def test_partial_result_and_unexecuted_actions(api, home_id, make_device):
    lamp, removed = make_device(), make_device(name="Удаляемая")
    scenario = create(api, home_id, [action(lamp), action(removed), action(lamp, "turn_off")])
    assert api.delete(f"/api/devices/{removed['id']}").status_code == 204
    result = api.post(f"/api/automations/{scenario['id']}/execute").json()
    assert result["status"] == "partial"
    assert [step["status"] for step in result["actions"]] == ["success", "error", "skipped"]
    assert (
        api.patch(f"/api/automations/{scenario['id']}", json={"enabled": False}).status_code == 200
    )


def test_optional_missing_device_is_skipped(api, home_id, make_device):
    lamp = make_device()
    scenario = create(api, home_id, [action(lamp, optional=True)])
    api.delete(f"/api/devices/{lamp['id']}")
    result = api.post(f"/api/automations/{scenario['id']}/execute").json()
    assert result["status"] == "success" and result["actions"][0]["status"] == "skipped"


def test_recursive_scenario_is_bounded(api, home_id, make_device):
    scenario = create(api, home_id, [action(make_device())])
    assert (
        api.patch(
            f"/api/automations/{scenario['id']}",
            json={"actions": [{"type": "scenario", "automation_id": scenario["id"]}]},
        ).status_code
        == 200
    )
    result = api.post(f"/api/automations/{scenario['id']}/execute").json()
    assert result["status"] == "error"
    with api.app.state.database.sessions() as session:
        assert session.scalar(select(EventLog).where(EventLog.event_type == "automation.blocked"))


def test_cyclic_rules_stop_and_response_is_final_state(api, home_id, make_device):
    first, second = make_device(name="A"), make_device(name="B")
    create(
        api,
        home_id,
        [action(second)],
        kind="rule",
        trigger={"type": "state_changed", "device_id": first["id"], "field": "power"},
    )
    create(
        api,
        home_id,
        [action(first, "turn_off")],
        kind="rule",
        trigger={"type": "state_changed", "device_id": second["id"], "field": "power"},
    )
    result = command(api, first, "turn_on")
    assert result.status_code == 200, result.text
    assert result.json()["values"]["power"] is False
    with api.app.state.database.sessions() as session:
        assert session.scalar(select(EventLog).where(EventLog.event_type == "automation.blocked"))


def test_bad_definitions_are_rejected(api, home_id, make_device):
    lamp = make_device()
    body = {
        "home_id": home_id,
        "name": "Bad",
        "kind": "rule",
        "enabled": True,
        "trigger": {"type": "motion", "device_id": lamp["id"]},
        "actions": [action(lamp)],
    }
    assert api.post("/api/automations", json=body).status_code == 422
    body.update(
        kind="scenario", trigger=None, actions=[action(lamp, "set_brightness", {"brightness": 101})]
    )
    assert api.post("/api/automations", json=body).status_code == 422
