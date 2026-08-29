import { fireEvent, render, screen } from "@testing-library/react";
import type { MediaAsset } from "@portfolio/api-client";
import { MediaImage } from "./media-image";

function asset(url: string): MediaAsset {
  return {
    id: "media-1",
    kind: "image",
    url,
    alt: "Published architecture diagram",
    is_decorative: false,
    width: 1200,
    height: 800,
    focal_x: 0.25,
    focal_y: 0.75,
  };
}

describe("MediaImage", () => {
  it("renders managed relative media with explicit responsive behavior", () => {
    render(<MediaImage asset={asset("/api/v1/media/diagram")} eager sizes="50vw" />);

    const image = screen.getByRole("img", { name: "Published architecture diagram" });
    expect(image).toHaveAttribute("sizes", "50vw");
    expect(image).toHaveAttribute("srcset");
    expect(image).toHaveStyle({ objectPosition: "25% 75%" });
  });

  it("falls back after a managed image fails to load", () => {
    render(<MediaImage asset={asset("https://cdn.example.com/diagram.webp")} />);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("Managed image is not available")).toBeInTheDocument();
  });

  it("keeps decorative image and fallback text out of the accessibility tree", () => {
    const decorative = { ...asset("/api/v1/media/texture"), alt: "", is_decorative: true };
    render(<MediaImage asset={decorative} fallbackLabel="Decorative texture" />);

    expect(screen.getByAltText("")).toBeInTheDocument();
    expect(screen.getByText("Decorative texture").closest("[aria-hidden]")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
  });

  it.each(["javascript:alert(1)", "not a URL"])(
    "does not render an unsafe media URL: %s",
    (url) => {
      render(<MediaImage asset={asset(url)} fallbackLabel="Unavailable media" />);
      expect(screen.queryByRole("img")).not.toBeInTheDocument();
      expect(screen.getByText("Unavailable media")).toBeInTheDocument();
    },
  );
});
