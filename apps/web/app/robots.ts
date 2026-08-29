import type { MetadataRoute } from "next";
import { getPublicApi } from "@/lib/api";
import { siteUrl } from "@/lib/metadata";

export const dynamic = "force-dynamic";

export default async function robots(): Promise<MetadataRoute.Robots> {
  const base = siteUrl();
  try {
    const { content } = await getPublicApi().public.getRobotsText();
    const lines = content.split(/\r?\n/);
    const disallow = lines.filter((line) => line.startsWith("Disallow:"))
      .map((line) => line.slice("Disallow:".length).trim());
    const allow = lines.filter((line) => line.startsWith("Allow:"))
      .map((line) => line.slice("Allow:".length).trim());
    const sitemap = lines.find((line) => line.startsWith("Sitemap:"))?.slice("Sitemap:".length).trim();
    const host = lines.find((line) => line.startsWith("Host:"))?.slice("Host:".length).trim();
    return {
      rules: [{ userAgent: "*", allow, disallow }],
      sitemap: sitemap ?? new URL("/sitemap.xml", base).toString(),
      host: host ?? base.host,
    };
  } catch {
    // Safe crawler policy remains restrictive if the discovery service is temporarily unavailable.
  }
  return {
    rules: [
      { userAgent: "*", disallow: "/" },
    ],
    sitemap: new URL("/sitemap.xml", base).toString(),
    host: base.origin,
  };
}
