import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import Conflict, DomainError, InvalidCommand, NotFound, Unavailable
from app.schemas.errors import ErrorResponse

logger = logging.getLogger(__name__)
STATUS_CODES = {NotFound: 404, Conflict: 409, InvalidCommand: 422, Unavailable: 503}
ERROR_RESPONSES = {status: {"model": ErrorResponse} for status in (404, 409, 422, 503)}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError):
        # Do not echo raw inputs: nonfinite numbers and exception objects cannot
        # be encoded as JSON, and future password fields must never be reflected.
        issues = [
            {"type": issue["type"], "loc": list(issue["loc"]), "msg": issue["msg"]}
            for issue in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": issues})

    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, error: DomainError):
        return JSONResponse(
            status_code=STATUS_CODES.get(type(error), 500),
            content={"detail": {"code": error.code, "message": str(error)}},
        )

    @app.exception_handler(SQLAlchemyError)
    async def storage_error(_request: Request, error: SQLAlchemyError):
        logger.error("Database operation failed", exc_info=error)
        return JSONResponse(
            status_code=503,
            content={
                "detail": {"code": "unavailable", "message": "База данных временно недоступна."}
            },
        )
