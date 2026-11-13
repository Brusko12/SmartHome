import { useState } from "react";
import { Clock, Plus, Pencil, Trash2 } from "lucide-react";
import { useHome } from "../hooks/useHome";
import { useResource } from "../hooks/useResource";
import { api } from "../services/api";
import { Modal } from "../components/Modal";
import { ActionsEditor, Weekdays } from "../components/AutomationEditors";
import type { Action, Automation } from "../types/automation";

type Schedule = {
  id: number;
  name: string;
  enabled: boolean;
  hour: number;
  minute: number;
  weekdays: number[];
  automation_id: number | null;
  actions: Action[];
  next_run_at: string | null;
  last_run_at: string | null;
};
function ScheduleForm({
  row,
  scenarios,
  onClose,
  onSaved,
}: {
  row?: Schedule;
  scenarios: Automation[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const { home } = useHome();
  const [days, setDays] = useState(row?.weekdays ?? [0, 1, 2, 3, 4, 5, 6]),
    [mode, setMode] = useState(
      row?.automation_id
        ? "scenario"
        : row
          ? "actions"
          : scenarios.length
            ? "scenario"
            : "actions",
    ),
    [actions, setActions] = useState<Action[]>(row?.actions ?? []),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <Modal
      title={row ? "Изменить расписание" : "Новое расписание"}
      onClose={onClose}
    >
      <form
        className="automation-builder"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          const f = new FormData(e.currentTarget);
          const [hour, minute] = String(f.get("time")).split(":").map(Number);
          try {
            await api(
              row ? `/schedules/${row.id}` : "/schedules",
              row ? "PATCH" : "POST",
              {
                ...(row ? {} : { home_id: home!.id }),
                name: f.get("name"),
                enabled: f.get("enabled") === "on",
                hour,
                minute,
                weekdays: days,
                automation_id:
                  mode === "scenario" ? Number(f.get("scenario")) : null,
                actions: mode === "actions" ? actions : [],
              },
            );
            onSaved();
            onClose();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Название
          <input
            aria-label="Название расписания"
            name="name"
            autoFocus
            required
            maxLength={200}
            defaultValue={row?.name ?? ""}
          />
        </label>
        <label>
          Время · {home?.timezone}
          <input
            aria-label="Время расписания"
            name="time"
            type="time"
            required
            defaultValue={`${String(row?.hour ?? 7).padStart(2, "0")}:${String(row?.minute ?? 0).padStart(2, "0")}`}
          />
        </label>
        <Weekdays value={days} onChange={setDays} />
        <label className="check">
          <input
            type="checkbox"
            name="enabled"
            defaultChecked={row?.enabled ?? true}
          />
          Включено
        </label>
        <label>
          Что выполнить
          <select
            aria-label="Цель расписания"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option value="scenario" disabled={!scenarios.length}>
              Запустить сценарий
            </option>
            <option value="actions">Выполнить действия</option>
          </select>
        </label>
        {mode === "scenario" ? (
          <label>
            Сценарий
            <select
              aria-label="Сценарий расписания"
              name="scenario"
              required
              defaultValue={row?.automation_id ?? scenarios[0]?.id ?? ""}
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                  {s.enabled ? "" : " (выключен)"}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <ActionsEditor
            value={actions}
            onChange={setActions}
            scenarios={scenarios}
          />
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button
          className="primary"
          disabled={
            busy || !days.length || (mode === "actions" && !actions.length)
          }
        >
          Сохранить
        </button>
      </form>
    </Modal>
  );
}
export function SchedulesPage() {
  const { home } = useHome();
  const {
    items,
    error: loadError,
    loaded,
    refresh,
  } = useResource<Schedule>(home ? `/schedules?home_id=${home.id}` : null);
  const { items: scenarios } = useResource<Automation>(
    home ? `/automations?home_id=${home.id}&kind=scenario` : null,
  );
  const [edit, setEdit] = useState<Schedule | null | undefined>(),
    [error, setError] = useState("");
  if (!home) return <div className="empty">Сначала настройте дом.</div>;
  return (
    <>
      <div className="page-title">
        <div>
          <p className="eyebrow">ПРИВЫЧНЫЙ РИТМ ЖИЗНИ</p>
          <h1>Расписания</h1>
          <p className="muted">
            Часовой пояс: {home.timezone}. Выполняются, пока SmartHome открыт.
          </p>
        </div>
        <button className="primary" onClick={() => setEdit(null)}>
          <Plus size={17} />
          Добавить расписание
        </button>
      </div>
      {(error || loadError) && (
        <p role="alert" className="error">
          {error || loadError}
        </p>
      )}
      {!loaded ? (
        <p role="status">Загрузка…</p>
      ) : !items.length ? (
        <div className="empty">
          <Clock size={34} />
          <h3>Дайте дому расписание</h3>
          <p>Выберите время, дни недели и действия.</p>
        </div>
      ) : (
        <div className="automation-grid">
          {items.map((row) => (
            <article key={row.id} className="panel automation-card">
              <div className="row">
                <Clock size={20} />
                <span className="schedule-time">
                  {String(row.hour).padStart(2, "0")}:
                  {String(row.minute).padStart(2, "0")}
                </span>
                <label className="check">
                  <input
                    aria-label={`Включить ${row.name}`}
                    type="checkbox"
                    checked={row.enabled}
                    onChange={async (e) => {
                      try {
                        await api(`/schedules/${row.id}`, "PATCH", {
                          enabled: e.target.checked,
                        });
                        await refresh();
                      } catch (e) {
                        setError((e as Error).message);
                      }
                    }}
                  />
                  Активно
                </label>
              </div>
              <h2>{row.name}</h2>
              <p className="small muted">
                {row.weekdays
                  .map((n) => ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][n])
                  .join(" · ")}
              </p>
              <p className="updated">
                {row.next_run_at
                  ? `Следующий запуск: ${new Date(row.next_run_at).toLocaleString("ru-RU", { timeZone: home.timezone })}`
                  : "Расписание выключено"}
              </p>
              <p className="small muted">
                {row.automation_id
                  ? (scenarios.find((s) => s.id === row.automation_id)?.name ??
                    "Сценарий")
                  : `Действий: ${row.actions.length}`}
              </p>
              <div className="row">
                <button className="secondary" onClick={() => setEdit(row)}>
                  <Pencil size={15} />
                  Изменить
                </button>
                <button
                  className="icon-button"
                  aria-label={`Удалить ${row.name}`}
                  onClick={async () => {
                    if (!window.confirm(`Удалить расписание «${row.name}»?`))
                      return;
                    try {
                      await api(`/schedules/${row.id}`, "DELETE");
                      await refresh();
                    } catch (e) {
                      setError((e as Error).message);
                    }
                  }}
                >
                  <Trash2 size={17} />
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
      {edit !== undefined && (
        <ScheduleForm
          row={edit ?? undefined}
          scenarios={scenarios}
          onClose={() => setEdit(undefined)}
          onSaved={() => void refresh()}
        />
      )}
    </>
  );
}
