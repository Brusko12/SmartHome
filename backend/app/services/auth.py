import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import delete, select

from app.core.errors import Unauthorized
from app.core.passwords import hash_password, verify_password
from app.database.base import utc_now
from app.database.transactions import write_transaction
from app.models import Home, User, UserSession
from app.services.events import record_event

SESSION_COOKIE = "smarthome_session"
CSRF_COOKIE = "smarthome_csrf"
MAX_AGE = 12 * 60 * 60


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Identity:
    user_id: int
    username: str
    csrf_hash: str


def authenticate(session, token) -> Identity:
    if not token or len(token) > 256:
        raise Unauthorized("Выполните вход в SmartHome.")
    row = session.scalar(select(UserSession).where(UserSession.token_hash == digest(token)))
    if row is None or row.expires_at <= utc_now():
        raise Unauthorized("Сессия завершена. Выполните вход.")
    user = session.get(User, row.user_id)
    if user is None:
        raise Unauthorized("Пользователь не найден.")
    return Identity(user.id, user.username, row.csrf_hash)


def login(session, payload):
    with write_transaction(session):
        user = session.scalar(select(User).where(User.username == payload.username))
        if user is None or not verify_password(
            payload.password.get_secret_value(), user.password_hash
        ):
            raise Unauthorized("Неверное имя пользователя или пароль.")
        now = utc_now()
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        session.execute(delete(UserSession).where(UserSession.expires_at <= now))
        session.add(
            UserSession(
                user_id=user.id,
                token_hash=digest(token),
                csrf_hash=digest(csrf),
                expires_at=now + timedelta(seconds=MAX_AGE),
            )
        )
        home = session.scalar(select(Home).where(Home.owner_id == user.id).order_by(Home.id))
        if home:
            record_event(
                session,
                home_id=home.id,
                event_type="auth.login",
                source="auth",
                description="Выполнен локальный вход.",
            )
        result = {"user": {"id": user.id, "username": user.username}}
    return result, token, csrf


def logout(session, token):
    with write_transaction(session):
        session.execute(delete(UserSession).where(UserSession.token_hash == digest(token)))


def change_password(session, user_id, payload):
    with write_transaction(session):
        user = session.get(User, user_id)
        if user is None or not verify_password(
            payload.current_password.get_secret_value(), user.password_hash
        ):
            raise Unauthorized("Текущий пароль неверен.")
        user.password_hash = hash_password(payload.new_password.get_secret_value())
        session.execute(delete(UserSession).where(UserSession.user_id == user.id))
        home = session.scalar(select(Home).where(Home.owner_id == user.id).order_by(Home.id))
        if home:
            record_event(
                session,
                home_id=home.id,
                event_type="auth.password_changed",
                source="auth",
                description="Пароль изменён, сессии завершены.",
            )
