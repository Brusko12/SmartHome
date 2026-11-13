from sqlalchemy.orm import Session

from app.models import EventLog


def record_event(
    session: Session,
    *,
    home_id: int,
    event_type: str,
    description: str,
    device_id: int | None = None,
    source: str = "user",
    status: str = "success",
    details: dict | None = None,
) -> None:
    session.add(
        EventLog(
            home_id=home_id,
            device_id=device_id,
            event_type=event_type,
            source=source,
            description=description,
            status=status,
            details=details or {},
        )
    )
