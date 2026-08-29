import { Badge, Button } from "@portfolio/ui";
import { ArrowLeft, ArrowRight, ShieldCheck } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { DiscoverySignals } from "@/components/discovery-signals";
import { ProjectCard } from "@/features/projects/project-card";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";
type Params = Promise<{ slug: string }>;

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  return discoveryMetadata(`/sectors/${slug}`, { title: "Sector" });
}

export default async function SectorPage({ params }: { params: Params }) {
  const { slug } = await params;
  const result = await loadApi(() => getPublicApi().public.getSector(slug));
  if (!result.ok) { if (result.error.status === 404) notFound(); throw new Error(result.error.message); }
  const sector = result.data;
  return (
    <main id="main-content">
      <DiscoverySignals path={`/sectors/${slug}`} />
      <header className="coordinate-grid border-b border-border"><div className="site-shell section-space"><Button asChild variant="text"><Link href="/sectors" prefetch={false}><ArrowLeft aria-hidden="true" />All sectors</Link></Button><div className="mt-10 grid gap-8 lg:grid-cols-[1fr_0.65fr] lg:items-end"><div><Badge variant="signal">Applied domain</Badge><h1 className="display-lg mt-7 max-w-[10ch]">{sector.name}</h1></div><div><p className="text-lg leading-8 text-muted-foreground">{sector.description}</p>{sector.evidence_summary && <p className="mt-5 border-l-2 border-primary pl-4 text-sm font-semibold leading-6">{sector.evidence_summary}</p>}</div></div></div></header>
      {sector.metrics.filter((metric) => metric.verified).length > 0 && <section className="site-shell section-space pb-0"><div className="flex items-center gap-2"><ShieldCheck className="size-4 text-primary" aria-hidden="true" /><p className="eyebrow">Approved evidence</p></div><dl className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{sector.metrics.filter((metric) => metric.verified).map((metric) => <div key={metric.id} className="rounded-[var(--radius-card)] border border-border bg-surface-raised p-6"><dt className="text-sm font-semibold">{metric.label}</dt><dd className="mt-5 font-display text-5xl tracking-[-0.06em]">{metric.value}{metric.unit}</dd><p className="mt-3 text-xs leading-5 text-muted-foreground">{metric.context}</p></div>)}</dl></section>}
      <section className="site-shell section-space"><div className="flex flex-col items-start gap-6 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">Published work</p><h2 className="display-md mt-6">Projects in this context.</h2></div><Button asChild variant="text"><Link href={`/projects?sector=${sector.slug}`}>Filtered archive <ArrowRight aria-hidden="true" /></Link></Button></div><div className={`mt-10 grid gap-5 ${sector.projects.length === 1 ? "max-w-2xl" : sector.projects.length === 2 ? "md:grid-cols-2" : "md:grid-cols-2 xl:grid-cols-3"}`}>{sector.projects.map((project) => <ProjectCard key={project.id} project={project} />)}</div>{sector.skills.length > 0 && <div className="mt-14 border-t border-border pt-8"><p className="eyebrow">Technologies used</p><div className="mt-5 flex flex-wrap gap-2">{sector.skills.map((skill) => <Badge key={skill.id} variant="muted">{skill.name}</Badge>)}</div></div>}</section>
    </main>
  );
}
