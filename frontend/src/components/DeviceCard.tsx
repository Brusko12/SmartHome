import { useState } from "react";
import {
  Lightbulb,
  Thermometer,
  Plug,
  Activity,
  Tv,
  Power,
  Settings2,
} from "lucide-react";
import { useHome } from "../hooks/useHome";
import { deviceNames } from "../types/domain";
import type { Device } from "../types/domain";

export function DeviceCard({
  device,
  onEdit,
}: {
  device: Device;
  onEdit?: (d: Device) => void;
}) {
  const { rooms, act } = useHome();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const s = device.state.values;
  const kind = device.device_type;
  const Icon =
    kind === "light"
      ? Lightbulb
      : kind === "outlet"
        ? Plug
        : kind === "tv"
          ? Tv
          : kind === "motion_sensor"
            ? Activity
            : Thermometer;
  async function send(command: string, params: Record<string, unknown> = {}) {
    setBusy(true);
    setError("");
    try {
      await act(`/devices/${device.id}/command`, "POST", { command, params });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <article
      className={`device-card ${s.power ? "is-on" : ""}`}
      aria-label={device.name}
    >
      <div className="device-top">
        <span className="device-icon">
          <Icon size={23} />
        </span>
        <span className="device-room">
          {rooms.find((r) => r.id === device.room_id)?.name}
        </span>
        {onEdit && (
          <button
            className="icon-button"
            aria-label={`Изменить ${device.name}`}
            onClick={() => onEdit(device)}
          >
            <Settings2 size={17} />
          </button>
        )}
      </div>
      <h3>{device.name}</h3>
      <p className="muted small">{deviceNames[kind]}</p>
      <div className="device-controls" aria-busy={busy}>
        {"power" in s && (
          <button
            disabled={busy}
            className={`power-button ${s.power ? "active" : ""}`}
            onClick={() => void send(s.power ? "turn_off" : "turn_on")}
            aria-label={`${s.power ? "Выключить" : "Включить"} ${device.name}`}
          >
            <Power size={17} />
            {s.power ? "Включено" : "Выключено"}
          </button>
        )}
        {kind === "light" && (
          <>
            <label>
              Яркость <span>{String(s.brightness)}%</span>
              <input
                aria-label={`Яркость ${device.name}`}
                disabled={busy}
                type="range"
                min="0"
                max="100"
                value={Number(s.brightness)}
                onChange={(e) =>
                  void send("set_brightness", {
                    brightness: Number(e.target.value),
                  })
                }
              />
            </label>
            <label className="inline-label">
              Цвет
              <input
                aria-label={`Цвет ${device.name}`}
                disabled={busy}
                type="color"
                value={String(s.color)}
                onChange={(e) =>
                  void send("set_color", { color: e.target.value })
                }
              />
            </label>
          </>
        )}
        {kind === "thermostat" && (
          <>
            <div className="reading">
              {Number(s.current_temperature).toFixed(1)}
              <small> °C</small>
            </div>
            <label>
              Целевая температура
              <input
                aria-label={`Цель ${device.name}`}
                type="number"
                min="5"
                max="35"
                step="0.5"
                defaultValue={Number(s.target_temperature)}
                key={String(s.target_temperature)}
                disabled={busy}
                onBlur={(e) => {
                  if (
                    e.target.value &&
                    Number(e.target.value) !== s.target_temperature
                  )
                    void send("set_target_temperature", {
                      temperature: Number(e.target.value),
                    });
                }}
              />
            </label>
            <select
              aria-label={`Режим ${device.name}`}
              disabled={busy}
              value={String(s.mode)}
              onChange={(e) => void send("set_mode", { mode: e.target.value })}
            >
              {["Off", "Heating", "Cooling", "Auto", "Eco"].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </>
        )}
        {kind === "outlet" && (
          <div className="reading-pair">
            <span>
              <b>{String(s.current_power_w)}</b> Вт
            </span>
            <span>
              <b>{Number(s.energy_kwh).toFixed(3)}</b> кВт·ч
            </span>
          </div>
        )}
        {kind === "tv" && (
          <>
            <label>
              Громкость <span>{String(s.volume)}%</span>
              <input
                aria-label={`Громкость ${device.name}`}
                disabled={busy}
                type="range"
                min="0"
                max="100"
                value={Number(s.volume)}
                onChange={(e) =>
                  void send("set_volume", { volume: Number(e.target.value) })
                }
              />
            </label>
            <button
              disabled={busy}
              className="secondary"
              onClick={() => void send("mute", { muted: !s.muted })}
            >
              {s.muted ? "Включить звук" : "Без звука"}
            </button>
          </>
        )}
        {kind === "motion_sensor" && (
          <>
            <p className={`sensor-state ${s.motion ? "detected" : ""}`}>
              {s.motion ? "Движение обнаружено" : "Нет движения"}
            </p>
            <button
              disabled={busy}
              className="secondary"
              onClick={() =>
                void send(s.motion ? "reset_motion" : "simulate_motion")
              }
            >
              {s.motion ? "Сбросить движение" : "Симулировать движение"}
            </button>
          </>
        )}
        {kind === "climate_sensor" && (
          <>
            <div className="reading-pair">
              <span>
                <b>{Number(s.temperature).toFixed(1)}°</b> температура
              </span>
              <span>
                <b>{String(s.humidity)}%</b> влажность
              </span>
            </div>
            <form
              className="sensor-form"
              onSubmit={(e) => {
                e.preventDefault();
                const form = new FormData(e.currentTarget);
                void send("simulate_reading", {
                  temperature: Number(form.get("temperature")),
                  humidity: Number(form.get("humidity")),
                });
              }}
            >
              <input
                aria-label={`Температура ${device.name}`}
                name="temperature"
                type="number"
                min="-40"
                max="125"
                step="0.1"
                defaultValue={Number(s.temperature)}
                required
              />
              <input
                aria-label={`Влажность ${device.name}`}
                name="humidity"
                type="number"
                min="0"
                max="100"
                step="0.1"
                defaultValue={Number(s.humidity)}
                required
              />
              <button className="secondary" disabled={busy}>
                Задать показания
              </button>
            </form>
          </>
        )}
      </div>
      {error && (
        <p className="error small" role="alert">
          {error}
        </p>
      )}
      <p className="updated">
        Обновлено{" "}
        {new Date(device.state.updated_at).toLocaleTimeString("ru-RU")}
      </p>
    </article>
  );
}
