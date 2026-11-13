import type { Page } from "../types/domain";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export function csrfToken() {
  return decodeURIComponent(
    document.cookie
      .split("; ")
      .find((v) => v.startsWith("smarthome_csrf="))
      ?.split("=")[1] ?? "",
  );
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const csrf = document.cookie
    .split("; ")
    .find((v) => v.startsWith("smarthome_csrf="))
    ?.split("=")[1];
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (csrf) headers["X-CSRF-Token"] = decodeURIComponent(csrf);
  const response = await fetch(`/api${path}`, {
    method,
    headers,
    credentials: "same-origin",
    cache: "no-store",
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("smarthome-auth-expired"));
    let message = `Ошибка HTTP ${response.status}`;
    try {
      const data = await response.json();
      message =
        data.detail?.message ??
        (Array.isArray(data.detail)
          ? data.detail.map((e: { msg: string }) => e.msg).join("; ")
          : typeof data.detail === "string"
            ? data.detail
            : message);
    } catch {
      /* No structured response. */
    }
    throw new ApiError(response.status, message);
  }
  return response.status === 204
    ? (undefined as T)
    : ((await response.json()) as T);
}
export async function all<T>(path: string): Promise<T[]> {
  const result: T[] = [];
  let offset = 0;
  for (;;) {
    const page = await api<Page<T>>(
      `${path}${path.includes("?") ? "&" : "?"}limit=100&offset=${offset}`,
    );
    result.push(...page.items);
    offset += page.items.length;
    if (offset >= page.total || !page.items.length) return result;
  }
}
