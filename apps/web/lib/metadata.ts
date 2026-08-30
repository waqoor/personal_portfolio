import type { DiscoveryPage, Seo } from "@portfolio/api-client";
import type { Metadata } from "next";
import { getPublicApi } from "@/lib/api";

export function siteUrl(): URL {
  try {
    return new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:18444");
  } catch {
    return new URL("http://localhost:18444");
  }
}

export function metadataFromSeo(seo: Seo, path?: string): Metadata {
  const canonical = seo.canonical_url ?? path;
  const image = seo.og_image?.url;
  return {
    // SEO/discovery titles are already canonical, complete document titles.
    // Mark them absolute so the root layout template does not append the site
    // name a second time.
    title: { absolute: seo.title },
    description: seo.description,
    keywords: seo.keywords,
    alternates: canonical ? { canonical } : undefined,
    robots: seo.noindex ? { index: false, follow: false } : { index: true, follow: true },
    openGraph: {
      type: "website",
      title: seo.title,
      description: seo.description,
      url: canonical,
      images: image ? [{ url: image, alt: seo.og_image?.alt ?? "" }] : undefined,
    },
    twitter: {
      card: image ? "summary_large_image" : "summary",
      title: seo.title,
      description: seo.description,
      images: image ? [image] : undefined,
    },
  };
}

export function metadataFromDiscovery(page: DiscoveryPage): Metadata {
  const { metadata } = page;
  const robots = metadata.robots.toLocaleLowerCase();
  const openGraphType = metadata.open_graph.type === "article"
    ? "article"
    : metadata.open_graph.type === "profile"
      ? "profile"
      : "website";
  const twitterCard = metadata.twitter.card === "summary_large_image" ? "summary_large_image" : "summary";
  return {
    title: { absolute: metadata.title },
    description: metadata.description,
    keywords: metadata.keywords,
    alternates: { canonical: metadata.canonical_url },
    robots: {
      index: !robots.includes("noindex"),
      follow: !robots.includes("nofollow"),
      googleBot: metadata.robots,
    },
    openGraph: {
      type: openGraphType,
      siteName: metadata.open_graph.site_name,
      locale: metadata.open_graph.locale,
      title: metadata.open_graph.title,
      description: metadata.open_graph.description,
      url: metadata.open_graph.url,
      images: metadata.open_graph.images,
    },
    twitter: {
      card: twitterCard,
      title: metadata.twitter.title,
      description: metadata.twitter.description,
      images: metadata.twitter.images,
    },
  };
}

export async function discoveryMetadata(
  path: string,
  fallback: Metadata,
  loadPage: (path: string) => Promise<DiscoveryPage> = (requestedPath) =>
    getPublicApi().public.getDiscoveryPage(requestedPath),
): Promise<Metadata> {
  let page: DiscoveryPage;
  try {
    page = await loadPage(path);
  } catch {
    return {
      ...fallback,
      robots: { index: false, follow: false },
    };
  }
  return metadataFromDiscovery(page);
}

export function jsonLd(value: Record<string, unknown>): string {
  return JSON.stringify(value).replace(/</g, "\\u003c");
}
