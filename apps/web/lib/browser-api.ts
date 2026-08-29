"use client";

import { createPortfolioApi, type PortfolioApi } from "@portfolio/api-client";

let api: PortfolioApi | undefined;
let activeCsrfToken: string | undefined;

function csrfCookie(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const cookieName = process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME ?? "portfolio_csrf";
  const prefix = `${encodeURIComponent(cookieName)}=`;
  const match = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(prefix));
  return match ? decodeURIComponent(match.slice(prefix.length)) : undefined;
}

export function getBrowserApi(csrfToken?: string): PortfolioApi {
  const effectiveCsrfToken = csrfToken ?? csrfCookie();
  if (!api || effectiveCsrfToken !== activeCsrfToken) {
    activeCsrfToken = effectiveCsrfToken;
    api = createPortfolioApi({
      baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend/api/v1",
      timeoutMs: 12_000,
      ...(effectiveCsrfToken ? { csrfToken: effectiveCsrfToken } : {}),
      defaultHeaders: { "X-Frontend-Channel": "browser" },
      onMutationSuccess: async ({ path }) => {
        if (!path.startsWith("/admin/") || !effectiveCsrfToken) return;
        const response = await fetch("/admin/revalidate-public", {
          method: "POST",
          credentials: "include",
          cache: "no-store",
          headers: { "X-CSRF-Token": effectiveCsrfToken },
        });
        if (!response.ok) {
          throw new Error("Public cache invalidation was not accepted.");
        }
      },
    });
  }
  return api;
}
