from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, Entity
from app.schemas.json_data import ObjectJSON

if TYPE_CHECKING:
    from app.models import DeviceState, EventLog, Home, Integration, Room


class Device(Entity, Base):
    __tablename__ = "devices"
    __table_args__ = (
        ForeignKeyConstraint(
            ["room_id", "home_id"], ["rooms.id", "rooms.home_id"], ondelete="RESTRICT"
        ),
        ForeignKeyConstraint(
            ["integration_id", "home_id"],
            ["integrations.id", "integrations.home_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        CheckConstraint(
            "device_type IN ('light', 'thermostat', 'outlet', "
            "'motion_sensor', 'climate_sensor', 'tv')",
            name="device_type_supported",
        ),
        {"sqlite_autoincrement": True},
    )

    home_id: Mapped[int] = mapped_column(ForeignKey("homes.id", ondelete="RESTRICT"), index=True)
    room_id: Mapped[int] = mapped_column(index=True)
    integration_id: Mapped[int | None] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(200))
    device_type: Mapped[str] = mapped_column(String(50))
    adapter_type: Mapped[str] = mapped_column(String(100), default="virtual")
    parameters: Mapped[dict] = mapped_column(ObjectJSON(), default=dict)
    home: Mapped["Home"] = relationship(back_populates="devices", foreign_keys=[home_id])
    room: Mapped["Room"] = relationship(back_populates="devices", foreign_keys=[room_id])
    integration: Mapped["Integration | None"] = relationship(
        back_populates="devices", foreign_keys=[integration_id]
    )
    state: Mapped["DeviceState | None"] = relationship(
        back_populates="device", uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )
    events: Mapped[list["EventLog"]] = relationship(back_populates="device", passive_deletes="all")
