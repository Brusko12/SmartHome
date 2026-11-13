import logging
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from zoneinfo import ZoneInfo

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import delete, select

from app.core.errors import InvalidCommand, Unavailable
from app.core.passwords import supported_password_hash
from app.database.base import Base, utc_now
from app.database.initialize import initialize_database
from app.database.session import Database
from app.database.transactions import write_transaction
from app.models import Automation, Device, Home, Schedule, User, UserSession
from app.schemas.automations import AutomationInput
from app.schemas.devices import STATE_TYPES
from app.schemas.schedules import ScheduleInput
from app.schemas.settings import HomeSettings
from app.services.automations import payload_dict
from app.services.events import record_event
from app.services.schedules import data

logger = logging.getLogger(__name__)
MAX_BACKUP_BYTES = 2 * 1024 * 1024 * 1024


def snapshot_file(source_path: Path, target_path: Path):
    with (
        closing(sqlite3.connect(str(source_path), timeout=10)) as source,
        closing(sqlite3.connect(str(target_path))) as target,
    ):
        source.backup(target)


def export_backup(state):
    directory = state.configuration.data_dir
    handle = tempfile.NamedTemporaryFile(
        prefix=".export-", suffix=".db", dir=directory, delete=False
    )
    path = Path(handle.name)
    handle.close()
    try:
        with state.gate:
            snapshot_file(state.configuration.database_path, path)
        return path
    except (sqlite3.Error, OSError) as error:
        path.unlink(missing_ok=True)
        raise Unavailable(
            "Не удалось создать резервную копию. Проверьте место на диске."
        ) from error


def validate_file(path: Path, settings):
    # Work on the uploaded copy, never the live database, until every check passes.
    with closing(sqlite3.connect(str(path))) as connection:
        if connection.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise ValueError("integrity")
        if connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('trigger','view')"
        ).fetchone():
            raise ValueError("unexpected schema objects")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("foreign keys")
    candidate_settings = settings.model_copy(update={"data_dir": path.parent})
    candidate = Database(path)
    try:
        initialize_database(candidate_settings, candidate)
        with candidate.engine.connect() as connection:
            if compare_metadata(MigrationContext.configure(connection), Base.metadata):
                raise ValueError("schema mismatch")
        with candidate.sessions() as session:
            if session.scalar(select(User.id).limit(1)) is None:
                raise ValueError("user missing")
            if session.scalar(select(Home.id).limit(1)) is None:
                raise ValueError("home missing")
            for home in session.scalars(select(Home)):
                if not isinstance(home.name, str) or not home.name.strip():
                    raise ValueError("invalid home name")
                ZoneInfo(home.timezone)
                HomeSettings.model_validate(home.settings)
            for user in session.scalars(select(User)):
                if (
                    not isinstance(user.username, str)
                    or not user.username.strip()
                    or not supported_password_hash(user.password_hash)
                ):
                    raise ValueError("invalid user credentials")
            for device in session.scalars(select(Device)):
                if device.state is None:
                    raise ValueError("state missing")
                import json

                STATE_TYPES[device.device_type].model_validate_json(json.dumps(device.state.values))
            for row in session.scalars(select(Automation)):
                AutomationInput.model_validate(payload_dict(row))
            for row in session.scalars(select(Schedule)):
                ScheduleInput.model_validate(data(row))
    finally:
        candidate.close()


def restore_backup(state, path: Path):
    with path.open("rb") as file:
        valid_header = file.read(16) == b"SQLite format 3\x00"
    if not valid_header or path.stat().st_size > MAX_BACKUP_BYTES:
        raise InvalidCommand("Выберите резервную копию SQLite размером не более 2 ГБ.")
    try:
        validate_file(path, state.configuration)
    except Exception as error:
        logger.info("Rejected invalid backup: %s", type(error).__name__)
        raise InvalidCommand("Файл повреждён или не соответствует формату SmartHome.") from error
    with state.gate:
        directory = state.configuration.data_dir
        backup_dir = directory / "backups"
        try:
            backup_dir.mkdir(exist_ok=True)
            safety = backup_dir / f"before-restore-{utc_now().strftime('%Y%m%d-%H%M%S-%f')}.db"
            snapshot_file(state.configuration.database_path, safety)
        except (sqlite3.Error, OSError) as error:
            raise Unavailable(
                "Не удалось сохранить страховочную копию. Восстановление отменено."
            ) from error
        state.database.engine.dispose()
        try:
            snapshot_file(path, state.configuration.database_path)
        except (sqlite3.Error, OSError) as error:
            raise Unavailable(
                "Ошибка восстановления. Страховочная копия сохранена в каталоге backups."
            ) from error
        with state.database.sessions() as session, write_transaction(session):
            session.execute(delete(UserSession))
            home = session.scalar(select(Home).order_by(Home.id))
            record_event(
                session,
                home_id=home.id,
                event_type="database.restored",
                source="system",
                description="База восстановлена из резервной копии.",
                details={"safety_backup": safety.name},
            )
        now = utc_now()
        state.runtime.started_at = now
        state.runtime.last_home_tick.clear()
        state.runtime.recover(now)
        state.runtime.last_error = None
        state.auth_epoch += 1
        return {"restored": True, "requires_login": True, "safety_backup": safety.name}
