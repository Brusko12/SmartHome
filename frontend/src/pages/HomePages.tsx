import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import {
  Plus,
  ArrowUpRight,
  House,
  Layers,
  Power,
  Zap,
  Thermometer,
  Trash2,
  Pencil,
  Sofa,
  Bed,
  CookingPot,
  Bath,
} from "lucide-react";
import { useHome } from "../hooks/useHome";
import { DeviceCard } from "../components/DeviceCard";
import { Modal } from "../components/Modal";
import { deviceNames } from "../types/domain";
import type { Device, DeviceType, Room } from "../types/domain";
import { QuickScenes } from "./AutomationsPage";
import { DemoOffer } from "./SystemPages";

function RoomGlyph({ name }: { name: string }) {
  const Icon =
    (
      { sofa: Sofa, bed: Bed, "cooking-pot": CookingPot, bath: Bath } as Record<
        string,
        typeof House
      >
    )[name] ?? House;
  return <Icon size={26} />;
}

export function DashboardPage() {
  const { home, dashboard: d, devices } = useHome();
  if (!home || !d) return <EmptyHome />;
  return (
    <>
      <div className="page-title">
        <div>
          <p className="eyebrow">ВСЁ ПОД КОНТРОЛЕМ</p>
          <h1>{home.name}</h1>
          <p className="muted">Ваш дом, в котором всё на своём месте.</p>
        </div>
        <span className="local-tag">Локальное управление</span>
      </div>
      <DemoOffer />
      <div className="stat-grid">
        {[
          [House, "Комнаты", d.rooms],
          [Layers, "Устройства", d.devices],
          [Power, "Включено", d.powered_devices],
          [Zap, "Активные правила", d.active_automations],
          [
            Thermometer,
            "Температура",
            d.temperature === null ? "Нет датчика" : `${d.temperature} °C`,
          ],
        ].map(([Icon, label, value]) => {
          const I = Icon as typeof House;
          return (
            <article className="stat" key={String(label)}>
              <I size={19} />
              <strong>{String(value)}</strong>
              <span>{String(label)}</span>
            </article>
          );
        })}
      </div>
      <QuickScenes />
      <div className="section-heading">
        <h2>Устройства дома</h2>
        <Link to="/devices">
          Все устройства <ArrowUpRight size={16} />
        </Link>
      </div>
      {devices.length ? (
        <div className="device-grid">
          {devices.slice(0, 6).map((d) => (
            <DeviceCard key={d.id} device={d} />
          ))}
        </div>
      ) : (
        <div className="empty">
          <Layers />
          <h3>Добавьте первое устройство</h3>
          <p>Виртуальные устройства помогут познакомиться с системой.</p>
          <Link className="primary" to="/devices">
            К устройствам
          </Link>
        </div>
      )}
      <div className="section-heading">
        <h2>Последние события</h2>
      </div>
      <div className="panel">
        {d.recent_events.length ? (
          d.recent_events.map((e) => (
            <div className="event-line" key={e.id}>
              <span className={`event-dot ${e.status}`} />
              <span>{e.description}</span>
              <time>
                {new Date(e.created_at).toLocaleTimeString("ru-RU", {
                  timeZone: home.timezone,
                })}
              </time>
            </div>
          ))
        ) : (
          <p className="muted">Здесь появятся события вашего дома.</p>
        )}
      </div>
    </>
  );
}
export function EmptyHome() {
  return (
    <div className="empty">
      <House size={40} />
      <h1>Добро пожаловать в SmartHome</h1>
      <p>
        Дом ещё не настроен. Первоначальная настройка пока доступна командой{" "}
        <code>python -m app.database.setup</code> из каталога backend.
      </p>
    </div>
  );
}

