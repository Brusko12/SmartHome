import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { all, api } from "../services/api";
import type { Dashboard, Device, Home, Room } from "../types/domain";

type Data = {
  home: Home | null;
  rooms: Room[];
  devices: Device[];
  dashboard: Dashboard | null;
  loaded: boolean;
  error: string;
  refresh: () => Promise<void>;
  act: (path: string, method?: string, body?: unknown) => Promise<unknown>;
};
const Context = createContext<Data | null>(null);
export function HomeProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState({
    home: null as Home | null,
    rooms: [] as Room[],
    devices: [] as Device[],
    dashboard: null as Dashboard | null,
    loaded: false,
    error: "",
  });
  const sequence = useRef(0);
  const refresh = useCallback(async () => {
    const current = ++sequence.current;
    try {
      const homes = await api<Home[]>("/homes");
      const home = homes[0] ?? null;
      const [rooms, devices, dashboard] = home
        ? await Promise.all([
            all<Room>(`/rooms?home_id=${home.id}`),
            all<Device>(`/devices?home_id=${home.id}`),
            api<Dashboard>(`/dashboard?home_id=${home.id}`),
          ])
        : [[], [], null];
      if (current === sequence.current)
        setData({ home, rooms, devices, dashboard, loaded: true, error: "" });
    } catch (e) {
      if (current === sequence.current)
        setData((d) => ({
          ...d,
          loaded: true,
          error: e instanceof Error ? e.message : "Нет соединения с сервером",
        }));
    }
  }, []);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), 3000);
    return () => {
      clearInterval(timer);
      sequence.current++;
    };
  }, [refresh]);
  const act = useCallback(
    async (path: string, method = "POST", body?: unknown) => {
      const result = await api(path, method, body);
      await refresh();
      return result;
    },
    [refresh],
  );
  return (
    <Context.Provider value={{ ...data, refresh, act }}>
      {children}
    </Context.Provider>
  );
}
export function useHome() {
  const data = useContext(Context);
  if (!data) throw new Error("HomeProvider missing");
  return data;
}
