import { useEffect, useState, useCallback } from "react";
import {
  RefreshCw,
  Download,
  Upload,
  ShieldCheck,
  Activity,
  Database,
  Search,
} from "lucide-react";
import { useHome } from "../hooks/useHome";
import { useAuth } from "../hooks/useAuth";
import { useObject } from "../hooks/useObject";
import { api, csrfToken } from "../services/api";
import { Modal } from "../components/Modal";
import type { Page } from "../types/domain";

type Config = {
  ui_poll_interval: number;
  simulation_enabled: boolean;
  simulation_interval: number;
  thermostat_rate: number;
  ambient_temperature: number;
  demo_choice: string;
};
type Settings = {
  home_id: number;
  name: string;
  timezone: string;
  config: Config;
  version: string;
  database_path: string;
};
type EventRow = {
  id: number;
  device_id: number | null;
  event_type: string;
  source: string;
  status: string;
  description: string;
  created_at: string;
  details: Record<string, unknown>;
};
type Status = {
  backend: string;
  version: string;
  started_at: string;
  database: {
    status: string;
    path: string;
    revision: string;
    integrity: string;
  };
  rooms: number;
  devices: number;
  events: number;
  runtime_running: boolean;
  last_runtime_error: string | null;
  can_shutdown: boolean;
  recent_errors: EventRow[];
};
const sources: Record<string, string> = {
  user: "Пользователь",
  automation: "Автоматизация",
  simulation: "Симуляция",
  manual_simulation: "Ручной тест",
  schedule: "Расписание",
  initialization: "Настройка",
  auth: "Авторизация",
  system: "Система",
  configuration: "Параметры",
};
const labels: Record<string, string> = {
  "device.created": "Устройство добавлено",
  "device.updated": "Устройство изменено",
  "device.deleted": "Устройство удалено",
  "device.moved": "Устройство перенесено",
  "device.state_changed": "Команда устройства",
  "device.command_failed": "Ошибка команды",
  "device.simulated": "Симуляция",
  "automation.created": "Сценарий/правило создано",
  "automation.updated": "Сценарий/правило изменено",
  "automation.deleted": "Сценарий/правило удалено",
  "automation.started": "Запуск сценария/правила",
  "automation.finished": "Результат сценария/правила",
  "automation.skipped": "Условия не выполнены",
  "automation.blocked": "Цепочка остановлена",
  "schedule.started": "Запуск расписания",
  "schedule.finished": "Результат расписания",
  "schedule.created": "Расписание создано",
  "schedule.updated": "Расписание изменено",
  "schedule.deleted": "Расписание удалено",
  "auth.login": "Вход",
  "auth.password_changed": "Пароль изменён",
  "room.created": "Комната создана",
  "room.updated": "Комната изменена",
  "room.deleted": "Комната удалена",
  "settings.updated": "Настройки",
  "demo.created": "Демонстрационный дом",
  "home.created": "Дом создан",
  "database.restored": "Восстановление",
};
const fieldNames: Record<string, string> = {
  power: "Питание",
  brightness: "Яркость",
  color: "Цвет",
  current_temperature: "Текущая температура",
  target_temperature: "Целевая температура",
  mode: "Режим",
  current_power_w: "Мощность, Вт",
  energy_kwh: "Энергия, кВт·ч",
  motion: "Движение",
  temperature: "Температура",
  humidity: "Влажность",
  volume: "Громкость",
  muted: "Без звука",
  last_motion_at: "Последнее движение",
  reset_at: "Срок сброса",
};
const valueText = (v: unknown) =>
  typeof v === "boolean"
    ? v
      ? "Да"
      : "Нет"
    : v === null || v === undefined
      ? "—"
      : typeof v === "number"
        ? Number(v.toFixed(5)).toString()
        : String(v);

