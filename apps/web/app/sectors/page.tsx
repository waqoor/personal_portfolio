import { Badge, Button, Card, EmptyState } from "@portfolio/ui";
import { ArrowRight, Compass, Map } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { DiscoverySignals } from "@/components/discovery-signals";
import { PageIntro } from "@/components/page-intro";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/sectors", { title: "Sectors" });
}

export default async function SectorsPage() {
  const result = await loadApi(() => getPublicApi().public.getSectors());
  if (!result.ok) return <PublicDataUnavailable reference={result.error.requestId} />;
  return (
    <main id="main-content">
      <DiscoverySignals path="/sectors" />
      <PageIntro eyebrow="Applied domains" title={result.data.presentation.sectors_title} description={result.data.presentation.sectors_intro} />
      <section className="site-shell section-space">{result.data.items.length > 0 ? <div className={`grid gap-5 ${result.data.items.length === 1 ? "max-w-4xl" : result.data.items.length === 2 ? "md:grid-cols-2" : "md:grid-cols-2 xl:grid-cols-3"}`}>{result.data.items.map((sector, index) => <Card key={sector.id} className="group flex min-h-80 flex-col justify-between p-6 transition-colors hover:border-primary hover:bg-primary/8 sm:p-8"><div className="flex items-start justify-between gap-4"><span className="font-display text-5xl tracking-[-0.07em] text-accent-ink dark:text-primary">{String(index + 1).padStart(2, "0")}</span><Compass className="size-5 text-muted-foreground" aria-hidden="true" /></div><div><Badge variant="muted">{sector.project_count} {sector.project_count === 1 ? "project" : "projects"}</Badge><h2 className="mt-5 font-display text-4xl leading-none tracking-[-0.05em]">{sector.name}</h2><p className="mt-4 text-sm leading-6 text-muted-foreground">{sector.description}</p>{sector.evidence_summary && <p className="mt-5 border-l-2 border-primary pl-4 text-sm font-semibold leading-6">{sector.evidence_summary}</p>}<Button asChild variant="text" className="mt-7"><Link href={`/sectors/${sector.slug}`}>View domain evidence <ArrowRight aria-hidden="true" /></Link></Button></div></Card>)}</div> : <EmptyState icon={<Map className="size-5" />} title="No sectors are published" description="Published domain experience will appear here when project evidence is available." />}</section>
    </main>
  );
}
