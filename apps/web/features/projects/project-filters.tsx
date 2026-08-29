import type { Category, Sector } from "@portfolio/api-client";
import { Button, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@portfolio/ui";
import { Search, X } from "lucide-react";
import Link from "next/link";

export function ProjectFilters({ categories, current, sectors }: { categories: Category[]; sectors: Sector[]; current: { category?: string | undefined; sector?: string | undefined; search?: string | undefined } }) {
  const active = Boolean(current.category || current.sector || current.search);
  return (
    <form method="get" action="/projects" className="grid gap-4 rounded-[var(--radius-card)] border border-border-strong bg-surface-raised p-5 md:grid-cols-[1fr_0.7fr_0.7fr_auto] md:items-end" role="search">
      <div className="grid gap-2"><Label htmlFor="project-search">Search the archive</Label><div className="relative"><Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" /><Input id="project-search" name="q" defaultValue={current.search} placeholder="Project, skill, outcome…" className="pl-11" /></div></div>
      <div className="grid gap-2"><Label htmlFor="category-filter">Category</Label><Select name="category" defaultValue={current.category ?? "all"}><SelectTrigger id="category-filter"><SelectValue placeholder="All categories" /></SelectTrigger><SelectContent><SelectItem value="all">All categories</SelectItem>{categories.map((category) => <SelectItem key={category.id} value={category.slug}>{category.name}</SelectItem>)}</SelectContent></Select></div>
      <div className="grid gap-2"><Label htmlFor="sector-filter">Sector</Label><Select name="sector" defaultValue={current.sector ?? "all"}><SelectTrigger id="sector-filter"><SelectValue placeholder="All sectors" /></SelectTrigger><SelectContent><SelectItem value="all">All sectors</SelectItem>{sectors.map((sector) => <SelectItem key={sector.id} value={sector.slug}>{sector.name}</SelectItem>)}</SelectContent></Select></div>
      <div className="flex gap-2"><Button type="submit" variant="signal">Filter</Button>{active && <Button asChild variant="ghost" size="icon" aria-label="Clear filters"><Link href="/projects"><X aria-hidden="true" /></Link></Button>}</div>
    </form>
  );
}
