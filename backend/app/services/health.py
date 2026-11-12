import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import __version__
from app.repositories.health import database_revision
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)


def check_health(session: Session, expected_revision: str) -> HealthResponse:
    try:
        revision = database_revision(session)
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        return HealthResponse(status="degraded", version=__version__, database="unavailable")
    if revision != expected_revision:
        return HealthResponse(status="degraded", version=__version__, database="migration_required")
    return HealthResponse(status="ok", version=__version__, database="ok")
