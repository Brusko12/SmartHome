from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from test_device_api import api as api
from test_device_api import command
from test_device_api import home_id as home_id
from test_device_api import make_device as make_device
from test_device_api import room as room

from app.database.base import utc_now
from app.main import create_app
from app.models import UserSession


def test_first_setup_auth_csrf_and_logout(settings):
    app = create_app(settings)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/api/auth/status").json() == {"configured": False}
        assert client.get("/api/rooms").status_code == 401
        body = {
            "username": "local",
            "password": "new-test-password",
            "home_name": "Дом",
            "timezone": "Asia/Yakutsk",
        }
        assert (
            client.post(
                "/api/auth/register", json=body, headers={"Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        response = client.post("/api/auth/register", json=body)
        assert response.status_code == 201, response.text
        raw = client.cookies["smarthome_session"]
        csrf = client.cookies["smarthome_csrf"]
        assert "HttpOnly" in response.headers.get_list("set-cookie")[0]
        assert client.get("/api/auth/me").json()["username"] == "local"
        assert client.post("/api/auth/logout").status_code == 403
        headers = {"X-CSRF-Token": csrf}
        assert (
            client.post(
                "/api/auth/logout", headers={**headers, "Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        assert client.post("/api/auth/register", json=body).status_code == 409
        with app.state.database.sessions() as session:
            stored = session.scalar(select(UserSession))
            assert stored.token_hash != raw and stored.csrf_hash != csrf
        assert client.post("/api/auth/logout", headers=headers).status_code == 204
        assert client.get("/api/auth/me").status_code == 401
        assert (
            client.post(
                "/api/auth/login", json={"username": "local", "password": "bad"}
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/api/auth/login", json={"username": "local", "password": "new-test-password"}
            ).status_code
            == 200
        )


def test_expired_persisted_session_is_rejected(api):
    with api.app.state.database.sessions.begin() as session:
        session.scalar(select(UserSession)).expires_at = utc_now() - timedelta(seconds=1)
    assert api.get("/api/devices").status_code == 401


def test_password_change_revokes_all_sessions(api, settings):
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as second:
        assert (
            second.post(
                "/api/auth/login", json={"username": "api-test", "password": "api-test-password"}
            ).status_code
            == 200
        )
        result = api.post(
            "/api/auth/password",
            json={"current_password": "api-test-password", "new_password": "changed-test-password"},
        )
        assert result.status_code == 204, result.text
        assert second.get("/api/auth/me").status_code == 401
        assert api.get("/api/auth/me").status_code == 401
        assert (
            api.post(
                "/api/auth/login", json={"username": "api-test", "password": "api-test-password"}
            ).status_code
            == 401
        )
        assert (
            api.post(
                "/api/auth/login",
                json={"username": "api-test", "password": "changed-test-password"},
            ).status_code
            == 200
        )


def test_settings_history_and_real_diagnostics(api, home_id, make_device):
    lamp = make_device()
    command(api, lamp, "turn_on")
    result = api.patch(
        f"/api/settings?home_id={home_id}",
        json={"name": "Новый дом", "timezone": "Asia/Yakutsk", "config": {"ui_poll_interval": 5}},
    )
    assert result.status_code == 200, result.text
    assert result.json()["config"]["ui_poll_interval"] == 5
    assert (
        api.patch(f"/api/settings?home_id={home_id}", json={"timezone": "Not/A/Zone"}).status_code
        == 422
    )
    assert (
        api.patch(
            f"/api/settings?home_id={home_id}", json={"config": {"ui_poll_interval": 0}}
        ).status_code
        == 422
    )
    api.delete(f"/api/devices/{lamp['id']}")
    events = api.get(f"/api/events?home_id={home_id}&device_id={lamp['id']}&limit=1&order=asc")
    assert events.status_code == 200, events.text
    assert events.json()["total"] >= 3
    event_id = events.json()["items"][0]["id"]
    assert api.get(f"/api/events/{event_id}").json()["details"]["device_id"] == lamp["id"]
    assert (
        api.get(
            f"/api/events?home_id={home_id}&date_from=2026-12-01&date_to=2026-01-01"
        ).status_code
        == 422
    )
    status = api.get("/api/system/status").json()
    assert (
        status["database"]["integrity"] == "ok" and status["devices"] == 0 and status["events"] > 0
    )


def test_backup_restore_validates_before_replacing_and_revokes_sessions(api, home_id, make_device):
    response = api.get("/api/system/backup")
    assert response.status_code == 200
    saved = response.content
    assert saved.startswith(b"SQLite format 3\x00")
    lamp = make_device()
    assert api.post("/api/system/restore", content=saved).status_code == 422
    headers = {"X-Confirm-Restore": "true", "Content-Type": "application/octet-stream"}
    assert (
        api.post("/api/system/restore", content=b"not a database", headers=headers).status_code
        == 422
    )
    assert api.get(f"/api/devices/{lamp['id']}").status_code == 200
    result = api.post("/api/system/restore", content=saved, headers=headers)
    assert result.status_code == 200, result.text
    assert result.json()["requires_login"] is True
    assert list((api.app.state.configuration.data_dir / "backups").glob("before-restore-*.db"))
    assert api.get("/api/devices").status_code == 401
    assert (
        api.post(
            "/api/auth/login", json={"username": "api-test", "password": "api-test-password"}
        ).status_code
        == 200
    )
    api.headers["X-CSRF-Token"] = api.cookies["smarthome_csrf"]
    assert api.get("/api/devices").json()["total"] == 0


def test_backup_rejects_unknown_schema(api):
    import sqlite3

    saved = api.get("/api/system/backup").content
    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(saved)
        connection.execute("CREATE TABLE unexpected(id INTEGER)")
        invalid = connection.serialize()
    finally:
        connection.close()
    response = api.post(
        "/api/system/restore", content=invalid, headers={"X-Confirm-Restore": "true"}
    )
    assert response.status_code == 422, response.text
    assert api.get("/api/auth/me").status_code == 200


def test_demo_seed_is_idempotent_and_uses_real_device_references(api, home_id):
    response = api.post(f"/api/demo?home_id={home_id}", json={"confirm": True})
    assert response.status_code == 200, response.text
    assert api.get("/api/devices").json()["total"] == 11
    assert (
        api.post(f"/api/demo?home_id={home_id}", json={"confirm": True}).json()["created"] is False
    )
    rows = api.get(f"/api/automations?home_id={home_id}").json()["items"]
    assert len(rows) == 4
    night = next(row for row in rows if row["name"] == "Ночной режим")
    lamp = next(d for d in api.get("/api/devices").json()["items"] if d["name"] == "Ночная лампа")
    api.delete(f"/api/devices/{lamp['id']}")
    result = api.post(f"/api/automations/{night['id']}/execute").json()
    assert result["status"] == "success"
    assert any(step["status"] == "skipped" for step in result["actions"])
