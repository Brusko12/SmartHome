from pydantic import Field

from app.schemas.entities import InputModel


class HomeSettings(InputModel):
    ui_poll_interval: int = Field(default=3, ge=1, le=30)
    simulation_enabled: bool = True
    simulation_interval: float = Field(default=1, ge=0.2, le=60)
    thermostat_rate: float = Field(default=0.6, gt=0, le=5)
    ambient_temperature: float = Field(default=20, ge=-10, le=40)
