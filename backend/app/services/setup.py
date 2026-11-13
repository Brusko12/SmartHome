from typing import Annotated

from pydantic import Field, SecretStr, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.core.passwords import hash_password, verify_password
from app.database.transactions import write_transaction
from app.models import Home, Room, User
from app.schemas.entities import InputModel, Name
from app.services.events import record_event


class SetupInput(InputModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    password: Annotated[SecretStr, Field(min_length=8, max_length=1024)]
    home_name: Name


def setup_home(session: Session, payload: SetupInput) -> int:
    with write_transaction(session):
        existing = session.scalar(select(User).order_by(User.id).limit(1))
        if existing is not None:
            if existing.username != payload.username or not verify_password(
                payload.password.get_secret_value(), existing.password_hash
            ):
                raise Conflict("Локальный пользователь уже настроен. Проверьте имя и пароль.")
            home = session.scalar(
                select(Home).where(Home.owner_id == existing.id).order_by(Home.id)
            )
            if home is not None:
                return home.id
            user = existing
        else:
            user = User(
                username=payload.username,
                password_hash=hash_password(payload.password.get_secret_value()),
            )
            session.add(user)
            session.flush()
        home = Home(owner_id=user.id, name=payload.home_name)
        session.add(home)
        session.flush()
        record_event(
            session,
            home_id=home.id,
            event_type="home.created",
            source="initialization",
            description=f"Создан дом «{home.name}».",
        )
        for name, icon in [
            ("Гостиная", "sofa"),
            ("Спальня", "bed"),
            ("Кухня", "cooking-pot"),
            ("Ванная", "bath"),
        ]:
            room = Room(home_id=home.id, name=name, icon=icon)
            session.add(room)
            session.flush()
            record_event(
                session,
                home_id=home.id,
                event_type="room.created",
                source="initialization",
                description=f"Создана комната «{name}».",
                details={"room_id": room.id},
            )
        return home.id
