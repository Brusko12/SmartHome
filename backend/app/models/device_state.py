from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, Entity
from app.schemas.json_data import ObjectJSON

if TYPE_CHECKING:
    from app.models.device import Device


class DeviceState(Entity, Base):
    __tablename__ = "device_states"
    __table_args__ = {"sqlite_autoincrement": True}

    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"), unique=True
    )
    values: Mapped[dict] = mapped_column(ObjectJSON(), default=dict)
    source: Mapped[str] = mapped_column(String(50), default="initialization")
    device: Mapped["Device"] = relationship(back_populates="state")
