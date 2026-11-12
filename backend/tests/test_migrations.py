from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, select, text

from alembic import command
from app.database.base import Base
from app.database.initialize import expected_revision, initialize_database, migration_config
from app.database.session import Database
from app.models import Device, Home, User


def test_initial_migration_creates_nine_tables_and_no_demo_users(database):
    assert set(inspect(database.engine).get_table_names()) == set(Base.metadata.tables) | {
        "alembic_version"
    }
    assert len(Base.metadata.tables) == 9
    with database.sessions() as session:
        assert session.scalars(select(User)).all() == []
        assert (
            session.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001"
        )
        assert session.execute(text("PRAGMA foreign_keys")).scalar_one() == 1


def test_migrated_schema_matches_orm_metadata(database):
    with database.engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        assert compare_metadata(context, Base.metadata) == []


def test_reinitialization_and_new_engine_preserve_data(settings, database, graph):
    initialize_database(settings, database)
    database.close()
    reopened = Database(settings.database_path)
    try:
        initialize_database(settings, reopened)
        with reopened.sessions() as session:
            assert len(session.scalars(select(User)).all()) == 1
            assert len(session.scalars(select(Home)).all()) == 1
            device = session.get(Device, graph.device_id)
            assert device.state.values == {"power": True, "brightness": 60}
            assert device.created_at.tzinfo is not None
    finally:
        reopened.close()


def test_empty_database_downgrade_and_upgrade(database):
    config = migration_config()
    with database.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "base")
        assert set(inspect(connection).get_table_names()) == {"alembic_version"}
        command.upgrade(config, "head")
        assert (
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            == expected_revision()
        )
