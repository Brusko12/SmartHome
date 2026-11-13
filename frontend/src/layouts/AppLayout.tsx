import { NavLink, Outlet, Link } from "react-router";
import {
  House,
  LayoutDashboard,
  DoorOpen,
  Layers,
  Search,
  ArrowUpRight,
  RefreshCw,
  Zap,
  Clock,
  History,
  Settings,
  Activity,
  LogOut,
} from "lucide-react";
import { useHome } from "../hooks/useHome";
import { useAuth } from "../hooks/useAuth";
import { useState } from "react";
import { api } from "../services/api";
export function AppLayout() {
  const { home, loaded, error, refresh } = useHome();
  const auth = useAuth();
  const [logoutError, setLogoutError] = useState("");
  async function logout() {
    try {
      await api("/auth/logout", "POST", {});
      await auth.refresh("Вы вышли из SmartHome.");
    } catch (e) {
      setLogoutError((e as Error).message);
    }
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" to="/">
          <span>
            <House size={24} />
          </span>
          SmartHome<span className="brand-dot">●</span>
        </Link>
        <p className="nav-label">ВАШЕ ПРОСТРАНСТВО</p>
        <nav>
          <NavLink to="/" end>
            <LayoutDashboard size={19} />
            Главная
          </NavLink>
          <NavLink to="/rooms">
            <DoorOpen size={19} />
            Комнаты
          </NavLink>
          <NavLink to="/devices">
            <Layers size={19} />
            Устройства
          </NavLink>
          <NavLink to="/automations">
            <Zap size={19} />
            Сценарии и правила
          </NavLink>
          <NavLink to="/schedules">
            <Clock size={19} />
            Расписания
          </NavLink>
          <NavLink to="/history">
            <History size={19} />
            История событий
          </NavLink>
          <NavLink to="/settings">
            <Settings size={19} />
            Настройки
          </NavLink>
          <NavLink to="/system">
            <Activity size={19} />
            Состояние системы
          </NavLink>
        </nav>
        <div className="sidebar-bottom">
          <div className="home-avatar">
            <House size={19} />
            <div>
              <strong>{home?.name ?? "SmartHome"}</strong>
              <small>Локальная система</small>
            </div>
          </div>
          <span className="small muted">Данные остаются у вас дома.</span>
          <button
            className="logout-button"
            onClick={async () => {
              try {
                await api("/auth/logout", "POST", {});
                await auth.refresh("Вы вышли из SmartHome.");
              } catch (e) {
                setLogoutError((e as Error).message);
              }
            }}
          >
            <LogOut size={15} />
            Выйти · {auth.user.username}
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span className="breadcrumb">
            Ваш дом <span>/</span> SmartHome
          </span>
          <Link to="/devices" className="search-link">
            <Search size={17} />
            Найти устройство
            <ArrowUpRight size={15} />
          </Link>
          <span className={`connection ${error ? "offline" : ""}`}>
            <i />
            {!loaded
              ? "Подключаемся…"
              : error
                ? "Нет соединения"
                : "Система доступна"}
          </span>
          <button
            className="mobile-logout icon-button"
            aria-label="Выйти"
            onClick={() => void logout()}
          >
            <LogOut size={17} />
          </button>
        </header>
        <main className="main-content">
          {logoutError && (
            <p role="alert" className="error">
              {logoutError}
            </p>
          )}
          {error && (
            <div className="error-banner" role="alert">
              {error}
              <button className="secondary" onClick={() => void refresh()}>
                <RefreshCw size={15} />
                Повторить
              </button>
            </div>
          )}
          {!loaded ? (
            <div className="empty" role="status">
              Загружаем ваш дом…
            </div>
          ) : error && !home ? (
            <div className="empty">
              <h1>Сервер недоступен</h1>
              <p>Проверьте, что локальный SmartHome запущен.</p>
            </div>
          ) : (
            <Outlet />
          )}
          <footer className="app-footer">
            <span>SmartHome · Локальная система управления</span>
            <span>Ваш дом. Ваши правила.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
