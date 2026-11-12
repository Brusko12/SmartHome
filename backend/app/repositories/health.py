from sqlalchemy import text
from sqlalchemy.orm import Session


def database_revision(session: Session) -> str | None:
    session.execute(text("SELECT 1")).scalar_one()
    return session.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
