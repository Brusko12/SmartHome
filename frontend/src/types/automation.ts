export type Action =
  | {
      type: "command";
      device_id: number;
      command: string;
      params: Record<string, unknown>;
      optional?: boolean;
    }
  | { type: "scenario"; automation_id: number; optional?: boolean };
export type Condition = {
  device_id: number;
  field: string;
  op: "eq" | "ne" | "gt" | "lt" | "between";
  value: unknown;
  upper?: number;
};
export type Trigger = {
  type: "motion" | "state_changed" | "threshold" | "time";
  device_id?: number;
  field?: string;
  direction?: "above" | "below";
  value?: number;
  hour?: number;
  minute?: number;
  weekdays?: number[];
};
export type Automation = {
  id: number;
  home_id: number;
  name: string;
  kind: "scenario" | "rule";
  enabled: boolean;
  trigger: Trigger | null;
  conditions: Condition[];
  actions: Action[];
  last_run_at: string | null;
};
export type Execution = {
  automation_id: number;
  status: string;
  reason: string;
  actions: { index: number; status: string; message: string }[];
};
