from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.adapters.registry import AdapterRegistry


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.database.sessions() as session:
        yield session


def get_adapters(request: Request) -> AdapterRegistry:
    return request.app.state.adapters


SessionDep = Annotated[Session, Depends(get_session)]
AdaptersDep = Annotated[AdapterRegistry, Depends(get_adapters)]
