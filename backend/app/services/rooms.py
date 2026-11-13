from sqlalchemy.orm import Session

from app.core.errors import Conflict, InvalidCommand
from app.database.transactions import write_transaction
from app.models import Room
from app.repositories import entities as repository
from app.schemas.entities import RoomCreate, RoomPage, RoomPatch, RoomRead
from app.services.events import record_event


def room_response(room: Room, count: int) -> RoomRead:
    return RoomRead(
        id=room.id,
        home_id=room.home_id,
        name=room.name,
        icon=room.icon,
        device_count=count,
        created_at=room.created_at,
        updated_at=room.updated_at,
    )


def list_rooms(session: Session, home_id: int | None, limit: int, offset: int) -> RoomPage:
    if home_id is not None:
        repository.require_home(session, home_id)
    rooms, counts, total = repository.list_rooms(session, home_id, limit, offset)
    return RoomPage(
        items=[room_response(room, counts.get(room.id, 0)) for room in rooms],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_room(session: Session, room_id: int) -> RoomRead:
    room = repository.require_room(session, room_id)
    return room_response(room, repository.device_count(session, room.id))


def create_room(session: Session, payload: RoomCreate) -> RoomRead:
    with write_transaction(session):
        repository.require_home(session, payload.home_id)
        repository.unique_room_name(session, payload.home_id, payload.name)
        room = Room(**payload.model_dump())
        session.add(room)
        session.flush()
        record_event(
            session,
            home_id=room.home_id,
            event_type="room.created",
            description=f"Создана комната «{room.name}».",
            details={"room_id": room.id, "room_name": room.name},
        )
        result = room_response(room, 0)
    return result


def update_room(session: Session, room_id: int, payload: RoomPatch) -> RoomRead:
    with write_transaction(session):
        room = repository.require_room(session, room_id)
        changes = payload.model_dump(exclude_unset=True)
        if "name" in changes:
            repository.unique_room_name(session, room.home_id, changes["name"], room.id)
        before = {key: getattr(room, key) for key in changes}
        for key, value in changes.items():
            setattr(room, key, value)
        session.flush()
        record_event(
            session,
            home_id=room.home_id,
            event_type="room.updated",
            description=f"Изменена комната «{room.name}».",
            details={"room_id": room.id, "before": before, "after": changes},
        )
        result = room_response(room, repository.device_count(session, room.id))
    return result


def delete_room(session: Session, room_id: int, move_devices_to: int | None) -> None:
    with write_transaction(session):
        room = repository.require_room(session, room_id)
        devices = repository.room_devices(session, room.id)
        if devices and move_devices_to is None:
            raise Conflict("В комнате есть устройства. Укажите комнату для переноса.")
        if move_devices_to is not None:
            if move_devices_to == room.id:
                raise InvalidCommand("Нельзя перенести устройства в удаляемую комнату.")
            target = repository.require_room(session, move_devices_to)
            if target.home_id != room.home_id:
                raise Conflict("Комната назначения должна принадлежать тому же дому.")
            for device in devices:
                device.room_id = target.id
                record_event(
                    session,
                    home_id=room.home_id,
                    device_id=device.id,
                    event_type="device.moved",
                    description=f"Перенос «{device.name}».",
                    details={
                        "device_name": device.name,
                        "from_room_id": room.id,
                        "to_room_id": target.id,
                    },
                )
            session.flush()
        record_event(
            session,
            home_id=room.home_id,
            event_type="room.deleted",
            description=f"Удалена комната «{room.name}».",
            details={
                "room_id": room.id,
                "room_name": room.name,
                "moved_devices": len(devices),
                "move_devices_to": move_devices_to,
            },
        )
        session.delete(room)
