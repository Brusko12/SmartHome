from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, Entity
from app.schemas.json_data import ObjectJSON

if TYPE_CHECKING:
    from app.models import Device, Home


class Integration(Entity, Base):
    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint("id", "home_id"),
        UniqueConstraint("home_id", "name"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        CheckConstraint("length(trim(adapter_type)) > 0", name="adapter_type_not_empty"),
        {"sqlite_autoincrement": True},
    )

    home_id: Mapped[int] = mapped_column(ForeignKey("homes.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    adapter_type: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(default=False)
    config: Mapped[dict] = mapped_column(ObjectJSON(), default=dict)
    home: Mapped["Home"] = relationship(back_populates="integrations")
    devices: Mapped[list["Device"]] = relationship(
        back_populates="integration", foreign_keys="Device.integration_id", passive_deletes="all"
    )
