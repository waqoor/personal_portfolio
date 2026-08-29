"use client";

import type { MediaAsset } from "@portfolio/api-client";
import { ImageIcon } from "lucide-react";
import Image from "next/image";
import * as React from "react";
import { cn } from "@portfolio/ui";

export function safeMediaUrl(value: string): string | undefined {
  if (value.startsWith("/") && !value.startsWith("//") && !value.includes("\\")) return value;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : undefined;
  } catch {
    return undefined;
  }
}

type MediaImageProps = {
  asset?: MediaAsset | undefined;
  className?: string | undefined;
  imageClassName?: string | undefined;
  eager?: boolean;
  fallbackLabel?: string;
  sizes?: string;
};

export function MediaImage({ asset, className, eager = false, fallbackLabel = "Managed image is not available", imageClassName, sizes = "100vw" }: MediaImageProps) {
  const [failed, setFailed] = React.useState(false);
  const src = asset ? safeMediaUrl(asset.url) : undefined;
  const objectPosition = asset?.focal_x !== undefined || asset?.focal_y !== undefined
    ? `${(asset.focal_x ?? 0.5) * 100}% ${(asset.focal_y ?? 0.5) * 100}%`
    : "50% 50%";

  return (
    <div className={cn("relative isolate overflow-hidden bg-muted", className)}>
      <div
        className="absolute inset-0 grid place-items-center bg-[radial-gradient(circle_at_30%_20%,color-mix(in_oklab,var(--primary)_22%,transparent),transparent_48%),linear-gradient(145deg,var(--muted),var(--background))] text-muted-foreground"
        aria-hidden={asset?.is_decorative || Boolean(src && !failed)}
      >
        <div className="grid max-w-44 place-items-center gap-3 px-4 text-center">
          <ImageIcon className="size-6" aria-hidden="true" />
          <span className="font-mono text-[0.62rem] uppercase leading-5 tracking-[0.13em]">{fallbackLabel}</span>
        </div>
      </div>
      {src && !failed && (
        <Image
          src={src}
          alt={asset?.alt ?? ""}
          fill
          priority={eager}
          sizes={sizes}
          unoptimized={!src.startsWith("/")}
          onError={() => setFailed(true)}
          style={{ objectPosition }}
          className={cn("relative z-10 size-full object-cover", imageClassName)}
        />
      )}
    </div>
  );
}
