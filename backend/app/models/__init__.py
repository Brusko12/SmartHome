"""Import every model so Alembic sees the complete metadata."""

from app.models.automation import Automation
from app.models.device import Device
from app.models.device_state import DeviceState
from app.models.event_log import EventLog
from app.models.home import Home
from app.models.integration import Integration
from app.models.room import Room
from app.models.schedule import Schedule
from app.models.user import User
from app.models.user_session import UserSession

__all__ = [
    "Automation",
    "Device",
    "DeviceState",
    "EventLog",
    "Home",
    "Integration",
    "Room",
    "Schedule",
    "User",
    "UserSession",
]
