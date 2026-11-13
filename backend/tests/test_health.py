from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.main import create_app
from app.models import User


def test_startup_initializes_database_and_health_checks_it(settings):
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "0.1.0", "database": "ok"}
    assert settings.database_path.is_file()


def test_actual_application_restart_preserves_data(settings):
    for run in range(2):
        with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
            assert client.get("/api/health").status_code == 200
            with client.app.state.database.sessions.begin() as session:
                if run == 0:
                    session.add(User(username="persistent", password_hash="$test$hash"))
                else:
                    assert session.scalars(select(User.username)).all() == ["persistent"]


def test_health_returns_503_when_database_is_unavailable(settings):
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        with client.app.state.database.engine.begin() as connection:
            connection.execute(text("DROP TABLE alembic_version"))
        response = client.get("/api/health")
        assert response.status_code == 503
        assert response.json()["database"] == "unavailable"
        assert str(settings.database_path) not in response.text


def test_health_detects_revision_mismatch(settings):
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        with client.app.state.database.engine.begin() as connection:
            connection.execute(text("UPDATE alembic_version SET version_num = 'old'"))
        response = client.get("/api/health")
        assert response.status_code == 503
        assert response.json()["database"] == "migration_required"


def test_unknown_routes_are_not_fake_successes_and_external_hosts_are_rejected(settings):
    with TestClient(create_app(settings), base_url="http://127.0.0.1") as client:
        assert client.get("/api/unimplemented").status_code == 404
        assert client.get("/api/health", headers={"Host": "untrusted.example"}).status_code == 400
