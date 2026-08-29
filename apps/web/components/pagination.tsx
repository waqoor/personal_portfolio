import { Button } from "@portfolio/ui";
import { ArrowLeft, ArrowRight } from "lucide-react";
import Link from "next/link";

function pageHref(path: string, page: number, query: Record<string, string | undefined>): string {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => { if (value) params.set(key, value); });
  if (page > 1) params.set("page", String(page));
  const suffix = params.toString();
  return suffix ? `${path}?${suffix}` : path;
}

export function Pagination({ page, path, query, totalPages }: { page: number; totalPages: number; path: string; query: Record<string, string | undefined> }) {
  if (totalPages <= 1) return null;
  return (
    <nav className="mt-12 flex items-center justify-between gap-4 border-t border-border pt-6" aria-label="Pagination">
      {page > 1 ? <Button asChild variant="outline"><Link href={pageHref(path, page - 1, query)} rel="prev"><ArrowLeft aria-hidden="true" />Previous</Link></Button> : <span />}
      <span className="font-mono text-[0.65rem] uppercase tracking-[0.13em] text-muted-foreground">Page {page} / {totalPages}</span>
      {page < totalPages ? <Button asChild variant="outline"><Link href={pageHref(path, page + 1, query)} rel="next">Next<ArrowRight aria-hidden="true" /></Link></Button> : <span />}
    </nav>
  );
}
