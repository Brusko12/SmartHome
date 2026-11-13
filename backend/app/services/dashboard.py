from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Automation, Device, DeviceState, EventLog, Home, Room
from app.repositories.entities import require_home


def homes(session: Session) -> list[dict]:
    return [
        {"id": h.id, "name": h.name, "timezone": h.timezone}
        for h in session.scalars(select(Home).order_by(Home.id))
    ]


def dashboard(session: Session, home_id: int) -> dict:
    home = require_home(session, home_id)
    rows = session.execute(
        select(Device, DeviceState).join(DeviceState).where(Device.home_id == home_id)
    ).all()
    temperatures = [
        state.values["temperature"]
        for device, state in rows
        if device.device_type == "climate_sensor" and "temperature" in state.values
    ]
    events = session.scalars(
        select(EventLog)
        .where(EventLog.home_id == home_id)
        .order_by(EventLog.created_at.desc(), EventLog.id.desc())
        .limit(6)
    ).all()
    return {
        "home": {"id": home.id, "name": home.name, "timezone": home.timezone},
        "rooms": session.scalar(
            select(func.count()).select_from(Room).where(Room.home_id == home_id)
        ),
        "devices": len(rows),
        "powered_devices": sum(state.values.get("power") is True for _, state in rows),
        "active_automations": session.scalar(
            select(func.count())
            .select_from(Automation)
            .where(
                Automation.home_id == home_id,
                Automation.kind == "rule",
                Automation.enabled.is_(True),
            )
        ),
        "temperature": round(sum(temperatures) / len(temperatures), 1) if temperatures else None,
        "recent_events": [
            {
                "id": e.id,
                "description": e.description,
                "status": e.status,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    }
