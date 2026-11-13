import json

from sqlalchemy.orm import Session

from app.adapters.contracts import DeviceSnapshot
from app.adapters.registry import AdapterRegistry
from app.core.errors import Conflict, InvalidCommand
from app.database.base import utc_now
from app.database.transactions import write_transaction
from app.models import Device, DeviceState
from app.repositories import entities as repository
from app.schemas.devices import STATE_TYPES, DevicePage, DeviceRead, StateRead
from app.schemas.entities import CommandRequest, DeviceCreate, DevicePatch
from app.services.events import record_event


def snapshot(device: Device) -> DeviceSnapshot:
    if device.state is None:
        raise Conflict("У устройства отсутствует сохранённое состояние.")
    return DeviceSnapshot(device.id, device.device_type, device.parameters, device.state.values)


def state_response(device: Device, adapters: AdapterRegistry) -> StateRead:
    values = adapters.get(device.adapter_type).get_state(snapshot(device))
    return StateRead(
        device_id=device.id,
        device_type=device.device_type,
        values=STATE_TYPES[device.device_type].model_validate_json(json.dumps(values)),
        source=device.state.source,
        updated_at=device.state.updated_at,
    )


def device_response(device: Device, adapters: AdapterRegistry) -> DeviceRead:
    return DeviceRead(
        id=device.id,
        home_id=device.home_id,
        room_id=device.room_id,
        name=device.name,
        device_type=device.device_type,
        adapter_type=device.adapter_type,
        parameters=device.parameters,
        state=state_response(device, adapters),
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


def get_device(session: Session, adapters: AdapterRegistry, device_id: int) -> DeviceRead:
    return device_response(repository.require_device(session, device_id), adapters)


def get_state(session: Session, adapters: AdapterRegistry, device_id: int) -> StateRead:
    return state_response(repository.require_device(session, device_id), adapters)


def list_devices(
    session: Session,
    adapters: AdapterRegistry,
    home_id: int | None,
    room_id: int | None,
    device_type: str | None,
    limit: int,
    offset: int,
) -> DevicePage:
    if home_id is not None:
        repository.require_home(session, home_id)
    if room_id is not None:
        repository.require_room(session, room_id)
    devices, total = repository.list_devices(session, home_id, room_id, device_type, limit, offset)
    return DevicePage(
        items=[device_response(device, adapters) for device in devices],
        total=total,
        limit=limit,
        offset=offset,
    )


def create_device(session: Session, adapters: AdapterRegistry, payload: DeviceCreate) -> DeviceRead:
    with write_transaction(session):
        room = repository.require_room(session, payload.room_id)
        adapter = adapters.get("virtual")
        parameters = adapter.validate_parameters(payload.device_type, payload.parameters)
        device = Device(
            home_id=room.home_id,
            room_id=room.id,
            name=payload.name,
            device_type=payload.device_type,
            adapter_type="virtual",
            parameters=parameters,
        )
        device.state = DeviceState(values=adapter.initial_state(payload.device_type))
        session.add(device)
        session.flush()
        record_event(
            session,
            home_id=device.home_id,
            device_id=device.id,
            event_type="device.created",
            description=f"Создано устройство «{device.name}».",
            details={
                "device_id": device.id,
                "device_name": device.name,
                "device_type": device.device_type,
                "room_id": device.room_id,
            },
        )
        result = device_response(device, adapters)
    return result


def update_device(
    session: Session,
    adapters: AdapterRegistry,
    device_id: int,
    payload: DevicePatch,
) -> DeviceRead:
    with write_transaction(session):
        device = repository.require_device(session, device_id)
        changes = payload.model_dump(exclude_unset=True)
        before = {key: getattr(device, key) for key in changes}
        if "room_id" in changes:
            target = repository.require_room(session, changes["room_id"])
            if target.home_id != device.home_id:
                raise Conflict("Устройство можно переносить только внутри своего дома.")
        if "parameters" in changes:
            adapter = adapters.get(device.adapter_type)
            changes["parameters"] = adapter.validate_parameters(
                device.device_type, changes["parameters"]
            )
            from app.services.simulation import settle

            now = utc_now()
            device.state.values = settle(device, adapter.get_state(snapshot(device)), now)
            device.state.simulated_at = now
        for key, value in changes.items():
            setattr(device, key, value)
        if "parameters" in changes:
            device.state.values = adapters.get(device.adapter_type).get_state(snapshot(device))
            device.state.source = "configuration"
            device.state.updated_at = utc_now()
        session.flush()
        record_event(
            session,
            home_id=device.home_id,
            device_id=device.id,
            event_type="device.updated",
            description=f"Изменено устройство «{device.name}».",
            details={"device_name": device.name, "before": before, "after": changes},
        )
        result = device_response(device, adapters)
    return result


def delete_device(session: Session, device_id: int) -> None:
    with write_transaction(session):
        device = repository.require_device(session, device_id)
        # The deletion event contains a snapshot, not a soon-to-be-deleted FK.
        record_event(
            session,
            home_id=device.home_id,
            event_type="device.deleted",
            description=f"Удалено устройство «{device.name}».",
            details={
                "device_id": device.id,
                "device_name": device.name,
                "device_type": device.device_type,
                "last_state": device.state.values,
            },
        )
        session.delete(device)


def execute_command(
    session: Session,
    adapters: AdapterRegistry,
    device_id: int,
    payload: CommandRequest,
    context=None,
) -> StateRead:
    failure = None
    with write_transaction(session):
        device = repository.require_device(session, device_id)
        home_id = device.home_id
        adapter = adapters.get(device.adapter_type)
        before = adapter.get_state(snapshot(device))
        now = utc_now()
        source = (
            "manual_simulation"
            if payload.command in {"simulate_motion", "reset_motion", "simulate_reading"}
            else "user"
        )
        if context is not None:
            source = context.source
        try:
            from app.services.simulation import settle

            settled = settle(device, before, now)
            current = snapshot(device)
            current = DeviceSnapshot(
                current.device_id, current.device_type, current.parameters, settled
            )
            after = adapter.execute_command(current, payload.command, payload.params, now)
        except InvalidCommand as error:
            failure = error
            record_event(
                session,
                home_id=device.home_id,
                device_id=device.id,
                event_type="device.command_failed",
                status="error",
                source=source,
                description=str(error),
                details={
                    "device_name": device.name,
                    "command": payload.command,
                    "params": payload.params,
                },
            )
        else:
            device.state.values = after
            device.state.source = source
            device.state.updated_at = now
            device.state.simulated_at = now
            device.updated_at = now
            record_event(
                session,
                home_id=device.home_id,
                device_id=device.id,
                event_type="device.state_changed",
                source=source,
                description=f"Выполнена команда {payload.command}: «{device.name}».",
                details={
                    "device_name": device.name,
                    "device_type": device.device_type,
                    "command": payload.command,
                    "params": payload.params,
                    "before": before,
                    "after": after,
                },
            )
            session.flush()
            state_response(device, adapters)
    # A rejected command commits only its error event, never a partial state.
    if failure is not None:
        raise failure
    from app.services.automation_engine import process_change

    process_change(session.get_bind(), adapters, home_id, device_id, before, after, context)
    session.expire_all()
    return get_state(session, adapters, device_id)
