import type { DiscoveryPage } from "@portfolio/api-client";
import { discoveryMetadata, metadataFromDiscovery } from "./metadata";

vi.mock("@/lib/api", () => ({
  getPublicApi: () => {
    throw new Error("The default API loader must not run in this unit test.");
  },
}));

const discoveryPage: DiscoveryPage = {
  metadata: {
    title: "Reviewed project",
    description: "Canonical discovery description.",
    canonical_url: "https://portfolio.example/projects/reviewed",
    robots: "index, follow",
    open_graph: {
      type: "article",
      site_name: "Portfolio",
      locale: "en_US",
      title: "Reviewed project",
      description: "Canonical discovery description.",
      url: "https://portfolio.example/projects/reviewed",
      images: ["https://portfolio.example/api/v1/public/project-media/media-1"],
    },
    twitter: {
      card: "summary_large_image",
      title: "Reviewed project",
      description: "Canonical discovery description.",
      images: ["https://portfolio.example/api/v1/public/project-media/media-1"],
    },
  },
  breadcrumbs: [],
  related_urls: [],
  json_ld: { "@context": "https://schema.org", "@graph": [] },
};

describe("discovery metadata", () => {
  it("maps authoritative discovery metadata without changing index policy", () => {
    const metadata = metadataFromDiscovery(discoveryPage);

    expect(metadata.robots).toEqual({
      index: true,
      follow: true,
      googleBot: "index, follow",
    });
    expect(metadata.title).toEqual({ absolute: "Reviewed project" });
    expect(metadata.openGraph).toEqual(
      expect.objectContaining({
        type: "article",
        url: "https://portfolio.example/projects/reviewed",
        images: ["https://portfolio.example/api/v1/public/project-media/media-1"],
      }),
    );
  });

  it("fails closed to noindex when the discovery authority is unavailable", async () => {
    const metadata = await discoveryMetadata(
      "/projects/reviewed",
      {
        title: "Fallback title",
        robots: { index: true, follow: true },
      },
      async () => {
        throw new Error("transient backend failure");
      },
    );

    expect(metadata.title).toBe("Fallback title");
    expect(metadata.robots).toEqual({ index: false, follow: false });
  });
});
