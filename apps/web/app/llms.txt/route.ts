import { NextResponse } from "next/server";
import { getPublicApi } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET() {
  let body = "# Portfolio\n\nPublished portfolio discovery data is temporarily unavailable.\n";
  try {
    body = (await getPublicApi().public.getLlmsText()).content;
  } catch {
    // The fallback contains no unverified personal or portfolio claims.
  }
  return new NextResponse(body, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=300, stale-while-revalidate=3600",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
