from fastapi.testclient import TestClient

from app.main import create_app


def test_static_ui_spa_assets_and_api_separation(settings, tmp_path):
    root = tmp_path / "ui"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<html>SmartHome test</html>")
    (root / "assets" / "app.js").write_text('console.log("local")')
    app = create_app(settings.model_copy(update={"frontend_dir": root}))
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/").text == "<html>SmartHome test</html>"
        assert client.get("/rooms").text == "<html>SmartHome test</html>"
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/assets/missing.js").status_code == 404
        assert client.get("/%2e%2e/backend/pyproject.toml").status_code == 404
        assert client.get("/api/unimplemented").status_code == 401
        health = client.get("/api/health")
        assert health.headers["X-SmartHome"] == "SmartHome"
        assert health.headers["X-SmartHome-Instance"] == app.state.instance_id


def test_missing_ui_build_is_an_explicit_error(settings, tmp_path):
    with TestClient(
        create_app(settings.model_copy(update={"frontend_dir": tmp_path / "absent"})),
        base_url="http://127.0.0.1",
    ) as client:
        assert client.get("/").status_code == 503
