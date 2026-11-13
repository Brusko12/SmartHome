from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from app.api.dependencies import SessionDep
from app.api.errors import ERROR_RESPONSES
from app.models import User
from app.schemas.auth import AuthStatus, LoginInput, LoginRead, PasswordChange, UserRead
from app.services import auth
from app.services.setup import SetupInput, setup_home

router = APIRouter(prefix="/auth", tags=["auth"], responses=ERROR_RESPONSES)


def cookies(response, token, csrf):
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=auth.MAX_AGE,
        httponly=True,
        samesite="strict",
        secure=False,
    )
    response.set_cookie(
        auth.CSRF_COOKIE,
        csrf,
        max_age=auth.MAX_AGE,
        httponly=False,
        samesite="strict",
        secure=False,
    )
    response.headers["Cache-Control"] = "no-store"


def clear_cookies(response):
    response.delete_cookie(auth.SESSION_COOKIE)
    response.delete_cookie(auth.CSRF_COOKIE)


@router.get("/status", response_model=AuthStatus)
def status(session: SessionDep):
    return {"configured": session.scalar(select(User.id).limit(1)) is not None}


@router.post("/register", response_model=LoginRead, status_code=201)
def register(payload: SetupInput, session: SessionDep, response: Response):
    setup_home(session, payload, require_new=True)
    result, token, csrf = auth.login(
        session, LoginInput(username=payload.username, password=payload.password)
    )
    cookies(response, token, csrf)
    return result


@router.post("/login", response_model=LoginRead)
def login(payload: LoginInput, session: SessionDep, response: Response):
    result, token, csrf = auth.login(session, payload)
    cookies(response, token, csrf)
    return result


@router.get("/me", response_model=UserRead)
def me(request: Request):
    return {"id": request.state.identity.user_id, "username": request.state.identity.username}


@router.post("/logout", status_code=204)
def logout(request: Request, session: SessionDep, response: Response):
    auth.logout(session, request.cookies[auth.SESSION_COOKIE])
    clear_cookies(response)


@router.post("/password", status_code=204)
def password(payload: PasswordChange, request: Request, session: SessionDep, response: Response):
    auth.change_password(session, request.state.identity.user_id, payload)
    request.app.state.auth_epoch += 1
    clear_cookies(response)
