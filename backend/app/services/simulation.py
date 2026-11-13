import math
from datetime import datetime

from app.schemas.settings import HomeSettings


def towards(current: float, goal: float, step: float) -> float:
    return min(current + step, goal) if goal > current else max(current - step, goal)


def advance(
    device_type: str,
    device_id: int,
    values: dict,
    elapsed: float,
    now: datetime,
    config: HomeSettings,
) -> dict:
    result = dict(values)
    if not config.simulation_enabled or elapsed <= 0:
        return result
    if device_type == "outlet":
        result["energy_kwh"] += result["current_power_w"] * elapsed / 3_600_000
    elif device_type == "thermostat":
        current, target, mode = (
            result["current_temperature"],
            result["target_temperature"],
            result["mode"],
        )
        rate = config.thermostat_rate
        if (
            mode == "Off"
            or (mode == "Heating" and current >= target)
            or (mode == "Cooling" and current <= target)
        ):
            goal = config.ambient_temperature
            rate = 0.05
        elif mode == "Eco":
            goal = min(target, 18)
            rate *= 0.5
        else:
            goal = target
        result["current_temperature"] = towards(current, goal, rate * elapsed / 60)
    elif device_type == "climate_sensor":
        phase = now.timestamp() / 180 + device_id
        result["temperature"] = round(config.ambient_temperature + math.sin(phase) * 1.5, 1)
        result["humidity"] = round(45 + math.sin(phase / 1.3) * 10, 1)
    elif device_type == "motion_sensor" and result["motion"] and result.get("reset_at"):
        if datetime.fromisoformat(result["reset_at"]) <= now:
            result.update(motion=False, reset_at=None)
    return result


def settle(device, values, now):
    config = HomeSettings.model_validate(device.home.settings)
    anchor = device.state.simulated_at or device.state.updated_at
    return advance(
        device.device_type, device.id, values, max(0, (now - anchor).total_seconds()), now, config
    )
