import { NextResponse, type NextRequest } from "next/server";
import { getPublicApi } from "@/lib/api";

export const dynamic = "force-dynamic";

export async function GET(request: NextRequest) {
  try {
    const resume = await getPublicApi().public.getResume();
    const target = new URL(resume.download_url, "https://portfolio.invalid");
    if (target.origin !== "https://portfolio.invalid") throw new Error("The résumé route must stay on the public origin.");
    const response = new NextResponse(null, {
      status: 307,
      headers: { Location: `${target.pathname}${target.search}` },
    });
    response.headers.set("Cache-Control", "no-store, max-age=0");
    response.headers.set("X-Robots-Tag", "noindex");
    return response;
  } catch {
    const unavailable = new URL("/resume-unavailable", request.nextUrl.origin);
    return NextResponse.redirect(unavailable, 307);
  }
}
