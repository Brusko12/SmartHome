from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.errors import Conflict, Unavailable


@contextmanager
def write_transaction(session: Session) -> Iterator[None]:
    """Serialize read-modify-write operations before reading a device state."""
    try:
        with session.begin():
            session.execute(text("BEGIN IMMEDIATE"))
            yield
    except IntegrityError as error:
        raise Conflict("Изменение нарушает уникальность или связи данных.") from error
    except OperationalError as error:
        raise Unavailable("База данных недоступна или занята. Повторите запрос.") from error
