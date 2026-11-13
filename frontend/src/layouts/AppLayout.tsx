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
} from "lucide-react";
import { useHome } from "../hooks/useHome";
export function AppLayout() {
  const { home, loaded, error, refresh } = useHome();
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
            {error ? "Нет соединения" : "Система доступна"}
          </span>
        </header>
        <main className="main-content">
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
