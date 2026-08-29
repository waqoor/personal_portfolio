import type { HomePage, HomepageSection, ProjectSummary } from "@portfolio/api-client";
import { Reveal } from "@portfolio/motion";
import { Badge, Button, Card } from "@portfolio/ui";
import { ArrowRight, ExternalLink, GitBranch, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { MediaImage } from "@/components/media-image";
import { SectionFrame, limitBySection } from "./section-frame";

function ProjectMeta({ project }: { project: ProjectSummary }) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-2 font-mono text-[0.63rem] uppercase tracking-[0.13em] text-muted-foreground">
      {project.year && <span>{project.year}</span>}
      {project.role && <span>{project.role}</span>}
      {project.status_label && <span>{project.status_label}</span>}
    </div>
  );
}

function RichProject({ index, project }: { index: number; project: ProjectSummary }) {
  const primaryLink = project.links.find((link) => link.kind === "demo" || link.kind === "website");
  return (
    <article data-story-item className="grid min-h-[42rem] gap-8 border-b border-border py-12 first:pt-0 last:border-b-0 lg:grid-cols-[minmax(0,0.72fr)_minmax(26rem,1.28fr)] lg:items-center lg:gap-14 lg:py-24">
      <div className={index % 2 === 1 ? "lg:order-2" : undefined}>
        <div className="flex items-center justify-between gap-4">
          <span className="font-display text-6xl leading-none tracking-[-0.08em] text-accent-ink dark:text-primary">0{index + 1}</span>
          {project.metrics.some((metric) => metric.verified) && <Badge variant="verified"><ShieldCheck aria-hidden="true" />Verified outcomes</Badge>}
        </div>
        <ProjectMeta project={project} />
        <h3 className="mt-6 font-display text-[clamp(2.7rem,5vw,5.8rem)] leading-[0.87] tracking-[-0.06em]">{project.title}</h3>
        {project.kicker && <p className="mt-5 text-lg font-semibold leading-7">{project.kicker}</p>}
        <p className="mt-5 max-w-xl text-base leading-7 text-muted-foreground">{project.summary}</p>
        {project.metrics.length > 0 && (
          <dl className="mt-8 grid grid-cols-2 gap-3">
            {project.metrics.filter((metric) => metric.verified).slice(0, 2).map((metric) => (
              <div key={metric.id} className="border-l-2 border-primary pl-4"><dt className="text-xs leading-5 text-muted-foreground">{metric.label}</dt><dd className="mt-1 font-display text-3xl tracking-[-0.04em]">{metric.value}{metric.unit}</dd></div>
            ))}
          </dl>
        )}
        <div className="mt-9 flex flex-wrap gap-3">
          <Button asChild variant="primary"><Link href={`/projects/${project.slug}`}>Read case study <ArrowRight aria-hidden="true" /></Link></Button>
          {primaryLink && <Button asChild variant="outline"><a href={primaryLink.url} target="_blank" rel="noreferrer">{primaryLink.label}<ExternalLink aria-hidden="true" /></a></Button>}
        </div>
      </div>
      <Link href={`/projects/${project.slug}`} aria-label={`Open ${project.title} case study`} className={`group relative block aspect-[4/3] overflow-hidden rounded-[clamp(1.5rem,4vw,3rem)] border border-border-strong bg-muted shadow-[0_40px_120px_-68px_var(--shadow-ink)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${index % 2 === 1 ? "lg:order-1" : ""}`}>
        <MediaImage asset={project.cover} className="size-full" imageClassName="transition-transform duration-700 ease-out group-hover:scale-[1.035] motion-reduce:transition-none" fallbackLabel="Managed project cover" sizes="(max-width: 1024px) 95vw, 52vw" />
        <div className="absolute inset-0 z-20 bg-gradient-to-t from-ink/55 via-transparent to-transparent opacity-75" />
        <span className="absolute bottom-5 right-5 z-30 grid size-12 place-items-center rounded-full bg-primary text-primary-foreground transition-transform group-hover:-translate-y-1 group-hover:translate-x-1 motion-reduce:transition-none"><ArrowRight aria-hidden="true" /></span>
      </Link>
    </article>
  );
}

function CompactProject({ project }: { project: ProjectSummary }) {
  return (
    <Card className="group overflow-hidden">
      <article className="grid h-full md:grid-cols-[0.85fr_1.15fr]">
        <Link href={`/projects/${project.slug}`} className="relative block aspect-[4/3] overflow-hidden bg-muted md:aspect-auto md:min-h-72" aria-label={`Open ${project.title} case study`}>
          <MediaImage asset={project.cover} className="absolute inset-0 size-full" imageClassName="transition-transform duration-700 group-hover:scale-[1.035] motion-reduce:transition-none" fallbackLabel="Managed project cover" />
        </Link>
        <div className="flex flex-col justify-between gap-8 p-6 sm:p-8">
          <div><ProjectMeta project={project} /><h3 className="mt-4 font-display text-4xl leading-[0.95] tracking-[-0.05em]">{project.title}</h3><p className="mt-4 text-sm leading-6 text-muted-foreground">{project.summary}</p></div>
          <div className="flex items-center justify-between gap-4"><div className="flex flex-wrap gap-2">{project.skills.slice(0, 3).map((skill) => <Badge key={skill.id} variant="muted">{skill.name}</Badge>)}</div><Button asChild variant="ghost" size="icon" aria-label={`Read ${project.title}`}><Link href={`/projects/${project.slug}`}><ArrowRight aria-hidden="true" /></Link></Button></div>
        </div>
      </article>
    </Card>
  );
}

export function SelectedWorkSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const projects = limitBySection(data.featured_projects, section, 5).slice(0, 5);
  const rich = projects.slice(0, 3);
  const compact = projects.slice(3, 5);
  return (
    <SectionFrame section={section} eyebrow="Selected / Signature work" title="Systems with a story behind them." description="A focused set of projects selected for depth, decisions, and evidence—not a wall of thumbnails." headerAside={section.cta_visible && <Button asChild variant="text" className="mt-5"><Link href="/projects">Explore the full archive <ArrowRight aria-hidden="true" /></Link></Button>}>
      {projects.length === 0 ? (
        <div className="rounded-[var(--radius-card)] border border-dashed border-border-strong p-10 text-center text-sm text-muted-foreground">No selected projects are currently published.</div>
      ) : (
        <>
          <div>{rich.map((project, index) => <RichProject key={project.id} index={index} project={project} />)}</div>
          {compact.length > 0 && <Reveal className="mt-10 grid gap-5 lg:grid-cols-2"><div className="lg:col-span-2 flex items-center gap-3 font-mono text-[0.65rem] uppercase tracking-[0.15em] text-muted-foreground"><GitBranch className="size-4 text-primary" aria-hidden="true" />More selected work</div>{compact.map((project) => <CompactProject key={project.id} project={project} />)}</Reveal>}
        </>
      )}
    </SectionFrame>
  );
}
