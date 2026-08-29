import "server-only";

import { createPortfolioApi, type ApiError, type PortfolioApi } from "@portfolio/api-client";
import { cookies } from "next/headers";

function serverBaseUrl(): string {
  return (process.env.API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");
}

export function getPublicApi(): PortfolioApi {
  return createPortfolioApi({
    baseUrl: serverBaseUrl(),
    timeoutMs: 8_000,
    defaultHeaders: { "X-Frontend-Channel": "server" },
  });
}

export async function getAdminApi(csrfToken?: string): Promise<PortfolioApi> {
  const store = await cookies();
  const cookie = store
    .getAll()
    .map(({ name, value }) => `${encodeURIComponent(name)}=${encodeURIComponent(value)}`)
    .join("; ");

  return createPortfolioApi({
    baseUrl: serverBaseUrl(),
    timeoutMs: 10_000,
    cookie,
    ...(csrfToken ? { csrfToken } : {}),
    defaultHeaders: { "X-Frontend-Channel": "server" },
  });
}

export type LoadResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: { code: string; message: string; status: number; requestId?: string } };

export async function loadApi<T>(request: () => Promise<T>): Promise<LoadResult<T>> {
  try {
    return { ok: true, data: await request() };
  } catch (caught) {
    const error = caught as Partial<ApiError>;
    const result: LoadResult<T> = {
      ok: false,
      error: {
        code: error.code ?? "service_unavailable",
        message: error.message ?? "The content service is temporarily unavailable.",
        status: error.status ?? 503,
      },
    };
    if (error.requestId !== undefined) result.error.requestId = error.requestId;
    return result;
  }
}
