from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, Entity, UTCDateTime
from app.schemas.json_data import ActionsJSON, ObjectJSON, ObjectsJSON

if TYPE_CHECKING:
    from app.models import Home, Schedule


class Automation(Entity, Base):
    __tablename__ = "automations"
    __table_args__ = (
        UniqueConstraint("id", "home_id"),
        CheckConstraint("kind IN ('scenario', 'rule')", name="kind_supported"),
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        CheckConstraint(
            "(kind = 'scenario' AND trigger IS NULL) OR (kind = 'rule' AND trigger IS NOT NULL)",
            name="trigger_matches_kind",
        ),
        {"sqlite_autoincrement": True},
    )

    home_id: Mapped[int] = mapped_column(ForeignKey("homes.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    enabled: Mapped[bool] = mapped_column(default=False)
    trigger: Mapped[dict | None] = mapped_column(ObjectJSON(none_as_null=True), nullable=True)
    conditions: Mapped[list[dict]] = mapped_column(ObjectsJSON(), default=list)
    actions: Mapped[list[dict]] = mapped_column(ActionsJSON(), default=list)
    last_run_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    home: Mapped["Home"] = relationship(back_populates="automations")
    schedules: Mapped[list["Schedule"]] = relationship(
        back_populates="automation", foreign_keys="Schedule.automation_id", passive_deletes="all"
    )
