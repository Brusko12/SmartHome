from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, Entity
from app.schemas.json_data import ObjectJSON

if TYPE_CHECKING:
    from app.models import Device, Home


class EventLog(Entity, Base):
    __tablename__ = "event_logs"
    __table_args__ = (
        Index("ix_event_logs_home_created_at", "home_id", "created_at"),
        CheckConstraint("status IN ('success', 'error', 'info')", name="status_supported"),
        {"sqlite_autoincrement": True},
    )

    home_id: Mapped[int] = mapped_column(ForeignKey("homes.id", ondelete="RESTRICT"))
    device_id: Mapped[int | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    source: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="info")
    details: Mapped[dict] = mapped_column(ObjectJSON(), default=dict)
    home: Mapped["Home"] = relationship(back_populates="events")
    device: Mapped["Device | None"] = relationship(back_populates="events")
