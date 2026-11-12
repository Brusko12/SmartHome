from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, Entity

if TYPE_CHECKING:
    from app.models.home import Home


class User(Entity, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(trim(username)) > 0", name="username_not_empty"),
        CheckConstraint("length(password_hash) > 0", name="password_hash_not_empty"),
        {"sqlite_autoincrement": True},
    )

    username: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    homes: Mapped[list["Home"]] = relationship(back_populates="owner", passive_deletes="all")
