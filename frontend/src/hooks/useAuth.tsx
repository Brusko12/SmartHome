import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { House, ShieldCheck } from "lucide-react";
import { api, ApiError } from "../services/api";

type User = { id: number; username: string };
const Context = createContext<{
  user: User;
  refresh: (message?: string) => Promise<void>;
  finish: () => void;
} | null>(null);
export function AuthBoundary({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null),
    [configured, setConfigured] = useState(true),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [stopped, setStopped] = useState(false);
  async function refresh(message = "") {
    setLoading(true);
    setError("");
    if (message) setNotice(message);
    try {
      setConfigured(
        (await api<{ configured: boolean }>("/auth/status")).configured,
      );
      try {
        setUser(await api<User>("/auth/me"));
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) setUser(null);
        else throw e;
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void refresh();
    const expired = () => {
      setUser(null);
      setConfigured(true);
      setNotice("Сессия завершена. Войдите снова.");
    };
    window.addEventListener("smarthome-auth-expired", expired);
    return () => window.removeEventListener("smarthome-auth-expired", expired);
  }, []);
  if (stopped)
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <h1>SmartHome завершает работу</h1>
          <p className="muted">Данные сохранены. Эту вкладку можно закрыть.</p>
        </div>
      </div>
    );
  if (loading)
    return (
      <div className="auth-screen">
        <div className="auth-card" role="status">
          Подключаемся к вашему дому…
        </div>
      </div>
    );
  if (error)
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <h1>Не удалось подключиться</h1>
          <p className="error" role="alert">
            {error}
          </p>
          <button className="primary" onClick={() => void refresh()}>
            Повторить
          </button>
        </div>
      </div>
    );
  if (!user)
    return (
      <LoginPage
        configured={configured}
        notice={notice}
        onSuccess={() => refresh()}
      />
    );
  return (
    <Context.Provider value={{ user, refresh, finish: () => setStopped(true) }}>
      {children}
    </Context.Provider>
  );
}
function LoginPage({
  configured,
  notice,
  onSuccess,
}: {
  configured: boolean;
  notice: string;
  onSuccess: () => Promise<void>;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="auth-brand">
          <House size={30} />
          <strong>SmartHome</strong>
        </div>
        <p className="eyebrow">ВАШ ДОМ. ВАШИ ПРАВИЛА.</p>
        <h1>{configured ? "Вход в SmartHome" : "Создайте свой умный дом"}</h1>
        <p className="muted">
          {configured
            ? "Войдите в локальную систему управления."
            : "Все данные останутся на этом компьютере."}
        </p>
        {notice && <p className="notice">{notice}</p>}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setError("");
            const f = new FormData(e.currentTarget);
            const username = String(f.get("username")).trim(),
              password = String(f.get("password"));
            if (!configured && password !== f.get("confirm")) {
              setError("Пароли не совпадают.");
              setBusy(false);
              return;
            }
            try {
              await api(
                configured ? "/auth/login" : "/auth/register",
                "POST",
                configured
                  ? { username, password }
                  : {
                      username,
                      password,
                      home_name: f.get("home_name"),
                      timezone: f.get("timezone"),
                    },
              );
              await onSuccess();
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <label>
            Имя пользователя
            <input
              name="username"
              autoComplete="username"
              autoFocus
              required
              maxLength={100}
            />
          </label>
          <label>
            Пароль
            <input
              name="password"
              type="password"
              autoComplete={configured ? "current-password" : "new-password"}
              required
              minLength={configured ? 1 : 8}
              maxLength={1024}
            />
          </label>
          {!configured && (
            <>
              <label>
                Повторите пароль
                <input
                  name="confirm"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                />
              </label>
              <label>
                Название дома
                <input
                  name="home_name"
                  required
                  maxLength={200}
                  defaultValue="Мой дом"
                />
              </label>
              <label>
                Часовой пояс
                <input
                  name="timezone"
                  aria-label="Часовой пояс"
                  required
                  list="zones"
                  defaultValue={
                    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
                  }
                />
                <datalist id="zones">
                  {[
                    "UTC",
                    "Europe/Moscow",
                    "Asia/Yakutsk",
                    "Asia/Vladivostok",
                    "Asia/Novosibirsk",
                    "Europe/Berlin",
                    "America/New_York",
                  ].map((z) => (
                    <option key={z}>{z}</option>
                  ))}
                </datalist>
              </label>
            </>
          )}
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <button className="primary" disabled={busy}>
            {busy ? "Подождите…" : configured ? "Войти" : "Создать дом"}
          </button>
        </form>
        <p className="auth-foot">
          <ShieldCheck size={14} />
          Локальный вход · Без облачного аккаунта
        </p>
      </div>
    </div>
  );
}
export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("AuthBoundary missing");
  return value;
}
