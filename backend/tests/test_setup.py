import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.core.errors import Conflict
from app.core.passwords import hash_password, verify_password
from app.models import Home, Room, User
from app.services.setup import SetupInput, setup_home


def test_setup_is_idempotent_and_keeps_user_changes(database):
    payload = SetupInput(username="local", password="test-password-123", home_name="Мой дом")
    with database.sessions() as session:
        home_id = setup_home(session, payload)
    with database.sessions.begin() as session:
        user = session.scalar(select(User))
        assert "test-password-123" not in user.password_hash
        assert verify_password("test-password-123", user.password_hash)
        session.scalar(select(Room).where(Room.name == "Гостиная")).name = "Зал"
    with database.sessions() as session:
        assert setup_home(session, payload) == home_id
    with database.sessions() as session:
        assert session.scalar(select(func.count()).select_from(User)) == 1
        assert session.scalar(select(func.count()).select_from(Home)) == 1
        assert session.scalar(select(func.count()).select_from(Room)) == 4
        assert session.scalar(select(Room).where(Room.name == "Зал")) is not None
    with database.sessions() as session, pytest.raises(Conflict):
        setup_home(session, SetupInput(username="local", password="wrong-password", home_name="X"))


def test_password_hash_is_salted_and_rejects_invalid_credentials():
    first, second = hash_password("test-password"), hash_password("test-password")
    assert first != second
    assert verify_password("test-password", first)
    assert not verify_password("incorrect", first)
    assert not verify_password("test-password", "invalid")


def test_setup_rejects_short_password():
    with pytest.raises(ValidationError):
        SetupInput(username="local", password="short", home_name="Дом")


def test_setup_cli_creates_database_without_printing_password(monkeypatch, tmp_path, capsys):
    from app.database import setup
    from app.database.session import Database

    answers = iter(["local", "Мой дом"])
    monkeypatch.setenv("SMARTHOME_DATA_DIR", str(tmp_path / "cli-data"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(setup, "getpass", lambda _prompt: "non-production-password")
    assert setup.main() == 0
    output = capsys.readouterr().out
    assert "home_id=" in output and "non-production-password" not in output
    database = Database(tmp_path / "cli-data" / "smart_home.db")
    try:
        with database.sessions() as session:
            assert session.scalar(select(func.count()).select_from(Room)) == 4
    finally:
        database.close()


def test_setup_cli_password_mismatch_creates_no_database(monkeypatch, tmp_path, capsys):
    from app.database import setup

    passwords = iter(["first-password", "different-password"])
    monkeypatch.setenv("SMARTHOME_DATA_DIR", str(tmp_path / "cancelled"))
    monkeypatch.setattr("builtins.input", lambda _prompt: "local")
    monkeypatch.setattr(setup, "getpass", lambda _prompt: next(passwords))
    assert setup.main() == 1
    assert not (tmp_path / "cancelled").exists()
    output = capsys.readouterr().out
    assert "first-password" not in output and "different-password" not in output
