from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, Entity
from app.schemas.json_data import ObjectJSON

if TYPE_CHECKING:
    from app.models import Automation, Device, EventLog, Integration, Room, Schedule, User


class Home(Entity, Base):
    __tablename__ = "homes"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        {"sqlite_autoincrement": True},
    )

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    settings: Mapped[dict] = mapped_column(ObjectJSON(), default=dict, server_default="{}")
    owner: Mapped["User"] = relationship(back_populates="homes")
    rooms: Mapped[list["Room"]] = relationship(back_populates="home", passive_deletes="all")
    devices: Mapped[list["Device"]] = relationship(back_populates="home", passive_deletes="all")
    automations: Mapped[list["Automation"]] = relationship(
        back_populates="home", passive_deletes="all"
    )
    schedules: Mapped[list["Schedule"]] = relationship(back_populates="home", passive_deletes="all")
    integrations: Mapped[list["Integration"]] = relationship(
        back_populates="home", passive_deletes="all"
    )
    events: Mapped[list["EventLog"]] = relationship(back_populates="home", passive_deletes="all")
