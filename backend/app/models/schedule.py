from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, Entity, UTCDateTime
from app.schemas.json_data import ActionsJSON, WeekdaysJSON

if TYPE_CHECKING:
    from app.models import Automation, Home


class Schedule(Entity, Base):
    __tablename__ = "schedules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["automation_id", "home_id"],
            ["automations.id", "automations.home_id"],
            ondelete="RESTRICT",
        ),
        CheckConstraint("length(trim(name)) > 0", name="name_not_empty"),
        CheckConstraint("hour >= 0 AND hour <= 23", name="hour_range"),
        CheckConstraint("minute >= 0 AND minute <= 59", name="minute_range"),
        CheckConstraint(
            "(automation_id IS NOT NULL AND json_array_length(actions) = 0) OR "
            "(automation_id IS NULL AND json_array_length(actions) > 0)",
            name="one_execution_target",
        ),
        {"sqlite_autoincrement": True},
    )

    home_id: Mapped[int] = mapped_column(ForeignKey("homes.id", ondelete="RESTRICT"), index=True)
    automation_id: Mapped[int | None] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(default=False)
    hour: Mapped[int]
    minute: Mapped[int]
    # Monday = 0, Sunday = 6; list order is normalized by validation.
    weekdays: Mapped[list[int]] = mapped_column(WeekdaysJSON())
    actions: Mapped[list[dict]] = mapped_column(ActionsJSON(), default=list)
    last_run_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    next_run_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    home: Mapped["Home"] = relationship(back_populates="schedules", foreign_keys=[home_id])
    automation: Mapped["Automation | None"] = relationship(
        back_populates="schedules", foreign_keys=[automation_id]
    )
