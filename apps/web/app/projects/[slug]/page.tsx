import type { ProjectSection } from "@portfolio/api-client";
import { Badge, Button } from "@portfolio/ui";
import { ArrowLeft, ArrowRight, CheckCircle2, ExternalLink as ExternalIcon, Quote, ShieldCheck } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { DiscoverySignals } from "@/components/discovery-signals";
import { ExternalLink } from "@/components/external-link";
import { MediaAssetView } from "@/components/media-asset";
import { MediaImage } from "@/components/media-image";
import { ProjectCard } from "@/features/projects/project-card";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";

type Params = Promise<{ slug: string }>;

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  return discoveryMetadata(`/projects/${slug}`, { title: "Case study" });
}

function ProjectStorySection({ section }: { section: ProjectSection }) {
  return (
    <section className="grid gap-7 border-t border-border py-12 md:grid-cols-[0.35fr_1fr] md:py-16" aria-labelledby={`section-${section.id}`}>
      <div><p className="eyebrow">{section.eyebrow ?? section.kind}</p></div>
      <div><h2 id={`section-${section.id}`} className="font-display text-[clamp(2.4rem,5vw,4.8rem)] leading-[0.92] tracking-[-0.055em]">{section.title}</h2>{section.body && <p className="mt-6 max-w-3xl whitespace-pre-line text-base leading-8 text-muted-foreground">{section.body}</p>}{section.items.length > 0 && <ul className="mt-8 grid gap-3 sm:grid-cols-2">{section.items.map((item) => <li key={item} className="grid grid-cols-[auto_1fr] gap-3 rounded-2xl border border-border bg-surface-raised p-4 text-sm leading-6"><CheckCircle2 className="mt-1 size-4 text-primary" aria-hidden="true" />{item}</li>)}</ul>}{section.media.length > 0 && <div className="mt-8 grid gap-4 sm:grid-cols-2">{section.media.map((media) => <MediaAssetView key={media.id} asset={media} className="aspect-[4/3] rounded-[var(--radius-card)] border border-border" fallbackLabel="Managed case-study media" />)}</div>}</div>
    </section>
  );
}

