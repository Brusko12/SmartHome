from alembic.config import Config
from alembic.script import ScriptDirectory

from alembic import command
from app.core.config import BACKEND_DIR, Settings
from app.database.session import Database


def migration_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("prepend_sys_path", str(BACKEND_DIR))
    return config


def expected_revision() -> str:
    return ScriptDirectory.from_config(migration_config()).get_current_head()


def initialize_database(settings: Settings, database: Database) -> None:
    """Apply versioned migrations without deleting or re-seeding user data."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    config = migration_config()
    with database.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def main() -> None:
    settings = Settings()
    database = Database(settings.database_path)
    try:
        initialize_database(settings, database)
        print(f"Database ready: {settings.database_path}")
    finally:
        database.close()


if __name__ == "__main__":
    main()
