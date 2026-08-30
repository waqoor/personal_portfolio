import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Yazeed Hasan Portfolio",
    short_name: "Yazeed Hasan",
    description: "Enterprise AI/ML, data platforms, MLOps, strategy, technical leadership, and accountable delivery by Yazeed Hasan.",
    start_url: "/",
    display: "standalone",
    background_color: "#f6f3eb",
    theme_color: "#9fcb4e",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
