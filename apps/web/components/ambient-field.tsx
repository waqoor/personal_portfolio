"use client";

import dynamic from "next/dynamic";

const WebGLField = dynamic(
  () => import("@portfolio/motion").then((module) => module.WebGLField),
  { ssr: false, loading: () => <div className="webgl-static-fallback size-full" aria-hidden="true" /> },
);

export function AmbientField({ className, density }: { className?: string; density?: number }) {
  return <WebGLField {...(className ? { className } : {})} {...(density !== undefined ? { density } : {})} />;
}
