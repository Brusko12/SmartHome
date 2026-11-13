export type Health = {
  status: "ok" | "degraded";
  version: string;
  database: "ok" | "unavailable" | "migration_required";
};