export default async function ProjectDetailPage({ params }: { params: Params }) {
  const { slug } = await params;
  const result = await loadApi(() => getPublicApi().public.getProject(slug));
  if (!result.ok) {
    if (result.error.status === 404) notFound();
    throw new Error(result.error.message);
  }
  const project = result.data;
  return (
    <main id="main-content">
      <DiscoverySignals path={`/projects/${slug}`} />
      <header className="coordinate-grid border-b border-border">
        <div className="site-shell section-space pb-12">
          <Button asChild variant="text"><Link href="/projects"><ArrowLeft aria-hidden="true" />Project archive</Link></Button>
          <div className="mt-10 grid gap-10 lg:grid-cols-[1fr_0.75fr] lg:items-end">
            <div><div className="flex flex-wrap gap-2">{project.categories.map((category) => <Badge key={category.id} variant="signal">{category.name}</Badge>)}{project.metrics.some((metric) => metric.verified) && <Badge variant="verified"><ShieldCheck aria-hidden="true" />Verified outcomes</Badge>}</div><h1 className="display-lg mt-7 max-w-[11ch]">{project.title}</h1>{project.kicker && <p className="mt-6 max-w-2xl font-display text-2xl leading-tight tracking-[-0.035em] text-muted-foreground">{project.kicker}</p>}</div>
            <div><p className="text-base leading-7 text-muted-foreground">{project.summary}</p><dl className="mt-7 grid grid-cols-2 gap-4 border-t border-border pt-5 font-mono text-[0.65rem] uppercase tracking-[0.12em]"><div><dt className="text-muted-foreground">Role</dt><dd className="mt-2 font-semibold text-foreground">{project.role ?? "Published in case study"}</dd></div><div><dt className="text-muted-foreground">Year</dt><dd className="mt-2 font-semibold text-foreground">{project.year ?? "Ongoing"}</dd></div></dl><div className="mt-7 flex flex-wrap gap-3">{project.links.map((link) => <Button key={link.url} asChild variant={link.kind === "demo" ? "signal" : "outline"}><ExternalLink href={link.url}>{link.label}<ExternalIcon aria-hidden="true" /></ExternalLink></Button>)}</div></div>
          </div>
        </div>
        <div className="site-shell pb-10">{project.cover ? <MediaAssetView asset={project.cover} eager className="aspect-[16/9] rounded-[clamp(1.5rem,4vw,3.5rem)] border border-border-strong shadow-[0_50px_150px_-80px_var(--shadow-ink)]" fallbackLabel="Managed project cover" sizes="95vw" /> : <MediaImage eager className="aspect-[16/9] rounded-[clamp(1.5rem,4vw,3.5rem)] border border-border-strong shadow-[0_50px_150px_-80px_var(--shadow-ink)]" fallbackLabel="Managed project cover" sizes="95vw" />}</div>
      </header>

      <article className="site-shell-narrow section-space">
        {project.metrics.filter((metric) => metric.verified).length > 0 && <section className="py-16" aria-labelledby="project-results"><div className="flex items-center gap-2"><ShieldCheck className="size-5 text-primary" aria-hidden="true" /><p className="eyebrow">Verified results</p></div><h2 id="project-results" className="display-md mt-6">Evidence over adjectives.</h2><dl className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{project.metrics.filter((metric) => metric.verified).map((metric) => <div key={metric.id} className="rounded-[var(--radius-card)] border border-border bg-surface-raised p-6"><dt className="text-sm font-semibold">{metric.label}</dt><dd className="mt-5 font-display text-5xl leading-none tracking-[-0.06em]">{metric.value}{metric.unit}</dd><p className="mt-4 text-xs leading-5 text-muted-foreground">{metric.context}</p>{metric.evidence_url && <ExternalLink href={metric.evidence_url} className="mt-4 text-xs font-semibold text-accent-ink dark:text-primary">{metric.evidence_label ?? "Evidence"}</ExternalLink>}</div>)}</dl></section>}

        {project.sections.map((section) => <ProjectStorySection key={section.id} section={section} />)}

        {project.gallery.length > 0 && <section className="border-t border-border py-16" aria-labelledby="project-gallery"><p className="eyebrow">Project media</p><h2 id="project-gallery" className="display-md mt-6">Inside the system.</h2><div className="mt-10 grid gap-5 sm:grid-cols-2">{project.gallery.map((media) => <MediaAssetView key={media.id} asset={media} className="aspect-[4/3] rounded-[var(--radius-card)] border border-border-strong" fallbackLabel="Managed case-study media" />)}</div></section>}

        {project.testimonials.filter((item) => item.verified).map((testimonial) => <figure key={testimonial.id} className="border-y border-border py-16"><Quote className="size-8 text-primary" aria-hidden="true" /><blockquote className="mt-8 font-display text-[clamp(2.2rem,5vw,4.8rem)] leading-[0.98] tracking-[-0.05em]">“{testimonial.quote}”</blockquote><figcaption className="mt-8 text-sm font-semibold">{testimonial.attribution_name}<span className="font-normal text-muted-foreground">{[testimonial.attribution_role, testimonial.attribution_organization].filter(Boolean).length ? ` · ${[testimonial.attribution_role, testimonial.attribution_organization].filter(Boolean).join(", ")}` : ""}</span></figcaption></figure>)}
      </article>

      {project.related_projects.length > 0 && <section className="border-t border-border bg-muted/45"><div className="site-shell section-space"><div className="flex flex-col items-start gap-6 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">Continue exploring</p><h2 className="display-md mt-6">Related work.</h2></div><Button asChild variant="text"><Link href="/projects">Full archive <ArrowRight aria-hidden="true" /></Link></Button></div><div className={`mt-10 grid gap-5 ${project.related_projects.length === 1 ? "max-w-2xl" : project.related_projects.length === 2 ? "md:grid-cols-2" : "md:grid-cols-2 xl:grid-cols-3"}`}>{project.related_projects.slice(0, 3).map((related) => <ProjectCard key={related.id} project={related} />)}</div></div></section>}
    </main>
  );
}
