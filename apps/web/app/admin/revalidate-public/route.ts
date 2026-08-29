import { timingSafeEqual } from "node:crypto";

import { type ApiError } from "@portfolio/api-client";
import { revalidateTag } from "next/cache";
import { type NextRequest, NextResponse } from "next/server";

import { getAdminApi } from "@/lib/api";
import { isSameOriginMutation } from "@/lib/proxy-origin";

export const runtime = "nodejs";

function equalSecret(left: string, right: string): boolean {
  const leftBytes = Buffer.from(left, "utf8");
  const rightBytes = Buffer.from(right, "utf8");
  return leftBytes.length === rightBytes.length && timingSafeEqual(leftBytes, rightBytes);
}

function error(status: number, code: string): NextResponse {
  return NextResponse.json(
    { error: { code, message: "Public cache invalidation was not authorized." } },
    { status, headers: { "Cache-Control": "no-store" } },
  );
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  if (!isSameOriginMutation(request.headers, request.nextUrl.origin)) {
    return error(403, "cross_origin_request");
  }

  const cookieName = process.env.NEXT_PUBLIC_CSRF_COOKIE_NAME ?? "portfolio_csrf";
  const cookieToken = request.cookies.get(cookieName)?.value;
  const headerToken = request.headers.get("x-csrf-token");
  if (!cookieToken || !headerToken || !equalSecret(cookieToken, headerToken)) {
    return error(403, "csrf_validation_failed");
  }

  try {
    const api = await getAdminApi(headerToken);
    await api.admin.getSession();
  } catch (caught) {
    const status = (caught as Partial<ApiError>).status;
    return status === 401 || status === 403
      ? error(401, "authentication_required")
      : error(503, "authentication_unavailable");
  }

  revalidateTag("portfolio-public", { expire: 0 });
  return new NextResponse(null, {
    status: 204,
    headers: { "Cache-Control": "no-store" },
  });
}