function RoomForm({ room, onClose }: { room?: Room; onClose: () => void }) {
  const { home, act } = useHome();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Modal
      title={room ? "Изменить комнату" : "Новая комната"}
      onClose={onClose}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          const f = new FormData(e.currentTarget);
          try {
            await act(
              room ? `/rooms/${room.id}` : "/rooms",
              room ? "PATCH" : "POST",
              {
                ...(room ? {} : { home_id: home!.id }),
                name: f.get("name"),
                icon: f.get("icon"),
              },
            );
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
            autoFocus
            name="name"
            required
            maxLength={200}
            defaultValue={room?.name ?? ""}
          />
        </label>
        <label>
          Иконка
          <select
            aria-label="Иконка"
            name="icon"
            defaultValue={room?.icon ?? "house"}
          >
            {[
              ["house", "Дом"],
              ["sofa", "Гостиная"],
              ["bed", "Спальня"],
              ["cooking-pot", "Кухня"],
              ["bath", "Ванная"],
            ].map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="primary" disabled={busy}>
          Сохранить
        </button>
      </form>
    </Modal>
  );
}
function DeleteRoom({ room, onClose }: { room: Room; onClose: () => void }) {
  const { rooms, act } = useHome();
  const [error, setError] = useState("");
  return (
    <Modal title={`Удалить «${room.name}»?`} onClose={onClose}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const target = new FormData(e.currentTarget).get("target");
          try {
            await act(
              `/rooms/${room.id}${room.device_count ? `?move_devices_to=${target}` : ""}`,
              "DELETE",
            );
            onClose();
          } catch (e) {
            setError((e as Error).message);
          }
        }}
      >
        <p>
          Устройства не будут удалены.
          {room.device_count
            ? " Выберите комнату для переноса."
            : " Комната пуста."}
        </p>
        {room.device_count > 0 && (
          <label>
            Перенести устройства
            <select
              aria-label="Перенести устройства"
              name="target"
              required
              defaultValue=""
            >
              <option value="" disabled>
                Выберите комнату
              </option>
              {rooms
                .filter((r) => r.id !== room.id)
                .map((r) => (
                  <option value={r.id} key={r.id}>
                    {r.name}
                  </option>
                ))}
            </select>
          </label>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="danger">Подтвердить удаление</button>
      </form>
    </Modal>
  );
}
export function RoomsPage() {
  const { home, rooms } = useHome();
  const [edit, setEdit] = useState<Room | null | undefined>(undefined);
  const [remove, setRemove] = useState<Room | null>(null);
  if (!home) return <EmptyHome />;
  return (
    <>
      <div className="page-title">
        <div>
          <p className="eyebrow">ПРОСТРАНСТВО ДОМА</p>
          <h1>Комнаты</h1>
          <p className="muted">Отдельное пространство для каждой части дома.</p>
        </div>
        <button className="primary" onClick={() => setEdit(null)}>
          <Plus size={18} />
          Добавить комнату
        </button>
      </div>
      <div className="room-grid">
        {rooms.map((r) => (
          <article className="room-card" key={r.id}>
            <RoomGlyph name={r.icon} />
            <h2>{r.name}</h2>
            <p className="muted">Устройств: {r.device_count}</p>
            <div className="row">
              <Link to={`/devices?room=${r.id}`}>
                Открыть <ArrowUpRight size={16} />
              </Link>
              <button
                className="icon-button"
                aria-label={`Изменить комнату ${r.name}`}
                onClick={() => setEdit(r)}
              >
                <Pencil size={17} />
              </button>
              <button
                className="icon-button"
                aria-label={`Удалить комнату ${r.name}`}
                onClick={() => setRemove(r)}
              >
                <Trash2 size={17} />
              </button>
            </div>
          </article>
        ))}
      </div>
      {!rooms.length && (
        <div className="empty">
          <House />
          <h3>Комнат пока нет</h3>
          <p>Создайте комнату, чтобы разместить устройства.</p>
        </div>
      )}
      {edit !== undefined && (
        <RoomForm room={edit ?? undefined} onClose={() => setEdit(undefined)} />
      )}
      {remove && <DeleteRoom room={remove} onClose={() => setRemove(null)} />}
    </>
  );
}

function DeviceForm({
  device,
  onClose,
}: {
  device?: Device;
  onClose: () => void;
}) {
  const { rooms, act } = useHome();
  const [kind, setKind] = useState<DeviceType>(device?.device_type ?? "light");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Modal
      title={device ? "Изменить устройство" : "Новое устройство"}
      onClose={onClose}
    >
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          const f = new FormData(e.currentTarget);
          const parameters =
            kind === "outlet"
              ? { nominal_power_w: Number(f.get("parameter")) }
              : kind === "motion_sensor"
                ? { reset_after_seconds: Number(f.get("parameter")) }
                : {};
          try {
            await act(
              device ? `/devices/${device.id}` : "/devices",
              device ? "PATCH" : "POST",
              {
                name: f.get("name"),
                room_id: Number(f.get("room")),
                ...(device ? {} : { device_type: kind }),
                parameters,
              },
            );
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
            autoFocus
            name="name"
            required
            maxLength={200}
            defaultValue={device?.name ?? ""}
          />
        </label>
        <label>
          Комната
          <select
            name="room"
            aria-label="Комната"
            required
            defaultValue={device?.room_id ?? rooms[0]?.id ?? ""}
          >
            <option value="" disabled>
              Выберите комнату
            </option>
            {rooms.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
        {!device && (
          <label>
            Тип устройства
            <select
              aria-label="Тип устройства"
              value={kind}
              onChange={(e) => setKind(e.target.value as DeviceType)}
            >
              {Object.entries(deviceNames).map(([v, l]) => (
                <option value={v} key={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>
        )}
        {kind === "outlet" && (
          <label>
            Мощность, Вт
            <input
              name="parameter"
              type="number"
              min="0.1"
              max="10000"
              step="0.1"
              required
              defaultValue={Number(device?.parameters.nominal_power_w ?? 60)}
            />
          </label>
        )}
        {kind === "motion_sensor" && (
          <label>
            Интервал сброса, сек
            <input
              name="parameter"
              type="number"
              min="1"
              max="3600"
              required
              defaultValue={Number(
                device?.parameters.reset_after_seconds ?? 30,
              )}
            />
          </label>
        )}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <button className="primary" disabled={busy}>
          Сохранить
        </button>
      </form>
      {device && (
        <button
          className="danger delete-device"
          onClick={async () => {
            if (
              !window.confirm(
                `Удалить устройство «${device.name}»? События останутся в истории.`,
              )
            )
              return;
            try {
              await act(`/devices/${device.id}`, "DELETE");
              onClose();
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          <Trash2 size={16} />
          Удалить устройство
        </button>
      )}
    </Modal>
  );
}
export function DevicesPage() {
  const { home, rooms, devices } = useHome();
  const [params] = useSearchParams();
  const [room, setRoom] = useState(params.get("room") ?? "");
  const [query, setQuery] = useState("");
  const [edit, setEdit] = useState<Device | null | undefined>(undefined);
  if (!home) return <EmptyHome />;
  const filtered = devices.filter(
    (d) =>
      (!room || d.room_id === Number(room)) &&
      d.name.toLocaleLowerCase().includes(query.toLocaleLowerCase()),
  );
  return (
    <>
      <div className="page-title">
        <div>
          <p className="eyebrow">ПОДКЛЮЧЕНО К ВАШЕМУ ДОМУ</p>
          <h1>Устройства</h1>
          <p className="muted">Управляйте каждым устройством в одном месте.</p>
        </div>
        <button
          className="primary"
          disabled={!rooms.length}
          onClick={() => setEdit(null)}
        >
          <Plus size={18} />
          Добавить устройство
        </button>
      </div>
      <div className="filters">
        <input
          aria-label="Поиск устройств"
          placeholder="Найти устройство…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          aria-label="Фильтр комнат"
          value={room}
          onChange={(e) => setRoom(e.target.value)}
        >
          <option value="">Все комнаты</option>
          {rooms.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
      </div>
      <div className="device-grid">
        {filtered.map((d) => (
          <DeviceCard key={d.id} device={d} onEdit={setEdit} />
        ))}
      </div>
      {!filtered.length && (
        <div className="empty">
          <Layers />
          <h3>Устройств пока нет</h3>
          <p>
            {rooms.length
              ? "Добавьте виртуальное устройство или измените фильтр."
              : "Сначала создайте комнату."}
          </p>
        </div>
      )}
      {edit !== undefined && (
        <DeviceForm
          device={edit ?? undefined}
          onClose={() => setEdit(undefined)}
        />
      )}
    </>
  );
}
