import type { DiscoveryPage } from "@portfolio/api-client";
import { ChevronRight } from "lucide-react";
import Link from "next/link";

export function DiscoveryBreadcrumbs({ breadcrumbs }: Pick<DiscoveryPage, "breadcrumbs">) {
  if (breadcrumbs.length <= 1) return null;
  return (
    <nav className="site-shell pt-6" aria-label="Breadcrumb">
      <ol className="flex flex-wrap items-center gap-2 font-mono text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">
        {breadcrumbs.map((breadcrumb, index) => {
          const current = index === breadcrumbs.length - 1;
          let href = breadcrumb.url;
          try { href = new URL(breadcrumb.url).pathname; } catch { /* relative URLs remain valid */ }
          return (
            <li key={breadcrumb.url} className="flex items-center gap-2">
              {index > 0 && <ChevronRight className="size-3" aria-hidden="true" />}
              {current ? <span aria-current="page">{breadcrumb.label}</span> : <Link href={href} prefetch={false} className="-mx-1 inline-flex min-h-11 min-w-11 items-center justify-center rounded-sm px-1 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">{breadcrumb.label}</Link>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
