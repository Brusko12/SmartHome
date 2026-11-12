import { useEffect, useState } from 'react';
import { fetchHealth } from '../services/health';
import type { Health } from '../types/health';

export type HealthState =
  | { kind: 'loading' }
  | { kind: 'ready'; data: Health }
  | { kind: 'error'; message: string };

export function useHealth() {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<HealthState>({ kind: 'loading' });

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ kind: 'ready', data });
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setState({
          kind: 'error',
          message: error instanceof Error
            ? error.message
            : 'Не удалось связаться с локальным сервером.',
        });
      });
    return () => controller.abort();
  }, [attempt]);

  function refresh() {
    setState({ kind: 'loading' });
    setAttempt((value) => value + 1);
  }

  return { state, refresh };
}
