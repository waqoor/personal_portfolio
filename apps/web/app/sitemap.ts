import type { MetadataRoute } from "next";
import { getPublicApi } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  try {
    const entries = await getPublicApi().public.getSitemap();
    return entries.map((entry) => ({
      url: entry.url,
      ...(entry.last_modified ? { lastModified: new Date(entry.last_modified) } : {}),
      ...(entry.change_frequency ? { changeFrequency: entry.change_frequency } : {}),
      ...(entry.priority !== undefined ? { priority: entry.priority } : {}),
    }));
  } catch {
    return [];
  }
}
