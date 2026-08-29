"use client";

import type { MediaAsset } from "@portfolio/api-client";
import { Button, cn } from "@portfolio/ui";
import { ExternalLink, FileText, Play } from "lucide-react";
import { MediaImage, safeMediaUrl } from "@/components/media-image";

type MediaAssetViewProps = {
  asset: MediaAsset;
  className?: string;
  eager?: boolean;
  fallbackLabel?: string;
  sizes?: string;
};

export function MediaAssetView({
  asset,
  className,
  eager = false,
  fallbackLabel = "Managed media is not available",
  sizes,
}: MediaAssetViewProps) {
  if (asset.kind === "image") {
    return (
      <figure className={cn("overflow-hidden", asset.caption && "flex flex-col", className)}>
        <MediaImage
          asset={asset}
          className={asset.caption ? "min-h-0 flex-1 rounded-none" : "size-full rounded-none"}
          eager={eager}
          fallbackLabel={fallbackLabel}
          {...(sizes ? { sizes } : {})}
        />
        {asset.caption && (
          <figcaption className="border-t border-border bg-surface-raised px-4 py-3 text-sm leading-6 text-muted-foreground">
            {asset.caption}
          </figcaption>
        )}
      </figure>
    );
  }

  const src = safeMediaUrl(asset.url);
  const accessibleName = asset.alt || asset.filename || "Managed project media";

  if (asset.kind === "video" && src) {
    return (
      <figure className={cn("overflow-hidden bg-ink text-white", className)}>
        <div className="relative grid min-h-64 place-items-center bg-[radial-gradient(circle_at_30%_20%,color-mix(in_oklab,var(--primary)_24%,transparent),transparent_48%),linear-gradient(145deg,var(--ink),color-mix(in_oklab,var(--ink)_82%,var(--primary)))]">
          <Play className="pointer-events-none absolute size-12 text-white/30" aria-hidden="true" />
          <video
            className="relative z-10 size-full object-contain"
            controls
            preload={eager ? "metadata" : "none"}
            aria-label={accessibleName}
          >
            <source src={src} type={asset.mime_type} />
            Your browser does not support embedded video.
          </video>
        </div>
        {(asset.caption || asset.alt) && (
          <figcaption className="border-t border-white/10 px-4 py-3 text-sm leading-6 text-white/70">
            {asset.caption || asset.alt}
          </figcaption>
        )}
      </figure>
    );
  }

  return (
    <figure className={cn("grid min-h-64 place-items-center gap-5 bg-muted p-8 text-center", className)}>
      <FileText className="size-10 text-primary" aria-hidden="true" />
      <div className="grid max-w-md gap-2">
        <p className="font-semibold">{asset.filename ?? "Project document"}</p>
        <p className="text-sm leading-6 text-muted-foreground">{accessibleName}</p>
      </div>
      {src && (
        <Button asChild variant="outline">
          <a href={src} target="_blank" rel="noopener noreferrer">
            Open document <ExternalLink aria-hidden="true" />
          </a>
        </Button>
      )}
      {asset.caption && <figcaption className="text-sm text-muted-foreground">{asset.caption}</figcaption>}
    </figure>
  );
}
