from fastapi import APIRouter, Query, Response
from pydantic import BaseModel

from app.api.dependencies import AdaptersDep, SessionDep
from app.core.errors import InvalidCommand
from app.schemas.system import ConfirmInput
from app.services import demo

router = APIRouter(tags=["demo"])


class DemoRead(BaseModel):
    created: bool
    devices: int | None = None
    scenarios: int | None = None
    message: str | None = None


@router.post("/demo", response_model=DemoRead)
def seed(
    payload: ConfirmInput, session: SessionDep, adapters: AdaptersDep, home_id: int = Query(gt=0)
):
    if not payload.confirm:
        raise InvalidCommand("Подтвердите создание демонстрационного дома.")
    return demo.seed(session, adapters, home_id)


@router.post("/demo/skip", status_code=204)
def skip(session: SessionDep, home_id: int = Query(gt=0)):
    demo.skip(session, home_id)
    return Response(status_code=204)
