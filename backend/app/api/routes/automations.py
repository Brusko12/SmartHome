from typing import Literal

from fastapi import APIRouter, Query, Response

from app.api.dependencies import AdaptersDep, SessionDep
from app.api.errors import ERROR_RESPONSES
from app.schemas.automations import (
    AutomationInput,
    AutomationPage,
    AutomationPatch,
    AutomationRead,
    ExecutionResult,
)
from app.services import automation_engine, automations

router = APIRouter(prefix="/automations", tags=["automations"], responses=ERROR_RESPONSES)


@router.get("", response_model=AutomationPage)
def list_rows(
    session: SessionDep,
    home_id: int = Query(gt=0),
    kind: Literal["scenario", "rule"] | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return automations.list_rows(session, home_id, kind, limit, offset)


@router.post("", response_model=AutomationRead, status_code=201)
def create(payload: AutomationInput, session: SessionDep, adapters: AdaptersDep):
    return automations.create(session, adapters, payload)


@router.get("/{automation_id}", response_model=AutomationRead)
def get(automation_id: int, session: SessionDep):
    return automations.response(automations.require_automation(session, automation_id))


@router.patch("/{automation_id}", response_model=AutomationRead)
def update(
    automation_id: int, payload: AutomationPatch, session: SessionDep, adapters: AdaptersDep
):
    return automations.update(session, adapters, automation_id, payload)


@router.delete("/{automation_id}", status_code=204)
def remove(automation_id: int, session: SessionDep):
    automations.remove(session, automation_id)
    return Response(status_code=204)


@router.post("/{automation_id}/execute", response_model=ExecutionResult)
def execute(automation_id: int, session: SessionDep, adapters: AdaptersDep):
    return automation_engine.execute(session.get_bind(), adapters, automation_id)
