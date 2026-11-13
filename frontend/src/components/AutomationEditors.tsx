import { ArrowUp, ArrowDown, Trash2, Plus } from "lucide-react";
import { useHome } from "../hooks/useHome";
import type {
  Action,
  Automation,
  Condition,
  Trigger,
} from "../types/automation";
import type { DeviceType } from "../types/domain";

const commands: Record<DeviceType, string[]> = {
  light: ["turn_on", "turn_off", "set_brightness", "set_color"],
  outlet: ["turn_on", "turn_off"],
  thermostat: ["set_target_temperature", "set_mode"],
  tv: ["turn_on", "turn_off", "set_volume", "mute"],
  motion_sensor: ["simulate_motion", "reset_motion"],
  climate_sensor: ["simulate_reading"],
};
const names: Record<string, string> = {
  turn_on: "Включить",
  turn_off: "Выключить",
  set_brightness: "Яркость",
  set_color: "Цвет",
  set_target_temperature: "Целевая температура",
  set_mode: "Режим",
  set_volume: "Громкость",
  mute: "Без звука",
  simulate_motion: "Симулировать движение",
  reset_motion: "Сбросить движение",
  simulate_reading: "Показания датчика",
  power: "Питание",
  brightness: "Яркость",
  temperature: "Температура",
  humidity: "Влажность",
  current_temperature: "Текущая температура",
  target_temperature: "Целевая температура",
  motion: "Движение",
  volume: "Громкость",
  muted: "Без звука",
  color: "Цвет",
  mode: "Режим",
  current_power_w: "Мощность",
  energy_kwh: "Энергия",
  reset_at: "Срок сброса",
  last_motion_at: "Последнее движение",
};
function defaults(command: string): Record<string, unknown> {
  return command === "set_brightness"
    ? { brightness: 60 }
    : command === "set_color"
      ? { color: "#FFFFFF" }
      : command === "set_target_temperature"
        ? { temperature: 22 }
        : command === "set_mode"
          ? { mode: "Eco" }
          : command === "set_volume"
            ? { volume: 30 }
            : command === "mute"
              ? { muted: true }
              : command === "simulate_reading"
                ? { temperature: 21, humidity: 45 }
                : {};
}
export function ActionsEditor({
  value,
  onChange,
  scenarios = [],
}: {
  value: Action[];
  onChange: (a: Action[]) => void;
  scenarios?: Automation[];
}) {
  const { devices } = useHome();
  function update(i: number, a: Action) {
    onChange(value.map((old, n) => (n === i ? a : old)));
  }
  function move(i: number, delta: number) {
    const copy = [...value];
    [copy[i], copy[i + delta]] = [copy[i + delta], copy[i]];
    onChange(copy);
  }
  return (
    <section className="editor-section">
      <div className="section-heading">
        <h3>Действия по порядку</h3>
        <button
          type="button"
          className="secondary"
          disabled={!devices.length || value.length >= 64}
          onClick={() =>
            onChange([
              ...value,
              {
                type: "command",
                device_id: devices[0].id,
                command: commands[devices[0].device_type][0],
                params: defaults(commands[devices[0].device_type][0]),
              },
            ])
          }
        >
          <Plus size={15} />
          Действие
        </button>
      </div>
      {value.map((a, i) => (
        <div className="action-row" key={i}>
          <div className="row">
            <b className="step-number">{i + 1}</b>
            <select
              aria-label={`Тип действия ${i + 1}`}
              value={a.type}
              onChange={(e) =>
                update(
                  i,
                  e.target.value === "scenario"
                    ? { type: "scenario", automation_id: scenarios[0]?.id ?? 0 }
                    : {
                        type: "command",
                        device_id: devices[0]?.id ?? 0,
                        command:
                          commands[devices[0]?.device_type ?? "light"][0],
                        params: defaults(commands[devices[0]?.device_type ?? "light"][0]),
                      },
                )
              }
            >
              <option value="command">Команда устройства</option>
              <option value="scenario" disabled={!scenarios.length}>
                Запустить сценарий
              </option>
            </select>
            <button
              type="button"
              className="icon-button"
              disabled={!i}
              aria-label={`Поднять действие ${i + 1}`}
              onClick={() => move(i, -1)}
            >
              <ArrowUp size={15} />
            </button>
            <button
              type="button"
              className="icon-button"
              disabled={i === value.length - 1}
              aria-label={`Опустить действие ${i + 1}`}
              onClick={() => move(i, 1)}
            >
              <ArrowDown size={15} />
            </button>
            <button
              type="button"
              className="icon-button"
              aria-label={`Удалить действие ${i + 1}`}
              onClick={() => onChange(value.filter((_, n) => n !== i))}
            >
              <Trash2 size={15} />
            </button>
          </div>
          {a.type === "scenario" ? (
            <select
              aria-label={`Сценарий действия ${i + 1}`}
              value={a.automation_id}
              onChange={(e) =>
                update(i, { ...a, automation_id: Number(e.target.value) })
              }
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          ) : (
            <>
              <select
                aria-label={`Устройство действия ${i + 1}`}
                value={a.device_id}
                onChange={(e) => {
                  const device = devices.find(
                    (d) => d.id === Number(e.target.value),
                  )!;
                  const cmd = commands[device.device_type][0];
                  update(i, {
                    ...a,
                    device_id: device.id,
                    command: cmd,
                    params: defaults(cmd),
                  });
                }}
              >
                {!devices.some((d) => d.id === a.device_id) && (
                  <option value={a.device_id}>
                    Удалённое устройство #{a.device_id}
                  </option>
                )}
                {devices.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
              <select
                aria-label={`Команда действия ${i + 1}`}
                value={a.command}
                onChange={(e) =>
                  update(i, {
                    ...a,
                    command: e.target.value,
                    params: defaults(e.target.value),
                  })
                }
              >
                {commands[
                  devices.find((d) => d.id === a.device_id)?.device_type ??
                    "light"
                ].map((cmd) => (
                  <option key={cmd} value={cmd}>
                    {names[cmd]}
                  </option>
                ))}
              </select>
              {Object.entries(a.params).map(([key, v]) => (
                <label key={key}>
                  {names[key] ?? key}
                  {key === "mode" ? (
                    <select
                      aria-label={`Параметр ${key} действия ${i + 1}`}
                      value={String(v)}
                      onChange={(e) =>
                        update(i, {
                          ...a,
                          params: { ...a.params, [key]: e.target.value },
                        })
                      }
                    >
                      {["Off", "Heating", "Cooling", "Auto", "Eco"].map((v) => (
                        <option key={v}>{v}</option>
                      ))}
                    </select>
                  ) : typeof v === "boolean" ? (
                    <select
                      aria-label={`Параметр ${key} действия ${i + 1}`}
                      value={String(v)}
                      onChange={(e) =>
                        update(i, {
                          ...a,
                          params: {
                            ...a.params,
                            [key]: e.target.value === "true",
                          },
                        })
                      }
                    >
                      <option value="true">Да</option>
                      <option value="false">Нет</option>
                    </select>
                  ) : (
                    <input
                      aria-label={`Параметр ${key} действия ${i + 1}`}
                      required
                      type={key === "color" ? "color" : "number"}
                      step="any"
                      value={String(v)}
                      onChange={(e) =>
                        update(i, {
                          ...a,
                          params: {
                            ...a.params,
                            [key]:
                              key === "color"
                                ? e.target.value
                                : Number(e.target.value),
                          },
                        })
                      }
                    />
                  )}
                </label>
              ))}
            </>
          )}
          <label className="check">
            <input
              type="checkbox"
              checked={!!a.optional}
              onChange={(e) => update(i, { ...a, optional: e.target.checked })}
            />
            Пропустить, если цель удалена
          </label>
        </div>
      ))}
      {!value.length && (
        <p className="muted small">Добавьте хотя бы одно действие.</p>
      )}
    </section>
  );
}
export function ConditionsEditor({
  value,
  onChange,
}: {
  value: Condition[];
  onChange: (c: Condition[]) => void;
}) {
  const { devices } = useHome();
  const fields = (id: number) =>
    Object.entries(devices.find((d) => d.id === id)?.state.values ?? {})
      .filter(([, v]) => v !== null)
      .map(([k]) => k);
  function set(i: number, c: Condition) {
    onChange(value.map((old, n) => (n === i ? c : old)));
  }
  return (
    <section>
      <div className="section-heading">
        <h3>Условия · все должны выполняться</h3>
        <button
          type="button"
          className="secondary"
          disabled={!devices.length}
          onClick={() => {
            const d = devices[0],
              field = fields(d.id)[0];
            onChange([
              ...value,
              {
                device_id: d.id,
                field,
                op: "eq",
                value: d.state.values[field],
              },
            ]);
          }}
        >
          Добавить
        </button>
      </div>
      {value.map((c, i) => {
        const current = devices.find((d) => d.id === c.device_id)?.state.values[
          c.field
        ];
        const numeric = typeof current === "number";
        return (
          <div className="condition-row" key={i}>
            <select
              aria-label={`Устройство условия ${i + 1}`}
              value={c.device_id}
              onChange={(e) => {
                const d = devices.find((d) => d.id === Number(e.target.value))!;
                const field = fields(d.id)[0];
                set(i, {
                  device_id: d.id,
                  field,
                  op: "eq",
                  value: d.state.values[field],
                });
              }}
            >
              {devices.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
            <select
              aria-label={`Параметр условия ${i + 1}`}
              value={c.field}
              onChange={(e) =>
                set(i, {
                  ...c,
                  field: e.target.value,
                  op: "eq",
                  value: devices.find((d) => d.id === c.device_id)?.state
                    .values[e.target.value],
                })
              }
            >
              {fields(c.device_id).map((f) => (
                <option key={f} value={f}>
                  {names[f] ?? f}
                </option>
              ))}
            </select>
            <select
              aria-label={`Сравнение ${i + 1}`}
              value={c.op}
              onChange={(e) =>
                set(i, {
                  ...c,
                  op: e.target.value as Condition["op"],
                  ...(e.target.value === "between"
                    ? { upper: Number(c.value) + 1 }
                    : {}),
                })
              }
            >
              {[
                ["eq", "Равно"],
                ["ne", "Не равно"],
                ...(numeric
                  ? [
                      ["gt", "Выше"],
                      ["lt", "Ниже"],
                      ["between", "В диапазоне"],
                    ]
                  : []),
              ].map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
            {typeof current === "boolean" ? (
              <select
                aria-label={`Значение условия ${i + 1}`}
                value={String(c.value)}
                onChange={(e) =>
                  set(i, { ...c, value: e.target.value === "true" })
                }
              >
                <option value="true">Да</option>
                <option value="false">Нет</option>
              </select>
            ) : (
              <input
                aria-label={`Значение условия ${i + 1}`}
                required
                type={numeric ? "number" : "text"}
                step="any"
                value={String(c.value ?? "")}
                onChange={(e) =>
                  set(i, {
                    ...c,
                    value: numeric ? Number(e.target.value) : e.target.value,
                  })
                }
              />
            )}
            {c.op === "between" && (
              <input
                aria-label={`Верхняя граница ${i + 1}`}
                type="number"
                step="any"
                required
                value={c.upper ?? 0}
                onChange={(e) =>
                  set(i, { ...c, upper: Number(e.target.value) })
                }
              />
            )}
            <button
              type="button"
              className="icon-button"
              aria-label={`Удалить условие ${i + 1}`}
              onClick={() => onChange(value.filter((_, n) => n !== i))}
            >
              <Trash2 size={15} />
            </button>
          </div>
        );
      })}
    </section>
  );
}
export function TriggerEditor({
  value,
  onChange,
}: {
  value: Trigger;
  onChange: (t: Trigger) => void;
}) {
  const { devices } = useHome();
  const eligible = devices.filter((d) =>
    value.type === "motion" ? d.device_type === "motion_sensor" : true,
  );
  const selected = devices.find((d) => d.id === value.device_id);
  const fields = Object.entries(selected?.state.values ?? {})
    .filter(([, v]) => value.type !== "threshold" || typeof v === "number")
    .map(([k]) => k);
  return (
    <section className="trigger-editor">
      <h3>Когда запускать</h3>
      <label>
        Триггер
        <select
          aria-label="Триггер"
          value={value.type}
          onChange={(e) => {
            const type = e.target.value as Trigger["type"];
            const device =
              type === "motion"
                ? devices.find((d) => d.device_type === "motion_sensor")
                : devices[0];
            onChange(
              type === "time"
                ? { type, hour: 7, minute: 0, weekdays: [0, 1, 2, 3, 4, 5, 6] }
                : type === "threshold"
                  ? {
                      type,
                      device_id: device?.id ?? 0,
                      field:
                        Object.entries(device?.state.values ?? {}).find(
                          ([, v]) => typeof v === "number",
                        )?.[0] ?? "temperature",
                      direction: "above",
                      value: 25,
                    }
                  : { type, device_id: device?.id ?? 0 },
            );
          }}
        >
          {[
            ["motion", "Обнаружение движения"],
            ["state_changed", "Изменение состояния"],
            ["threshold", "Пересечение порога"],
            ["time", "Наступление времени"],
          ].map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
      </label>
      {value.type === "time" ? (
        <>
          <label>
            Время
            <input
              aria-label="Время триггера"
              type="time"
              required
              value={`${String(value.hour ?? 7).padStart(2, "0")}:${String(value.minute ?? 0).padStart(2, "0")}`}
              onChange={(e) => {
                const [hour, minute] = e.target.value.split(":").map(Number);
                onChange({ ...value, hour, minute });
              }}
            />
          </label>
          <Weekdays
            value={value.weekdays ?? []}
            onChange={(weekdays) => onChange({ ...value, weekdays })}
          />
        </>
      ) : (
        <>
          <label>
            Устройство
            <select
              aria-label="Устройство триггера"
              required
              value={value.device_id ?? ""}
              onChange={(e) => {
                const d = devices.find((d) => d.id === Number(e.target.value))!;
                onChange({
                  ...value,
                  device_id: d.id,
                  ...(value.type === "threshold"
                    ? {
                        field:
                          Object.entries(d.state.values).find(
                            ([, v]) => typeof v === "number",
                          )?.[0] ?? "",
                      }
                    : { field: undefined }),
                });
              }}
            >
              <option value="" disabled>
                Выберите устройство
              </option>
              {eligible.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>
          {value.type !== "motion" && (
            <label>
              Параметр
              <select
                aria-label="Параметр триггера"
                value={value.field ?? ""}
                onChange={(e) =>
                  onChange({ ...value, field: e.target.value || undefined })
                }
              >
                {value.type === "state_changed" && (
                  <option value="">Любой параметр</option>
                )}
                {fields.map((f) => (
                  <option key={f} value={f}>
                    {names[f] ?? f}
                  </option>
                ))}
              </select>
            </label>
          )}
          {value.type === "threshold" && (
            <div className="row">
              <select
                aria-label="Направление порога"
                value={value.direction}
                onChange={(e) =>
                  onChange({
                    ...value,
                    direction: e.target.value as "above" | "below",
                  })
                }
              >
                <option value="above">Станет выше</option>
                <option value="below">Станет ниже</option>
              </select>
              <input
                aria-label="Порог"
                type="number"
                step="any"
                required
                value={value.value ?? 25}
                onChange={(e) =>
                  onChange({ ...value, value: Number(e.target.value) })
                }
              />
            </div>
          )}
        </>
      )}
    </section>
  );
}
export function Weekdays({
  value,
  onChange,
}: {
  value: number[];
  onChange: (days: number[]) => void;
}) {
  return (
    <fieldset className="weekdays">
      <legend>Дни недели</legend>
      {["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"].map((d, i) => (
        <label key={d}>
          <input
            type="checkbox"
            checked={value.includes(i)}
            onChange={(e) =>
              onChange(
                e.target.checked
                  ? [...value, i].sort()
                  : value.filter((n) => n !== i),
              )
            }
          />
          {d}
        </label>
      ))}
    </fieldset>
  );
}
