import { useState } from "react";
import { Plus, Play, Zap, Pencil, Trash2 } from "lucide-react";
import { useHome } from "../hooks/useHome";
import { useResource } from "../hooks/useResource";
import { api } from "../services/api";
import { Modal } from "../components/Modal";
import {
  ActionsEditor,
  ConditionsEditor,
  TriggerEditor,
} from "../components/AutomationEditors";
import type {
  Action,
  Automation,
  Condition,
  Execution,
  Trigger,
} from "../types/automation";

const statuses: Record<string, string> = {
  success: "Выполнено",
  partial: "Выполнено частично",
  error: "Ошибка",
  skipped: "Пропущено",
};
export function RunButton({
  automation,
  onDone,
}: {
  automation: Automation;
  onDone?: () => void;
}) {
  const { refresh } = useHome();
  const [busy, setBusy] = useState(false),
    [result, setResult] = useState<Execution | null>(null),
    [error, setError] = useState("");
  return (
    <>
      <button
        className="secondary"
        disabled={busy || !automation.enabled}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            setResult(
              await api<Execution>(
                `/automations/${automation.id}/execute`,
                "POST",
              ),
            );
            await refresh();
            onDone?.();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <Play size={15} />
        {automation.kind === "rule" ? "Проверить" : "Запустить"}
      </button>
      {error && (
        <p role="alert" className="error small">
          {error}
        </p>
      )}
      {result && (
        <Modal
          title={statuses[result.status] ?? result.status}
          onClose={() => setResult(null)}
        >
          <p>{automation.name}</p>
          {result.reason === "conditions_not_met" && (
            <p>Условия не выполнены. Устройства не изменены.</p>
          )}
          {result.actions.map((a) => (
            <div className="event-line" key={a.index}>
              <b>{a.index + 1}</b>
              <span>{statuses[a.status]}</span>
              {a.message && <span>{a.message}</span>}
            </div>
          ))}
        </Modal>
      )}
    </>
  );
}
function AutomationForm({
  row,
  scenarios,
  onClose,
  onSaved,
}: {
  row?: Automation;
  scenarios: Automation[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const { home, devices } = useHome();
  const [kind, setKind] = useState<"scenario" | "rule">(
      row?.kind ?? "scenario",
    ),
    [trigger, setTrigger] = useState<Trigger>(
      row?.trigger ?? { type: "state_changed", device_id: devices[0]?.id ?? 0 },
    ),
    [actions, setActions] = useState<Action[]>(row?.actions ?? []),
    [conditions, setConditions] = useState<Condition[]>(row?.conditions ?? []),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <Modal
      title={
        row ? "Изменить сценарий или правило" : "Новый сценарий или правило"
      }
      onClose={onClose}
    >
      <form
        className="automation-builder"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          const data = new FormData(e.currentTarget);
          const payload = {
            name: data.get("name"),
            kind,
            enabled: data.get("enabled") === "on",
            trigger: kind === "rule" ? trigger : null,
            conditions,
            actions,
            ...(row ? {} : { home_id: home!.id }),
          };
          try {
            await api(
              row ? `/automations/${row.id}` : "/automations",
              row ? "PATCH" : "POST",
              payload,
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
            aria-label="Название сценария"
            name="name"
            autoFocus
            required
            maxLength={200}
            defaultValue={row?.name ?? ""}
          />
        </label>
        <label>
          Тип
          <select
            aria-label="Тип автоматизации"
            value={kind}
            onChange={(e) => setKind(e.target.value as typeof kind)}
          >
            <option value="scenario">Ручной сценарий</option>
            <option value="rule">Автоматическое правило</option>
          </select>
        </label>
        <label className="check">
          <input
            name="enabled"
            type="checkbox"
            defaultChecked={row?.enabled ?? true}
          />
          Включено
        </label>
        {kind === "rule" && (
          <TriggerEditor value={trigger} onChange={setTrigger} />
        )}
        <ConditionsEditor value={conditions} onChange={setConditions} />
        <ActionsEditor
          value={actions}
          onChange={setActions}
          scenarios={scenarios.filter((s) => s.id !== row?.id)}
        />
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="primary" disabled={busy || !actions.length}>
          Сохранить
        </button>
      </form>
    </Modal>
  );
}
export function QuickScenes() {
  const { home } = useHome();
  const { items } = useResource<Automation>(
    home ? `/automations?home_id=${home.id}&kind=scenario` : null,
  );
  const enabled = items.filter((s) => s.enabled);
  if (!enabled.length) return null;
  return (
    <>
      <div className="section-heading">
        <h2>Быстрые сценарии</h2>
      </div>
      <div className="scenario-grid">
        {enabled.map((s) => (
          <article className="panel scenario-quick" key={s.id}>
            <Zap size={20} />
            <h3>{s.name}</h3>
            <RunButton automation={s} />
          </article>
        ))}
      </div>
    </>
  );
}
export function AutomationsPage() {
  const { home, refresh: refreshHome } = useHome();
  const {
    items,
    loaded,
    error: loadError,
    refresh,
  } = useResource<Automation>(home ? `/automations?home_id=${home.id}` : null);
  const [edit, setEdit] = useState<Automation | null | undefined>(),
    [error, setError] = useState("");
  if (!home) return <div className="empty">Сначала настройте дом.</div>;
  return (
    <>
      <div className="page-title">
        <div>
          <p className="eyebrow">ДОМ РАБОТАЕТ ЗА ВАС</p>
          <h1>Сценарии и автоматизации</h1>
          <p className="muted">Объединяйте действия и настраивайте правила.</p>
        </div>
        <button className="primary" onClick={() => setEdit(null)}>
          <Plus size={17} />
          Создать
        </button>
      </div>
      {(error || loadError) && (
        <p role="alert" className="error">
          {error || loadError}
        </p>
      )}
      {!loaded ? (
        <p role="status">Загрузка…</p>
      ) : items.length ? (
        <div className="automation-grid">
          {items.map((row) => (
            <article className="panel automation-card" key={row.id}>
              <div className="row">
                <Zap size={20} />
                <span className="small muted">
                  {row.kind === "rule"
                    ? "Автоматическое правило"
                    : "Ручной сценарий"}
                </span>
                <label className="check">
                  <input
                    aria-label={`Включить ${row.name}`}
                    type="checkbox"
                    checked={row.enabled}
                    onChange={async (e) => {
                      try {
                        await api(`/automations/${row.id}`, "PATCH", {
                          enabled: e.target.checked,
                        });
                        await refresh();
                        await refreshHome();
                      } catch (e) {
                        setError((e as Error).message);
                      }
                    }}
                  />
                  Активно
                </label>
              </div>
              <h2>{row.name}</h2>
              <p className="muted small">
                Действий: {row.actions.length} · Условий:{" "}
                {row.conditions.length}
              </p>
              <p className="updated">
                {row.last_run_at
                  ? `Последний запуск: ${new Date(row.last_run_at).toLocaleString("ru-RU")}`
                  : "Ещё не запускался"}
              </p>
              <div className="row">
                <RunButton automation={row} onDone={() => void refresh()} />
                <button
                  className="icon-button"
                  aria-label={`Изменить ${row.name}`}
                  onClick={() => setEdit(row)}
                >
                  <Pencil size={17} />
                </button>
                <button
                  className="icon-button"
                  aria-label={`Удалить ${row.name}`}
                  onClick={async () => {
                    if (!window.confirm(`Удалить «${row.name}»?`)) return;
                    try {
                      await api(`/automations/${row.id}`, "DELETE");
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
      ) : (
        <div className="empty">
          <Zap size={34} />
          <h3>Ваш первый сценарий</h3>
          <p>
            Создайте набор команд или правило «триггер → условия → действия».
          </p>
        </div>
      )}
      {edit !== undefined && (
        <AutomationForm
          row={edit ?? undefined}
          scenarios={items.filter((s) => s.kind === "scenario")}
          onClose={() => setEdit(undefined)}
          onSaved={() => {
            void refresh();
            void refreshHome();
          }}
        />
      )}
    </>
  );
}
