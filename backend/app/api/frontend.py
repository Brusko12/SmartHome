from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse


def install_frontend(app, directory: Path):
    root = directory.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API-маршрут не найден.")
        candidate = (root / path).resolve()
        if not candidate.is_relative_to(root):
            raise HTTPException(status_code=404)
        if candidate.is_file():
            return FileResponse(candidate)
        if path.startswith("assets/") or Path(path).suffix:
            raise HTTPException(status_code=404, detail="Ресурс не найден.")
        index = root / "index.html"
        if not index.is_file():
            raise HTTPException(
                status_code=503, detail="Сначала соберите интерфейс командой npm run build."
            )
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
