import { z } from "zod";
import { ApiContractError, ApiError, HttpClient, queryString } from "./client";

function response(body: unknown, status = 200, headers: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

describe("HttpClient", () => {
  it("rejects an empty base URL", () => {
    expect(() => new HttpClient({ baseUrl: "  " })).toThrow("API base URL is required");
  });

  it("normalizes the base URL and validates successful payloads", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(response({ id: "one" }));
    const client = new HttpClient({ baseUrl: "https://api.example.com/v1/", fetch: fetchMock });

    await expect(client.get("/public/item", z.object({ id: z.string() }))).resolves.toEqual({ id: "one" });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/v1/public/item",
      expect.objectContaining({ method: "GET", credentials: "include" }),
    );
  });

  it("maps API error envelopes without leaking implementation details", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(response(
      { code: "rate_limited", message: "Try again shortly.", request_id: "req-1" },
      429,
    ));
    const client = new HttpClient({ baseUrl: "https://api.example.com", fetch: fetchMock });

    const error = await client.get("/limited", z.unknown()).catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 429, code: "rate_limited", requestId: "req-1" });
  });

  it("fails closed when the response violates the typed contract", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(response({ id: 42 }));
    const client = new HttpClient({ baseUrl: "https://api.example.com", fetch: fetchMock });

    await expect(client.get("/item", z.object({ id: z.string() }))).rejects.toBeInstanceOf(ApiContractError);
  });

  it("sends CSRF and cookie credentials for mutations", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(response({ saved: true }));
    const client = new HttpClient({
      baseUrl: "https://api.example.com",
      fetch: fetchMock,
      cookie: "session=secure",
      csrfToken: "csrf-token",
    });

    await client.post("/admin/item", { title: "Item" }, z.object({ saved: z.boolean() }));
    const init = fetchMock.mock.calls[0]?.[1];
    const headers = new Headers(init?.headers);
    expect(headers.get("cookie")).toBe("session=secure");
    expect(headers.get("x-csrf-token")).toBe("csrf-token");
    expect(headers.get("content-type")).toBe("application/json");
  });

  it("notifies successful mutations without turning invalidation failure into a replayable error", async () => {
    const onMutationSuccess = vi.fn().mockRejectedValue(new Error("cache unavailable"));
    const client = new HttpClient({
      baseUrl: "https://api.example.com",
      fetch: vi.fn<typeof fetch>().mockImplementation(async () => response({ saved: true })),
      onMutationSuccess,
    });

    await expect(
      client.post("/admin/item", { title: "Item" }, z.object({ saved: z.boolean() })),
    ).resolves.toEqual({ saved: true });
    expect(onMutationSuccess).toHaveBeenCalledWith({ method: "POST", path: "/admin/item" });

    await client.get("/public/item", z.object({ saved: z.boolean() }));
    expect(onMutationSuccess).toHaveBeenCalledTimes(1);
  });

  it("supports every mutation verb, absolute URLs, uploads, and caller headers", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (_input, init) => {
      if (init?.method === "DELETE") return new Response(null, { status: 204 });
      return response({ saved: true });
    });
    const client = new HttpClient({
      baseUrl: "https://api.example.com/v1",
      fetch: fetchMock,
      csrfToken: "csrf-token",
      defaultHeaders: { "X-Default": "default" },
    });
    const savedSchema = z.object({ saved: z.boolean() });

    await client.patch("/item", { value: 1 }, savedSchema, {
      headers: { "X-Default": "overridden", "X-Caller": "caller" },
    });
    await client.put("https://uploads.example.com/item", { value: 2 }, savedSchema);
    await client.delete("/item", z.undefined());
    const form = new FormData();
    form.set("file", new Blob(["file"]), "file.txt");
    await client.upload("/media", form, savedSchema);

    expect(fetchMock.mock.calls.map((call) => call[1]?.method)).toEqual([
      "PATCH",
      "PUT",
      "DELETE",
      "POST",
    ]);
    expect(fetchMock.mock.calls[1]?.[0]).toBe("https://uploads.example.com/item");
    const patchHeaders = new Headers(fetchMock.mock.calls[0]?.[1]?.headers);
    expect(patchHeaders.get("x-default")).toBe("overridden");
    expect(patchHeaders.get("x-caller")).toBe("caller");
    const uploadHeaders = new Headers(fetchMock.mock.calls[3]?.[1]?.headers);
    expect(uploadHeaders.has("content-type")).toBe(false);
    expect(uploadHeaders.get("x-csrf-token")).toBe("csrf-token");
  });

  it("accepts empty successful responses and combines caller cancellation", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 204 }));
    const client = new HttpClient({ baseUrl: "https://api.example.com", fetch: fetchMock });
    const caller = new AbortController();

    await expect(
      client.get("/empty", z.undefined(), { signal: caller.signal }),
    ).resolves.toBeUndefined();
    const headers = new Headers(fetchMock.mock.calls[0]?.[1]?.headers);
    expect(headers.get("x-csrf-token")).toBeNull();
    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBeInstanceOf(AbortSignal);
  });

  it("normalizes nested, text, malformed, and fallback error responses", async () => {
    const responses = [
      response({ detail: { message: "Nested failure", code: "nested_error" }, errors: ["field"] }, 422),
      new Response("Plain failure", {
        status: 502,
        headers: { "content-type": "text/plain", "x-request-id": "header-request" },
      }),
      new Response("not-json", { status: 500, headers: { "content-type": "application/json" } }),
      new Response("", { status: 418 }),
    ];
    const fetchMock = vi.fn<typeof fetch>();
    for (const item of responses) fetchMock.mockResolvedValueOnce(item);
    const client = new HttpClient({ baseUrl: "https://api.example.com", fetch: fetchMock });

    await expect(client.get("/nested", z.unknown())).rejects.toMatchObject({
      status: 422,
      code: "nested_error",
      message: "Nested failure",
      details: ["field"],
    });
    await expect(client.get("/text", z.unknown())).rejects.toMatchObject({
      status: 502,
      message: "Plain failure",
      requestId: "header-request",
    });
    await expect(client.get("/malformed", z.unknown())).rejects.toMatchObject({
      status: 500,
      message: "Request failed with status 500.",
    });
    await expect(client.get("/fallback", z.unknown())).rejects.toMatchObject({
      status: 418,
      code: "api_error",
      message: "Request failed with status 418.",
    });
  });

  it("normalizes unreadable success, timeout, and network failures", async () => {
    const unreadable = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response("not-json", { status: 200 }));
    const unreadableClient = new HttpClient({
      baseUrl: "https://api.example.com",
      fetch: unreadable,
    });
    await expect(unreadableClient.get("/invalid", z.unknown())).rejects.toMatchObject({
      status: 502,
      code: "invalid_api_contract",
    });

    const timeoutClient = new HttpClient({
      baseUrl: "https://api.example.com",
      fetch: vi.fn<typeof fetch>().mockRejectedValue(new DOMException("aborted", "AbortError")),
    });
    await expect(timeoutClient.get("/slow", z.unknown())).rejects.toMatchObject({
      status: 408,
      code: "request_timeout",
    });

    const networkClient = new HttpClient({
      baseUrl: "https://api.example.com",
      fetch: vi.fn<typeof fetch>().mockRejectedValue(new TypeError("private network detail")),
    });
    await expect(networkClient.get("/offline", z.unknown())).rejects.toMatchObject({
      status: 503,
      code: "network_unavailable",
      message: "The service is temporarily unavailable.",
    });
  });

  it("preserves explicit API error metadata and causes", () => {
    const cause = new Error("provider detail");
    const error = new ApiError({
      message: "Public failure",
      status: 409,
      requestId: "request-1",
      details: { field: "title" },
      cause,
    });
    expect(error).toMatchObject({
      name: "ApiError",
      status: 409,
      code: "api_error",
      requestId: "request-1",
      details: { field: "title" },
      cause,
    });
  });
});

describe("queryString", () => {
  it("drops undefined and empty values", () => {
    expect(queryString({ page: 2, q: "", active: false, missing: undefined })).toBe("?page=2&active=false");
    expect(queryString({ q: "", missing: undefined })).toBe("");
  });
});
