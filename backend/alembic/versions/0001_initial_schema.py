"""initial_schema

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "length(password_hash) > 0", name=op.f("ck_users_password_hash_not_empty")
        ),
        sa.CheckConstraint("length(trim(username)) > 0", name=op.f("ck_users_username_not_empty")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
        sqlite_autoincrement=True,
    )
    op.create_table(
        "homes",
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_homes_name_not_empty")),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_homes_owner_id_users"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_homes")),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("homes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_homes_owner_id"), ["owner_id"], unique=False)

    op.create_table(
        "automations",
        sa.Column("home_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("trigger", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(kind = 'scenario' AND trigger IS NULL) OR (kind = 'rule' AND trigger IS NOT NULL)",
            name=op.f("ck_automations_trigger_matches_kind"),
        ),
        sa.CheckConstraint(
            "kind IN ('scenario', 'rule')", name=op.f("ck_automations_kind_supported")
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_automations_name_not_empty")),
        sa.ForeignKeyConstraint(
            ["home_id"],
            ["homes.id"],
            name=op.f("fk_automations_home_id_homes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_automations")),
        sa.UniqueConstraint("id", "home_id", name=op.f("uq_automations_id")),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("automations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_automations_home_id"), ["home_id"], unique=False)

    op.create_table(
        "integrations",
        sa.Column("home_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("adapter_type", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "length(trim(adapter_type)) > 0", name=op.f("ck_integrations_adapter_type_not_empty")
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_integrations_name_not_empty")),
        sa.ForeignKeyConstraint(
            ["home_id"],
            ["homes.id"],
            name=op.f("fk_integrations_home_id_homes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_integrations")),
        sa.UniqueConstraint("home_id", "name", name=op.f("uq_integrations_home_id")),
        sa.UniqueConstraint("id", "home_id", name=op.f("uq_integrations_id")),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("integrations", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_integrations_home_id"), ["home_id"], unique=False)

    op.create_table(
        "rooms",
        sa.Column("home_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("icon", sa.String(length=64), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_rooms_name_not_empty")),
        sa.ForeignKeyConstraint(
            ["home_id"], ["homes.id"], name=op.f("fk_rooms_home_id_homes"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rooms")),
        sa.UniqueConstraint("home_id", "name", name=op.f("uq_rooms_home_id")),
        sa.UniqueConstraint("id", "home_id", name=op.f("uq_rooms_id")),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("rooms", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_rooms_home_id"), ["home_id"], unique=False)

    op.create_table(
        "devices",
        sa.Column("home_id", sa.Integer(), nullable=False),
        sa.Column("room_id", sa.Integer(), nullable=False),
        sa.Column("integration_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("device_type", sa.String(length=50), nullable=False),
        sa.Column("adapter_type", sa.String(length=100), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "device_type IN ('light', 'thermostat', 'outlet', "
            "'motion_sensor', 'climate_sensor', 'tv')",
            name=op.f("ck_devices_device_type_supported"),
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_devices_name_not_empty")),
        sa.ForeignKeyConstraint(
            ["home_id"], ["homes.id"], name=op.f("fk_devices_home_id_homes"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["integration_id", "home_id"],
            ["integrations.id", "integrations.home_id"],
            name=op.f("fk_devices_integration_id_integrations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["room_id", "home_id"],
            ["rooms.id", "rooms.home_id"],
            name=op.f("fk_devices_room_id_rooms"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devices")),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_devices_home_id"), ["home_id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_devices_integration_id"), ["integration_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_devices_room_id"), ["room_id"], unique=False)

    op.create_table(
        "schedules",
        sa.Column("home_id", sa.Integer(), nullable=False),
        sa.Column("automation_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("hour", sa.Integer(), nullable=False),
        sa.Column("minute", sa.Integer(), nullable=False),
        sa.Column("weekdays", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(automation_id IS NOT NULL AND json_array_length(actions) = 0) OR "
            "(automation_id IS NULL AND json_array_length(actions) > 0)",
            name=op.f("ck_schedules_one_execution_target"),
        ),
        sa.CheckConstraint("hour >= 0 AND hour <= 23", name=op.f("ck_schedules_hour_range")),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_schedules_name_not_empty")),
        sa.CheckConstraint("minute >= 0 AND minute <= 59", name=op.f("ck_schedules_minute_range")),
        sa.ForeignKeyConstraint(
            ["automation_id", "home_id"],
            ["automations.id", "automations.home_id"],
            name=op.f("fk_schedules_automation_id_automations"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["home_id"], ["homes.id"], name=op.f("fk_schedules_home_id_homes"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schedules")),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("schedules", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_schedules_automation_id"), ["automation_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_schedules_home_id"), ["home_id"], unique=False)

    op.create_table(
        "device_states",
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name=op.f("fk_device_states_device_id_devices"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_device_states")),
        sa.UniqueConstraint("device_id", name=op.f("uq_device_states_device_id")),
        sqlite_autoincrement=True,
    )
    op.create_table(
        "event_logs",
        sa.Column("home_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('success', 'error', 'info')", name=op.f("ck_event_logs_status_supported")
        ),
        sa.ForeignKeyConstraint(
            ["device_id"],
            ["devices.id"],
            name=op.f("fk_event_logs_device_id_devices"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["home_id"], ["homes.id"], name=op.f("fk_event_logs_home_id_homes"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_event_logs")),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("event_logs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_event_logs_device_id"), ["device_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_event_logs_event_type"), ["event_type"], unique=False)
        batch_op.create_index(
            "ix_event_logs_home_created_at", ["home_id", "created_at"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("event_logs", schema=None) as batch_op:
        batch_op.drop_index("ix_event_logs_home_created_at")
        batch_op.drop_index(batch_op.f("ix_event_logs_event_type"))
        batch_op.drop_index(batch_op.f("ix_event_logs_device_id"))

    op.drop_table("event_logs")
    op.drop_table("device_states")
    with op.batch_alter_table("schedules", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_schedules_home_id"))
        batch_op.drop_index(batch_op.f("ix_schedules_automation_id"))

    op.drop_table("schedules")
    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_devices_room_id"))
        batch_op.drop_index(batch_op.f("ix_devices_integration_id"))
        batch_op.drop_index(batch_op.f("ix_devices_home_id"))

    op.drop_table("devices")
    with op.batch_alter_table("rooms", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_rooms_home_id"))

    op.drop_table("rooms")
    with op.batch_alter_table("integrations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_integrations_home_id"))

    op.drop_table("integrations")
    with op.batch_alter_table("automations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_automations_home_id"))

    op.drop_table("automations")
    with op.batch_alter_table("homes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_homes_owner_id"))

    op.drop_table("homes")
    op.drop_table("users")
