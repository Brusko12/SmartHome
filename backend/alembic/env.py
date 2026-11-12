from alembic import context
from app import models  # noqa: F401
from app.core.config import Settings
from app.database.base import Base, UTCDateTime
from app.database.session import Database
from app.schemas.json_data import ValidatedJSON

config = context.config
target_metadata = Base.metadata


def render_item(item_type, obj, _autogen_context):
    # Freeze storage types into revisions; migrations must not depend on future
    # application validation classes.
    if item_type == "type" and isinstance(obj, UTCDateTime):
        return "sa.DateTime()"
    if item_type == "type" and isinstance(obj, ValidatedJSON):
        return f"sa.JSON(none_as_null={obj.impl.none_as_null!r})"
    return False


def run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
        compare_type=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Use online migrations against the configured local SQLite database")
elif config.attributes.get("connection") is not None:
    run_migrations(config.attributes["connection"])
else:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    database = Database(settings.database_path)
    try:
        with database.engine.begin() as connection:
            run_migrations(connection)
    finally:
        database.close()
