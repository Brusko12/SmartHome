"""Separate simulation clock from the last observable state change."""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("device_states", sa.Column("simulated_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("device_states", "simulated_at")
