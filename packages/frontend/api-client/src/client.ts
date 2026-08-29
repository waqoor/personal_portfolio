import { z } from "zod";

export type NextRequestOptions = {
  revalidate?: number | false;
  tags?: string[];
};

export type ApiRequestOptions = Omit<RequestInit, "body" | "method"> & {
  next?: NextRequestOptions;
};

export type ApiClientConfig = {
  baseUrl: string;
  fetch?: typeof globalThis.fetch;
  timeoutMs?: number;
  cookie?: string | undefined;
  csrfToken?: string | undefined;
  defaultHeaders?: HeadersInit | undefined;
  onMutationSuccess?:
    | ((request: { method: string; path: string }) => Promise<void> | void)
    | undefined;
};

type ApiErrorBody = {
  code?: string;
  message?: string;
  detail?: string | { message?: string; code?: string };
  request_id?: string;
  errors?: unknown;
};

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId?: string;
  readonly details?: unknown;

  constructor(input: {
    message: string;
    status: number;
    code?: string;
    requestId?: string;
    details?: unknown;
    cause?: unknown;
  }) {
    super(input.message, input.cause === undefined ? undefined : { cause: input.cause });
    this.name = "ApiError";
    this.status = input.status;
    this.code = input.code ?? "api_error";
    if (input.requestId !== undefined) this.requestId = input.requestId;
    if (input.details !== undefined) this.details = input.details;
  }
}

export class ApiContractError extends ApiError {
  constructor(message: string, cause: unknown) {
    super({ message, status: 502, code: "invalid_api_contract", cause });
    this.name = "ApiContractError";
  }
}

function normalizeBaseUrl(value: string): string {
  if (!value.trim()) {
    throw new Error("API base URL is required.");
  }
  return value.replace(/\/$/, "");
}

function buildUrl(baseUrl: string, path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  return `${baseUrl}/${path.replace(/^\//, "")}`;
}

async function readError(response: Response): Promise<ApiErrorBody> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    try {
      return (await response.json()) as ApiErrorBody;
    } catch {
      return {};
    }
  }
  try {
    const detail = await response.text();
    return detail ? { detail } : {};
  } catch {
    return {};
  }
}

function errorMessage(body: ApiErrorBody, fallback: string): string {
  if (typeof body.message === "string") return body.message;
  if (typeof body.detail === "string") return body.detail;
  if (body.detail && typeof body.detail.message === "string") return body.detail.message;
  return fallback;
}

function errorCode(body: ApiErrorBody): string | undefined {
  if (typeof body.code === "string") return body.code;
  if (body.detail && typeof body.detail === "object" && typeof body.detail.code === "string") return body.detail.code;
  return undefined;
}

export class HttpClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof globalThis.fetch;
  private readonly timeoutMs: number;
  private readonly cookie?: string;
  private readonly csrfToken?: string;
  private readonly defaultHeaders?: HeadersInit;
  private readonly onMutationSuccess?: ApiClientConfig["onMutationSuccess"];

  constructor(config: ApiClientConfig) {
    this.baseUrl = normalizeBaseUrl(config.baseUrl);
    this.fetchImpl = config.fetch ?? globalThis.fetch.bind(globalThis);
    this.timeoutMs = config.timeoutMs ?? 10_000;
    if (config.cookie !== undefined) this.cookie = config.cookie;
    if (config.csrfToken !== undefined) this.csrfToken = config.csrfToken;
    if (config.defaultHeaders !== undefined) this.defaultHeaders = config.defaultHeaders;
    if (config.onMutationSuccess !== undefined) this.onMutationSuccess = config.onMutationSuccess;
  }

  get<T>(path: string, schema: z.ZodType<T>, options?: ApiRequestOptions): Promise<T> {
    return this.request(path, schema, { ...options, method: "GET" });
  }

  post<T>(path: string, body: unknown, schema: z.ZodType<T>, options?: ApiRequestOptions): Promise<T> {
    return this.request(path, schema, { ...options, body: JSON.stringify(body), method: "POST" });
  }

  patch<T>(path: string, body: unknown, schema: z.ZodType<T>, options?: ApiRequestOptions): Promise<T> {
    return this.request(path, schema, { ...options, body: JSON.stringify(body), method: "PATCH" });
  }

  put<T>(path: string, body: unknown, schema: z.ZodType<T>, options?: ApiRequestOptions): Promise<T> {
    return this.request(path, schema, { ...options, body: JSON.stringify(body), method: "PUT" });
  }

  delete<T>(path: string, schema: z.ZodType<T>, options?: ApiRequestOptions): Promise<T> {
    return this.request(path, schema, { ...options, method: "DELETE" });
  }

  upload<T>(path: string, body: FormData, schema: z.ZodType<T>, options?: ApiRequestOptions): Promise<T> {
    return this.request(path, schema, { ...options, body, method: "POST" });
  }

  private async request<T>(
    path: string,
    schema: z.ZodType<T>,
    options: ApiRequestOptions & { method: string; body?: BodyInit },
  ): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    const headers = new Headers(this.defaultHeaders);
    new Headers(options.headers).forEach((value, key) => headers.set(key, value));
    headers.set("Accept", "application/json");
    headers.set("X-Requested-With", "portfolio-web");
    if (options.body !== undefined && !(options.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
    if (this.cookie) headers.set("Cookie", this.cookie);
    if (this.csrfToken && options.method !== "GET") headers.set("X-CSRF-Token", this.csrfToken);

    const signal = options.signal
      ? AbortSignal.any([options.signal, controller.signal])
      : controller.signal;

    try {
      const response = await this.fetchImpl(buildUrl(this.baseUrl, path), {
        ...options,
        credentials: options.credentials ?? "include",
        headers,
        signal,
      });

      if (!response.ok) {
        const body = await readError(response);
        const requestId = body.request_id ?? response.headers.get("x-request-id") ?? undefined;
        const code = errorCode(body);
        throw new ApiError({
          message: errorMessage(body, `Request failed with status ${response.status}.`),
          status: response.status,
          ...(code ? { code } : {}),
          ...(requestId ? { requestId } : {}),
          ...(body.errors !== undefined ? { details: body.errors } : {}),
        });
      }

      let payload: unknown;
      if (response.status === 204) {
        payload = undefined;
      } else {
        try {
          payload = await response.json();
        } catch (error) {
          throw new ApiContractError("The API returned an unreadable response.", error);
        }
      }

      const result = schema.safeParse(payload);
      if (!result.success) {
        throw new ApiContractError("The API response did not match the published frontend contract.", result.error);
      }
      if (options.method !== "GET" && this.onMutationSuccess) {
        try {
          await this.onMutationSuccess({ method: options.method, path });
        } catch {
          // The mutation is already committed. Cache invalidation failure must not invite a replay.
        }
      }
      return result.data;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (error instanceof DOMException && error.name === "AbortError") {
        throw new ApiError({
          message: "The request timed out. Please try again.",
          status: 408,
          code: "request_timeout",
          cause: error,
        });
      }
      throw new ApiError({
        message: "The service is temporarily unavailable.",
        status: 503,
        code: "network_unavailable",
        cause: error,
      });
    } finally {
      clearTimeout(timer);
    }
  }
}

export function queryString(values: Record<string, string | number | boolean | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const result = params.toString();
  return result ? `?${result}` : "";
}