export function DemoOffer() {
  const { home, refresh } = useHome();
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  if (!home || home.settings?.demo_choice !== "pending") return null;
  return (
    <section className="demo-offer">
      <div>
        <h2>Познакомьтесь с вашим умным домом</h2>
        <p>
          11 виртуальных устройств, 3 сценария, правило движения и утреннее
          расписание.
        </p>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </div>
      <div className="row">
        <button
          className="primary"
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            try {
              await api(`/demo?home_id=${home.id}`, "POST", { confirm: true });
              await refresh();
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          Создать демонстрационный дом
        </button>
        <button
          className="secondary"
          disabled={busy}
          onClick={async () => {
            try {
              await api(`/demo/skip?home_id=${home.id}`, "POST", {});
              await refresh();
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          Начать с пустым домом
        </button>
      </div>
    </section>
  );
}

export function SettingsPage() {
  const { home, refresh } = useHome();
  const auth = useAuth();
  const {
    data,
    error: loadError,
    refresh: reload,
  } = useObject<Settings>(home ? `/settings?home_id=${home.id}` : null);
  const [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  if (!home) return <div className="empty">Сначала настройте дом.</div>;
  if (!data)
    return <div className="empty">{loadError || "Загрузка настроек…"}</div>;
  return (
    <>
      <div className="page-title">
        <div>
          <p className="eyebrow">УСТРОЙТЕ ВСЁ ПО-СВОЕМУ</p>
          <h1>Настройки</h1>
          <p className="muted">Название дома, симуляция и ваши данные.</p>
        </div>
      </div>
      {(error || loadError) && (
        <p className="error" role="alert">
          {error || loadError}
        </p>
      )}
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
      <div className="settings-grid">
        <section className="panel settings-panel">
          <h2>Ваш дом</h2>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              setBusy(true);
              setError("");
              try {
                await api(`/settings?home_id=${home.id}`, "PATCH", {
                  name: f.get("name"),
                  timezone: f.get("timezone"),
                  config: {
                    ui_poll_interval: Number(f.get("poll")),
                    simulation_enabled: f.get("simulation") === "on",
                    simulation_interval: Number(f.get("interval")),
                    thermostat_rate: Number(f.get("rate")),
                    ambient_temperature: Number(f.get("ambient")),
                  },
                });
                await reload();
                await refresh();
                setMessage("Настройки сохранены.");
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Название дома
              <input
                name="name"
                required
                maxLength={200}
                defaultValue={data.name}
              />
            </label>
            <label>
              Часовой пояс
              <input
                name="timezone"
                required
                defaultValue={data.timezone}
                placeholder="Asia/Yakutsk"
              />
            </label>
            <label>
              Обновление интерфейса, сек
              <input
                name="poll"
                type="number"
                min="1"
                max="30"
                required
                defaultValue={data.config.ui_poll_interval}
              />
            </label>
            <label className="check">
              <input
                name="simulation"
                type="checkbox"
                defaultChecked={data.config.simulation_enabled}
              />
              Включить симуляцию
            </label>
            <label>
              Шаг симуляции, сек
              <input
                name="interval"
                type="number"
                min="0.2"
                max="60"
                step="0.1"
                required
                defaultValue={data.config.simulation_interval}
              />
            </label>
            <label>
              Скорость термостата, °C/мин
              <input
                name="rate"
                type="number"
                min="0.01"
                max="5"
                step="0.01"
                required
                defaultValue={data.config.thermostat_rate}
              />
            </label>
            <label>
              Температура окружающей среды, °C
              <input
                name="ambient"
                type="number"
                min="-10"
                max="40"
                step="0.1"
                required
                defaultValue={data.config.ambient_temperature}
              />
            </label>
            <button className="primary" disabled={busy}>
              Сохранить настройки
            </button>
          </form>
        </section>
        <div className="settings-stack">
          <section className="panel settings-panel">
            <h2>Резервная копия</h2>
            <p className="muted">
              Перенесите дом на другой компьютер или сохраните копию перед
              изменениями.
            </p>
            <a
              className="secondary"
              href="/api/system/backup"
              download="SmartHome-backup.db"
            >
              <Download size={16} />
              Экспортировать базу
            </a>
            <label className="upload-label">
              <Upload size={16} />
              Восстановить из файла
              <input
                aria-label="Файл резервной копии"
                type="file"
                accept=".db,.sqlite,.sqlite3"
                disabled={busy}
                onChange={async (e) => {
                  const input = e.currentTarget;
                  const file = input.files?.[0];
                  if (!file) return;
                  if (file.size > 2 * 1024 * 1024 * 1024) {
                    setError("Максимальный размер копии — 2 ГБ.");
                    input.value = "";
                    return;
                  }
                  if (
                    !window.confirm(
                      "Заменить текущие данные резервной копией? Перед заменой сохранится страховочная копия. После восстановления потребуется вход с паролем из выбранной базы.",
                    )
                  ) {
                    input.value = "";
                    return;
                  }
                  setBusy(true);
                  setError("");
                  try {
                    const response = await fetch("/api/system/restore", {
                      method: "POST",
                      credentials: "same-origin",
                      headers: {
                        "Content-Type": "application/octet-stream",
                        "X-CSRF-Token": csrfToken(),
                        "X-Confirm-Restore": "true",
                      },
                      body: file,
                    });
                    const result = await response.json();
                    if (!response.ok)
                      throw new Error(
                        result.detail?.message ??
                          "Не удалось восстановить базу.",
                      );
                    await auth.refresh(
                      "База восстановлена. Войдите с паролем из резервной копии.",
                    );
                  } catch (e) {
                    setError((e as Error).message);
                  } finally {
                    setBusy(false);
                    input.value = "";
                  }
                }}
              />
            </label>
            <p className="small muted">
              При переносе папки программы пользовательская база автоматически
              не переносится.
            </p>
          </section>
          <section className="panel settings-panel">
            <h2>Пароль локального пользователя</h2>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                if (f.get("new") !== f.get("confirm")) {
                  setError("Новые пароли не совпадают.");
                  return;
                }
                setBusy(true);
                try {
                  await api("/auth/password", "POST", {
                    current_password: f.get("current"),
                    new_password: f.get("new"),
                  });
                  await auth.refresh("Пароль изменён. Войдите снова.");
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label>
                Текущий пароль
                <input
                  name="current"
                  type="password"
                  autoComplete="current-password"
                  required
                />
              </label>
              <label>
                Новый пароль
                <input
                  name="new"
                  type="password"
                  minLength={8}
                  maxLength={1024}
                  autoComplete="new-password"
                  required
                />
              </label>
              <label>
                Повторите новый пароль
                <input
                  name="confirm"
                  type="password"
                  minLength={8}
                  autoComplete="new-password"
                  required
                />
              </label>
              <button className="secondary" disabled={busy}>
                <ShieldCheck size={16} />
                Изменить пароль
              </button>
            </form>
          </section>
          <section className="panel settings-panel">
            <h2>О приложении</h2>
            <p>Версия {data.version}</p>
            <p className="small muted">База данных</p>
            <code className="path">{data.database_path}</code>
            {data.config.demo_choice !== "created" && (
              <button
                className="secondary"
                disabled={busy}
                onClick={async () => {
                  setBusy(true);
                  try {
                    await api(`/demo?home_id=${home.id}`, "POST", {
                      confirm: true,
                    });
                    await refresh();
                    await reload();
                    setMessage("Демонстрационный дом создан.");
                  } catch (e) {
                    setError((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Создать демонстрационный дом
              </button>
            )}
          </section>
        </div>
      </div>
    </>
  );
}

function EventDetail({
  row,
  onClose,
  timezone,
}: {
  row: EventRow;
  onClose: () => void;
  timezone: string;
}) {
  const before = row.details.before as Record<string, unknown> | undefined,
    after = row.details.after as Record<string, unknown> | undefined;
  const steps = row.details.actions as
    { index: number; status: string; message: string }[] | undefined;
  return (
    <Modal title={labels[row.event_type] ?? row.event_type} onClose={onClose}>
      <p>{row.description}</p>
      <dl className="diagnostic-list">
        <dt>Время</dt>
        <dd>
          {new Date(row.created_at).toLocaleString("ru-RU", {
            timeZone: timezone,
          })}
        </dd>
        <dt>Источник</dt>
        <dd>{sources[row.source] ?? row.source}</dd>
        <dt>Статус</dt>
        <dd>
          {row.status === "error"
            ? "Ошибка"
            : row.status === "success"
              ? "Успешно"
              : "Информация"}
        </dd>
      </dl>
      {before && after && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Параметр</th>
                <th>Было</th>
                <th>Стало</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(after).map((key) => (
                <tr key={key}>
                  <td>{fieldNames[key] ?? key}</td>
                  <td>{valueText(before[key])}</td>
                  <td>{valueText(after[key])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {steps?.map((step) => (
        <p className="event-line" key={step.index}>
          Действие {step.index + 1}:{" "}
          {step.status === "success"
            ? "выполнено"
            : step.status === "error"
              ? "ошибка"
              : "пропущено"}{" "}
          {step.message}
        </p>
      ))}
    </Modal>
  );
}
export function HistoryPage() {
  const { home, devices } = useHome();
  const [rows, setRows] = useState<Page<EventRow> | null>(null),
    [types, setTypes] = useState<string[]>([]),
    [eventDevices, setEventDevices] = useState<{ id: number; name: string }[]>(
      [],
    ),
    [error, setError] = useState(""),
    [offset, setOffset] = useState(0),
    [type, setType] = useState(""),
    [device, setDevice] = useState(""),
    [from, setFrom] = useState(""),
    [to, setTo] = useState(""),
    [order, setOrder] = useState("desc"),
    [selected, setSelected] = useState<EventRow | null>(null);
  const query = new URLSearchParams({
    home_id: String(home?.id ?? 0),
    limit: "25",
    offset: String(offset),
    order,
    ...(type ? { event_type: type } : {}),
    ...(device ? { device_id: device } : {}),
    ...(from ? { date_from: from } : {}),
    ...(to ? { date_to: to } : {}),
  }).toString();
  const load = useCallback(async () => {
    if (!home) return;
    try {
      const [page, types, devices] = await Promise.all([
        api<Page<EventRow>>(`/events?${query}`),
        api<string[]>(`/event-types?home_id=${home.id}`),
        api<{ id: number; name: string }[]>(
          `/event-devices?home_id=${home.id}`,
        ),
      ]);
      setRows(page);
      setTypes(types);
      setEventDevices(devices);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, [home?.id, query]);
  useEffect(() => {
    void load();
    const timer = setInterval(
      () => void load(),
      (home?.settings?.ui_poll_interval ?? 3) * 1000,
    );
    return () => clearInterval(timer);
  }, [load, home?.settings?.ui_poll_interval]);
  if (!home) return <div className="empty">Сначала настройте дом.</div>;
  return (
    <>
      <div className="page-title">
        <div>
          <p className="eyebrow">КАЖДОЕ ДЕЙСТВИЕ НА СВОЁМ МЕСТЕ</p>
          <h1>История событий</h1>
          <p className="muted">
            События сохраняются между запусками. Даты — {home.timezone}.
          </p>
        </div>
        <button className="secondary" onClick={() => void load()}>
          <RefreshCw size={16} />
          Обновить
        </button>
      </div>
      <div className="history-filters">
        <label>
          Тип
          <select
            aria-label="Тип события"
            value={type}
            onChange={(e) => {
              setType(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">Все события</option>
            {types.map((t) => (
              <option key={t} value={t}>
                {labels[t] ?? t}
              </option>
            ))}
          </select>
        </label>
        <label>
          Устройство
          <select
            aria-label="Устройство события"
            value={device}
            onChange={(e) => {
              setDevice(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">Все устройства</option>
            {eventDevices.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
                {devices.some((now) => now.id === d.id) ? "" : " (удалено)"}
              </option>
            ))}
          </select>
        </label>
        <label>
          С даты
          <input
            type="date"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <label>
          По дату
          <input
            type="date"
            value={to}
            onChange={(e) => {
              setTo(e.target.value);
              setOffset(0);
            }}
          />
        </label>
        <label>
          Порядок
          <select
            aria-label="Порядок событий"
            value={order}
            onChange={(e) => {
              setOrder(e.target.value);
              setOffset(0);
            }}
          >
            <option value="desc">Сначала новые</option>
            <option value="asc">Сначала старые</option>
          </select>
        </label>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {error ? (
        <div className="empty">
          Не удалось загрузить события. Проверьте фильтры и соединение.
        </div>
      ) : !rows ? (
        <p role="status">Загрузка…</p>
      ) : !rows.total ? (
        <div className="empty">
          <Search size={30} />
          <h3>Событий не найдено</h3>
          <p>Измените фильтры или выполните действие в доме.</p>
        </div>
      ) : (
        <>
          <div className="panel history-list">
            {rows.items.map((row) => (
              <button
                className="history-row"
                key={row.id}
                onClick={() => setSelected(row)}
              >
                <span className={`event-dot ${row.status}`} />
                <div>
                  <strong>{row.description}</strong>
                  <small>
                    {labels[row.event_type] ?? row.event_type} ·{" "}
                    {sources[row.source] ?? row.source}
                  </small>
                </div>
                <time>
                  {new Date(row.created_at).toLocaleString("ru-RU", {
                    timeZone: home.timezone,
                  })}
                </time>
              </button>
            ))}
          </div>
          <div className="pagination">
            <span>
              {offset + 1}–{Math.min(offset + 25, rows.total)} из {rows.total}
            </span>
            <button
              className="secondary"
              disabled={!offset}
              onClick={() => setOffset(Math.max(0, offset - 25))}
            >
              Назад
            </button>
            <button
              className="secondary"
              disabled={offset + 25 >= rows.total}
              onClick={() => setOffset(offset + 25)}
            >
              Далее
            </button>
          </div>
        </>
      )}
      {selected && (
        <EventDetail
          row={selected}
          timezone={home.timezone}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}

export function SystemPage() {
  const auth = useAuth();
  const [stopError, setStopError] = useState("");
  const { home } = useHome();
  const { data, error, refresh } = useObject<Status>(
    "/system/status",
    home?.settings?.ui_poll_interval ?? 3,
  );
  return (
    <>
      <div className="page-title">
        <div>
          <p className="eyebrow">ПРОЗРАЧНОСТЬ И КОНТРОЛЬ</p>
          <h1>Состояние системы</h1>
          <p className="muted">
            Реальные сведения локального сервера и базы данных.
          </p>
        </div>
        <button className="secondary" onClick={() => void refresh()}>
          <RefreshCw size={16} />
          Проверить
        </button>
      </div>
      {(error || stopError) && (
        <p className="error" role="alert">
          {error || stopError}
        </p>
      )}
      {!data ? (
        <p role="status">Загрузка диагностики…</p>
      ) : (
        <>
          <div className="stat-grid">
            {[
              ["Комнаты", data.rooms],
              ["Устройства", data.devices],
              ["События", data.events],
              ["Версия", data.version],
              [
                "SQLite",
                data.database.status === "ok" ? "В порядке" : "Ошибка",
              ],
            ].map(([l, v]) => (
              <article className="stat" key={l}>
                <Database size={18} />
                <strong>{v}</strong>
                <span>{l}</span>
              </article>
            ))}
          </div>
          <section className="panel settings-panel">
            <h2>
              <Activity size={19} />
              Локальная система
            </h2>
            <dl className="diagnostic-list">
              <dt>Backend</dt>
              <dd>{data.backend === "ok" ? "Работает" : "Ошибка"}</dd>
              <dt>Проверка SQLite</dt>
              <dd>{data.database.integrity}</dd>
              <dt>Версия схемы</dt>
              <dd>{data.database.revision}</dd>
              <dt>Фоновые задачи</dt>
              <dd>{data.runtime_running ? "Работают" : "Отключены"}</dd>
              <dt>Запущено</dt>
              <dd>
                {new Date(data.started_at).toLocaleString("ru-RU", {
                  timeZone: home?.timezone ?? "UTC",
                })}
              </dd>
              <dt>База данных</dt>
              <dd className="path">{data.database.path}</dd>
              <dt>Последняя фоновая ошибка</dt>
              <dd>{data.last_runtime_error ?? "Нет"}</dd>
            </dl>
            {data.can_shutdown && (
              <button
                className="danger"
                onClick={async () => {
                  try {
                    await api("/system/shutdown", "POST", {});
                    auth.finish();
                  } catch (e) {
                    setStopError((e as Error).message);
                  }
                }}
              >
                Завершить SmartHome
              </button>
            )}
          </section>
          <div className="section-heading">
            <h2>Последние ошибки</h2>
          </div>
          <section className="panel">
            {data.recent_errors.length ? (
              data.recent_errors.map((e) => (
                <div className="event-line" key={e.id}>
                  <span className="event-dot error" />
                  {e.description}
                  <time>
                    {new Date(e.created_at).toLocaleString("ru-RU", {
                      timeZone: home?.timezone ?? "UTC",
                    })}
                  </time>
                </div>
              ))
            ) : (
              <p className="muted settings-panel">
                Ошибок не зарегистрировано.
              </p>
            )}
          </section>
        </>
      )}
    </>
  );
}
