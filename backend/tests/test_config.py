from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings, default_data_dir


def test_defaults_are_persistent_and_outside_project(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local-app-data"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    for key in ("SMARTHOME_DATA_DIR", "SMARTHOME_PORT", "SMARTHOME_LOG_LEVEL"):
        monkeypatch.delenv(key, raising=False)
    settings = Settings(_env_file=None)
    assert settings.data_dir == default_data_dir()
    assert settings.database_path.name == "smart_home.db"
    assert settings.port == 8000
    assert settings.log_level == "info"
    assert not settings.data_dir.exists()  # Loading config has no filesystem side effects.


def test_configuration_uses_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("SMARTHOME_DATA_DIR", str(tmp_path / "custom"))
    monkeypatch.setenv("SMARTHOME_PORT", "8123")
    assert Settings(_env_file=None).database_path == tmp_path / "custom" / "smart_home.db"
    assert Settings(_env_file=None).port == 8123


@pytest.mark.parametrize("port", [0, 80, 65536, "bad"])
def test_invalid_ports_are_rejected(port):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, port=port)


def test_relative_data_directory_is_rejected():
    with pytest.raises(ValidationError, match="absolute path"):
        Settings(_env_file=None, data_dir=Path("relative"))


def test_dotenv_is_utf8_and_environment_takes_precedence(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        f"SMARTHOME_DATA_DIR={tmp_path / 'данные'}\nSMARTHOME_PORT=8123\n", encoding="utf-8"
    )
    monkeypatch.delenv("SMARTHOME_DATA_DIR", raising=False)
    monkeypatch.setenv("SMARTHOME_PORT", "8124")
    settings = Settings(_env_file=env)
    assert settings.data_dir.name == "данные"
    assert settings.port == 8124
