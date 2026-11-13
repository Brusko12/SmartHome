from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import Conflict, NotFound
from app.models import Device, Home, Room


def require_home(session: Session, home_id: int) -> Home:
    home = session.get(Home, home_id)
    if home is None:
        raise NotFound("Дом не найден. Сначала выполните первоначальную настройку.")
    return home


def require_room(session: Session, room_id: int) -> Room:
    room = session.get(Room, room_id)
    if room is None:
        raise NotFound("Комната не найдена.")
    return room


def require_device(session: Session, device_id: int) -> Device:
    device = session.scalar(
        select(Device).where(Device.id == device_id).options(selectinload(Device.state))
    )
    if device is None:
        raise NotFound("Устройство не найдено.")
    if device.state is None:
        raise Conflict("У устройства отсутствует сохранённое состояние.")
    return device


def device_count(session: Session, room_id: int) -> int:
    return session.scalar(select(func.count()).select_from(Device).where(Device.room_id == room_id))


def list_rooms(session: Session, home_id: int | None, limit: int, offset: int):
    query = select(Room)
    if home_id is not None:
        query = query.where(Room.home_id == home_id)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    rooms = session.scalars(query.order_by(Room.id).offset(offset).limit(limit)).all()
    ids = [room.id for room in rooms]
    counts = (
        dict(
            session.execute(
                select(Device.room_id, func.count())
                .where(Device.room_id.in_(ids))
                .group_by(Device.room_id)
            ).all()
        )
        if ids
        else {}
    )
    return rooms, counts, total


def list_devices(
    session: Session,
    home_id: int | None,
    room_id: int | None,
    device_type: str | None,
    limit: int,
    offset: int,
):
    query = select(Device)
    for field, value in [
        (Device.home_id, home_id),
        (Device.room_id, room_id),
        (Device.device_type, device_type),
    ]:
        if value is not None:
            query = query.where(field == value)
    total = session.scalar(select(func.count()).select_from(query.subquery()))
    devices = session.scalars(
        query.options(selectinload(Device.state)).order_by(Device.id).offset(offset).limit(limit)
    ).all()
    return devices, total


def room_devices(session: Session, room_id: int) -> list[Device]:
    return list(
        session.scalars(select(Device).where(Device.room_id == room_id).order_by(Device.id))
    )


def unique_room_name(session: Session, home_id: int, name: str, except_id: int | None = None):
    query = select(Room.id).where(Room.home_id == home_id, Room.name == name)
    if except_id is not None:
        query = query.where(Room.id != except_id)
    if session.scalar(query) is not None:
        raise Conflict("Комната с таким названием уже существует в этом доме.")
