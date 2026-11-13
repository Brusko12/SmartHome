import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


def default_data_dir() -> Path:
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        root = Path(local) if local else Path.home() / "AppData" / "Local"
    else:
        xdg = os.environ.get("XDG_DATA_HOME")
        root = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return root / "SmartHome" / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SMARTHOME_",
        env_file=PROJECT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Field(default_factory=default_data_dir)
    port: int = Field(default=8000, ge=1024, le=65535)
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    background_tasks: bool = True

    @field_validator("data_dir")
    @classmethod
    def absolute_data_dir(cls, value: Path) -> Path:
        value = value.expanduser()
        if not value.is_absolute():
            raise ValueError("SMARTHOME_DATA_DIR must be an absolute path")
        return value

    @property
    def database_path(self) -> Path:
        return self.data_dir / "smart_home.db"
