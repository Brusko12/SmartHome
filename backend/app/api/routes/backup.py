import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.background import BackgroundTask

from app.api.errors import ERROR_RESPONSES
from app.api.routes.auth import clear_cookies
from app.core.errors import InvalidCommand
from app.services import backup

router = APIRouter(prefix="/system", tags=["backup"], responses=ERROR_RESPONSES)


class RestoreRead(BaseModel):
    restored: bool
    requires_login: bool
    safety_backup: str


@router.get("/backup")
async def export(request: Request):
    path = await asyncio.to_thread(backup.export_backup, request.app.state)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename="SmartHome-backup.db",
        headers={"Cache-Control": "no-store"},
        background=BackgroundTask(path.unlink, missing_ok=True),
    )


@router.post("/restore", response_model=RestoreRead)
async def restore(request: Request):
    if request.headers.get("x-confirm-restore") != "true":
        raise InvalidCommand("Подтвердите замену текущих данных.")
    handle = tempfile.NamedTemporaryFile(
        prefix=".restore-", suffix=".db", dir=request.app.state.configuration.data_dir, delete=False
    )
    path = Path(handle.name)
    try:
        size = 0
        with handle:
            async for chunk in request.stream():
                size += len(chunk)
                if size > backup.MAX_BACKUP_BYTES:
                    raise HTTPException(status_code=413, detail="Файл превышает 2 ГБ.")
                handle.write(chunk)
        result = await asyncio.to_thread(backup.restore_backup, request.app.state, path)
    finally:
        path.unlink(missing_ok=True)
    response = JSONResponse(result)
    clear_cookies(response)
    return response
