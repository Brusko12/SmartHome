import type { Health } from '../types/health';

function isHealth(value: unknown): value is Health {
  if (typeof value !== 'object' || value === null) return false;
  const body = value as Record<string, unknown>;
  return (
    (body.status === 'ok' || body.status === 'degraded') &&
    typeof body.version === 'string' &&
    ['ok', 'unavailable', 'migration_required'].includes(String(body.database))
  );
}

export async function fetchHealth(signal: AbortSignal): Promise<Health> {
  const response = await fetch('/api/health', {
    signal: AbortSignal.any([signal, AbortSignal.timeout(8000)]),
    cache: 'no-store',
  });
  if (!response.ok && response.status !== 503) {
    throw new Error(`Сервер вернул ошибку HTTP ${response.status}.`);
  }
  const body: unknown = await response.json();
  if (!isHealth(body)) throw new Error('Сервер вернул ответ в неизвестном формате.');
  return body;
}
