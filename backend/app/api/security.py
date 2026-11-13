import asyncio
import hmac

from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import Unauthorized
from app.services.auth import CSRF_COOKIE, SESSION_COOKIE, authenticate, digest

PUBLIC = {"/api/health", "/api/auth/status", "/api/auth/login", "/api/auth/register"}


def install_security(app):
    @app.middleware("http")
    async def security(request, call_next):
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            expected = f"{request.url.scheme}://{request.headers.get('host')}"
            if origin is not None and origin != expected:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": {
                            "code": "forbidden",
                            "message": "Запрос с другого сайта запрещён.",
                        }
                    },
                )
        if path not in PUBLIC:

            def check():
                with app.state.gate, app.state.database.sessions() as session:
                    return authenticate(
                        session, request.cookies.get(SESSION_COOKIE)
                    ), app.state.auth_epoch

            try:
                identity, epoch = await asyncio.to_thread(check)
            except Unauthorized as error:
                return JSONResponse(
                    status_code=401,
                    content={"detail": {"code": "unauthorized", "message": str(error)}},
                )
            except SQLAlchemyError:
                return JSONResponse(
                    status_code=503,
                    content={
                        "detail": {"code": "unavailable", "message": "Хранилище сессий недоступно."}
                    },
                )
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                header = request.headers.get("x-csrf-token", "")
                cookie = request.cookies.get(CSRF_COOKIE, "")
                if (
                    not header
                    or not cookie
                    or not hmac.compare_digest(header, cookie)
                    or not hmac.compare_digest(digest(header), identity.csrf_hash)
                ):
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": {
                                "code": "forbidden",
                                "message": "Неверный защитный токен. Обновите страницу.",
                            }
                        },
                    )
            request.state.identity = identity
            request.state.auth_epoch = epoch
        return await call_next(request)
