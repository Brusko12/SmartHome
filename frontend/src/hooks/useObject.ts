import { useCallback, useEffect, useState } from "react";
import { api } from "../services/api";
export function useObject<T>(path: string | null, poll = 0) {
  const [data, setData] = useState<T | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true);
  const refresh = useCallback(async () => {
    if (!path) {
      setLoading(false);
      return;
    }
    try {
      setData(await api<T>(path));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [path]);
  useEffect(() => {
    void refresh();
    if (!poll) return;
    const timer = setInterval(() => void refresh(), poll * 1000);
    return () => clearInterval(timer);
  }, [refresh, poll]);
  return { data, error, loading, refresh };
}
