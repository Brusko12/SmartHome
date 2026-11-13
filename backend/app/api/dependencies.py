import asyncio
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.adapters.registry import AdapterRegistry
from app.core.errors import Unauthorized


async def get_session(request: Request) -> AsyncIterator[Session]:
    await asyncio.to_thread(request.app.state.gate.acquire)
    try:
        if (
            getattr(request.state, "auth_epoch", request.app.state.auth_epoch)
            != request.app.state.auth_epoch
        ):
            raise Unauthorized("Сессия обновилась. Выполните вход.")
        with request.app.state.database.sessions() as session:
            yield session
    finally:
        request.app.state.gate.release()


def get_adapters(request: Request) -> AdapterRegistry:
    return request.app.state.adapters


SessionDep = Annotated[Session, Depends(get_session)]
AdaptersDep = Annotated[AdapterRegistry, Depends(get_adapters)]
