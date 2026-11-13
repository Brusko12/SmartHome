export type Home = { id: number; name: string; timezone: string };
export type Room = {
  id: number;
  home_id: number;
  name: string;
  icon: string;
  device_count: number;
};
export type DeviceType =
  "light" | "thermostat" | "outlet" | "motion_sensor" | "climate_sensor" | "tv";
export type Device = {
  id: number;
  room_id: number;
  home_id: number;
  name: string;
  device_type: DeviceType;
  adapter_type: string;
  parameters: Record<string, unknown>;
  state: {
    values: Record<string, unknown>;
    updated_at: string;
    source: string;
  };
};
export type Page<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};
export type Dashboard = {
  home: Home;
  rooms: number;
  devices: number;
  powered_devices: number;
  active_automations: number;
  temperature: number | null;
  recent_events: {
    id: number;
    description: string;
    status: string;
    created_at: string;
  }[];
};
export const deviceNames: Record<DeviceType, string> = {
  light: "Умная лампа",
  thermostat: "Термостат",
  outlet: "Умная розетка",
  motion_sensor: "Датчик движения",
  climate_sensor: "Температура и влажность",
  tv: "Телевизор",
};
