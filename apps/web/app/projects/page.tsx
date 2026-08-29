import type { Metadata } from "next";
import { EmptyState } from "@portfolio/ui";
import { FolderSearch } from "lucide-react";
import { DiscoverySignals } from "@/components/discovery-signals";
import { PageIntro } from "@/components/page-intro";
import { Pagination } from "@/components/pagination";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { ProjectCard } from "@/features/projects/project-card";
import { ProjectFilters } from "@/features/projects/project-filters";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function stringParam(value: string | string[] | undefined): string | undefined {
  const resolved = Array.isArray(value) ? value[0] : value;
  return resolved && resolved !== "all" ? resolved.slice(0, 120) : undefined;
}

function pageParam(value: string | string[] | undefined): number {
  const parsed = Number.parseInt(stringParam(value) ?? "1", 10);
  return Number.isFinite(parsed) && parsed > 0 ? Math.min(parsed, 10_000) : 1;
}

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/projects", { title: "Project archive" });
}

export default async function ProjectsPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const page = pageParam(params.page);
  const category = stringParam(params.category);
  const sector = stringParam(params.sector);
  const search = stringParam(params.q);
  const result = await loadApi(() => getPublicApi().public.getProjects({ page, pageSize: 12, category, sector, search }));
  if (!result.ok) return <PublicDataUnavailable reference={result.error.requestId} />;

  return (
    <main id="main-content">
      <DiscoverySignals path="/projects" />
      <PageIntro eyebrow="Complete archive" title={result.data.presentation.projects_title} description={result.data.presentation.projects_intro} />
      <section className="site-shell section-space" aria-labelledby="archive-heading">
        <h2 id="archive-heading" className="sr-only">Project archive</h2>
        <ProjectFilters categories={result.data.categories} sectors={result.data.sectors} current={{ category, sector, search }} />
        <p className="mt-6 font-mono text-[0.65rem] uppercase tracking-[0.13em] text-muted-foreground">{result.data.page_info.total} published {result.data.page_info.total === 1 ? "project" : "projects"}</p>
        {result.data.items.length > 0 ? <div className={`mt-8 grid gap-5 ${result.data.items.length === 1 ? "max-w-2xl" : result.data.items.length === 2 ? "md:grid-cols-2" : "md:grid-cols-2 xl:grid-cols-3"}`}>{result.data.items.map((project) => <ProjectCard key={project.id} project={project} />)}</div> : <EmptyState className="mt-8" icon={<FolderSearch className="size-5" />} title="No projects match" description="Try clearing a filter or using a broader search term. Draft and archived work remains private." />}
        <Pagination page={result.data.page_info.page} totalPages={result.data.page_info.total_pages} path="/projects" query={{ category, sector, q: search }} />
      </section>
    </main>
  );
}
