import type { ProjectSummary } from "@portfolio/api-client";
import { Badge, Button, Card } from "@portfolio/ui";
import { ArrowRight, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { MediaImage } from "@/components/media-image";

export function ProjectCard({ project }: { project: ProjectSummary }) {
  const verifiedMetrics = project.metrics.filter((metric) => metric.verified);
  return (
    <Card className="group flex h-full flex-col overflow-hidden">
      <Link href={`/projects/${project.slug}`} className="relative block aspect-[4/3] overflow-hidden bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring" aria-label={`Read ${project.title} case study`}>
        <MediaImage asset={project.cover} className="size-full" imageClassName="transition-transform duration-700 ease-out group-hover:scale-[1.035] motion-reduce:transition-none" fallbackLabel="Managed project cover" sizes="(max-width: 768px) 95vw, (max-width: 1280px) 45vw, 30vw" />
        {project.featured_rank && <span className="absolute left-4 top-4 z-20 rounded-full border border-white/20 bg-ink/60 px-3 py-1.5 font-mono text-[0.6rem] uppercase tracking-[0.14em] text-white backdrop-blur-md">Featured 0{project.featured_rank}</span>}
      </Link>
      <article className="flex flex-1 flex-col justify-between p-6">
        <div>
          <div className="flex flex-wrap items-center gap-2">{project.categories.slice(0, 2).map((category) => <Badge key={category.id} variant="muted">{category.name}</Badge>)}{verifiedMetrics.length > 0 && <Badge variant="verified"><ShieldCheck aria-hidden="true" />Verified outcome</Badge>}</div>
          <h2 className="mt-5 font-display text-4xl leading-[0.92] tracking-[-0.052em]"><Link href={`/projects/${project.slug}`} className="focus-visible:rounded-lg">{project.title}</Link></h2>
          <p className="mt-4 text-sm leading-6 text-muted-foreground">{project.summary}</p>
        </div>
        <div className="mt-8 flex items-end justify-between gap-5 border-t border-border pt-5">
          <div className="font-mono text-[0.62rem] uppercase tracking-[0.12em] text-muted-foreground">{[project.year, project.role].filter(Boolean).join(" · ")}</div>
          <Button asChild variant="ghost" size="icon-sm"><Link href={`/projects/${project.slug}`} aria-label={`Open ${project.title}`}><ArrowRight aria-hidden="true" /></Link></Button>
        </div>
      </article>
    </Card>
  );
}
