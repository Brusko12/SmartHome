from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, Entity

if TYPE_CHECKING:
    from app.models import Device, Home


class Room(Entity, Base):
    __tablename__ = "rooms"
    __table_args__ = (
        UniqueConstraint("id", "home_id"),
        UniqueConstraint("home_id", "name"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        {"sqlite_autoincrement": True},
    )

    home_id: Mapped[int] = mapped_column(ForeignKey("homes.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    icon: Mapped[str] = mapped_column(String(64), default="house")
    home: Mapped["Home"] = relationship(back_populates="rooms")
    devices: Mapped[list["Device"]] = relationship(
        back_populates="room", foreign_keys="Device.room_id", passive_deletes="all"
    )
