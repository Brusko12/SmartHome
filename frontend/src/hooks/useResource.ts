import { useCallback, useEffect, useRef, useState } from "react";
import { all } from "../services/api";
import { useHome } from "./useHome";
export function useResource<T>(path: string | null) {
  const { home } = useHome();
  const poll = home?.settings?.ui_poll_interval ?? 3;
  const [items, setItems] = useState<T[]>([]);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const sequence = useRef(0);
  const refresh = useCallback(async () => {
    const id = ++sequence.current;
    if (!path) {
      setItems([]);
      setLoaded(true);
      return;
    }
    try {
      const rows = await all<T>(path);
      if (id === sequence.current) {
        setItems(rows);
        setError("");
        setLoaded(true);
      }
    } catch (e) {
      if (id === sequence.current) {
        setError((e as Error).message);
        setLoaded(true);
      }
    }
  }, [path]);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => void refresh(), poll * 1000);
    return () => {
      clearInterval(timer);
      sequence.current++;
    };
  }, [refresh, poll]);
  return { items, error, loaded, refresh };
}
