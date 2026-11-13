from typing import Annotated

from fastapi import APIRouter, Path, Query, Response

from app.api.dependencies import AdaptersDep, SessionDep
from app.api.errors import ERROR_RESPONSES
from app.schemas.devices import DevicePage, DeviceRead, StateRead
from app.schemas.entities import CommandRequest, DeviceCreate, DevicePatch, DeviceType
from app.services import devices

router = APIRouter(prefix="/devices", tags=["devices"], responses=ERROR_RESPONSES)
DeviceId = Annotated[int, Path(gt=0)]


@router.get("", response_model=DevicePage)
def list_devices(
    session: SessionDep,
    adapters: AdaptersDep,
    home_id: Annotated[int | None, Query(gt=0)] = None,
    room_id: Annotated[int | None, Query(gt=0)] = None,
    device_type: DeviceType | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DevicePage:
    return devices.list_devices(session, adapters, home_id, room_id, device_type, limit, offset)


@router.post("", response_model=DeviceRead, status_code=201)
def create_device(payload: DeviceCreate, session: SessionDep, adapters: AdaptersDep) -> DeviceRead:
    return devices.create_device(session, adapters, payload)


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device_id: DeviceId, session: SessionDep, adapters: AdaptersDep) -> DeviceRead:
    return devices.get_device(session, adapters, device_id)


@router.patch("/{device_id}", response_model=DeviceRead)
def update_device(
    device_id: DeviceId,
    payload: DevicePatch,
    session: SessionDep,
    adapters: AdaptersDep,
) -> DeviceRead:
    return devices.update_device(session, adapters, device_id, payload)


@router.delete("/{device_id}", status_code=204)
def delete_device(device_id: DeviceId, session: SessionDep) -> Response:
    devices.delete_device(session, device_id)
    return Response(status_code=204)


@router.get("/{device_id}/state", response_model=StateRead)
def get_state(device_id: DeviceId, session: SessionDep, adapters: AdaptersDep) -> StateRead:
    return devices.get_state(session, adapters, device_id)


@router.post("/{device_id}/command", response_model=StateRead)
def execute_command(
    device_id: DeviceId,
    payload: CommandRequest,
    session: SessionDep,
    adapters: AdaptersDep,
) -> StateRead:
    return devices.execute_command(session, adapters, device_id, payload)
