"""Persistent home settings for simulation and interface polling."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("homes", sa.Column("settings", sa.JSON(), nullable=False, server_default="{}"))


def downgrade():
    op.drop_column("homes", "settings")
