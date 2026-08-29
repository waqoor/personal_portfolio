import { render, screen } from "@testing-library/react";
import type { MediaAsset } from "@portfolio/api-client";
import { MediaAssetView } from "./media-asset";

function asset(overrides: Partial<MediaAsset>): MediaAsset {
  return {
    id: "managed-media",
    kind: "video",
    url: "/api/v1/public/project-media/managed-media",
    alt: "Architecture walkthrough",
    is_decorative: false,
    filename: "walkthrough.mp4",
    mime_type: "video/mp4",
    ...overrides,
  };
}

describe("MediaAssetView", () => {
  it("renders image captions semantically inside the responsive figure", () => {
    render(
      <MediaAssetView
        asset={asset({
          kind: "image",
          url: "/api/v1/public/project-media/diagram",
          alt: "Reviewed architecture diagram",
          caption: "Figure 1: reviewed system boundary",
          width: 1200,
          height: 800,
        })}
        sizes="50vw"
      />,
    );

    expect(screen.getByRole("img", { name: "Reviewed architecture diagram" })).toHaveAttribute(
      "sizes",
      "50vw",
    );
    expect(screen.getByText("Figure 1: reviewed system boundary").tagName).toBe("FIGCAPTION");
  });

  it("renders managed video with native controls and an accessible name", () => {
    render(<MediaAssetView asset={asset({})} />);

    const video = screen.getByLabelText("Architecture walkthrough");
    expect(video).toHaveAttribute("controls");
    expect(video.querySelector("source")).toHaveAttribute(
      "src",
      "/api/v1/public/project-media/managed-media",
    );
  });

  it("renders managed documents as safe explicit links", () => {
    render(
      <MediaAssetView
        asset={asset({
          kind: "document",
          url: "https://cdn.example.com/evidence.pdf",
          filename: "evidence.pdf",
          mime_type: "application/pdf",
        })}
      />,
    );

    expect(screen.getByRole("link", { name: /open document/i })).toHaveAttribute(
      "href",
      "https://cdn.example.com/evidence.pdf",
    );
  });

  it("does not link unsafe managed document URLs", () => {
    render(
      <MediaAssetView
        asset={asset({ kind: "document", url: "javascript:alert(1)" })}
      />,
    );

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("walkthrough.mp4")).toBeInTheDocument();
  });
});
