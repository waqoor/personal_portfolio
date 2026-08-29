import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Yazeed Hasan Portfolio",
    short_name: "Yazeed Hasan",
    description: "AI engineering, data platforms, MLOps, leadership, projects, and achievements by Yazeed Hasan.",
    start_url: "/",
    display: "standalone",
    background_color: "#f5f2e9",
    theme_color: "#baf43c",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
