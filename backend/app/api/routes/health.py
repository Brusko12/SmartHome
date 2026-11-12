from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.schemas.health import HealthResponse
from app.services.health import check_health

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def health(
    request: Request,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> HealthResponse:
    result = check_health(session, request.app.state.expected_revision)
    if result.status != "ok":
        response.status_code = 503
    return result
