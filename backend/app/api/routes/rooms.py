from typing import Annotated

from fastapi import APIRouter, Path, Query, Response

from app.api.dependencies import SessionDep
from app.api.errors import ERROR_RESPONSES
from app.schemas.entities import RoomCreate, RoomPage, RoomPatch, RoomRead
from app.services import rooms

router = APIRouter(prefix="/rooms", tags=["rooms"], responses=ERROR_RESPONSES)
RoomId = Annotated[int, Path(gt=0)]


@router.get("", response_model=RoomPage)
def list_rooms(
    session: SessionDep,
    home_id: Annotated[int | None, Query(gt=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RoomPage:
    return rooms.list_rooms(session, home_id, limit, offset)


@router.post("", response_model=RoomRead, status_code=201)
def create_room(payload: RoomCreate, session: SessionDep) -> RoomRead:
    return rooms.create_room(session, payload)


@router.get("/{room_id}", response_model=RoomRead)
def get_room(room_id: RoomId, session: SessionDep) -> RoomRead:
    return rooms.get_room(session, room_id)


@router.patch("/{room_id}", response_model=RoomRead)
def update_room(room_id: RoomId, payload: RoomPatch, session: SessionDep) -> RoomRead:
    return rooms.update_room(session, room_id, payload)


@router.delete("/{room_id}", status_code=204)
def delete_room(
    room_id: RoomId,
    session: SessionDep,
    move_devices_to: Annotated[int | None, Query(gt=0)] = None,
) -> Response:
    rooms.delete_room(session, room_id, move_devices_to)
    return Response(status_code=204)
