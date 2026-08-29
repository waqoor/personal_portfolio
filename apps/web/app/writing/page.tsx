import { Button, EmptyState, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@portfolio/ui";
import { BookX, Search, X } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { DiscoverySignals } from "@/components/discovery-signals";
import { PageIntro } from "@/components/page-intro";
import { Pagination } from "@/components/pagination";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { ArticleCard } from "@/features/writing/article-card";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";
type SearchParams = Promise<Record<string, string | string[] | undefined>>;

function valueOf(value: string | string[] | undefined): string | undefined {
  const first = Array.isArray(value) ? value[0] : value;
  return first && first !== "all" ? first.slice(0, 120) : undefined;
}

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/writing", { title: "Writing" });
}

export default async function WritingPage({ searchParams }: { searchParams: SearchParams }) {
  const params = await searchParams;
  const topic = valueOf(params.topic);
  const search = valueOf(params.q);
  const rawPage = Number.parseInt(valueOf(params.page) ?? "1", 10);
  const page = Number.isFinite(rawPage) && rawPage > 0 ? rawPage : 1;
  const result = await loadApi(() => getPublicApi().public.getArticles({ page, pageSize: 10, topic, search }));
  if (!result.ok) return <PublicDataUnavailable reference={result.error.requestId} />;
  const [featured, ...articles] = result.data.items;

  return (
    <main id="main-content">
      <DiscoverySignals path="/writing" />
      <PageIntro eyebrow="Writing / Field notes" title={result.data.presentation.writing_title} description={result.data.presentation.writing_intro} />
      <section className="site-shell section-space">
        <form method="get" action="/writing" role="search" className="grid gap-4 rounded-[var(--radius-card)] border border-border-strong bg-surface-raised p-5 md:grid-cols-[1fr_0.7fr_auto] md:items-end"><div className="grid gap-2"><Label htmlFor="article-search">Search writing</Label><div className="relative"><Search className="absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" /><Input id="article-search" name="q" defaultValue={search} placeholder="Topic, title, idea…" className="pl-11" /></div></div><div className="grid gap-2"><Label htmlFor="topic-filter">Topic</Label><Select name="topic" defaultValue={topic ?? "all"}><SelectTrigger id="topic-filter"><SelectValue placeholder="All topics" /></SelectTrigger><SelectContent><SelectItem value="all">All topics</SelectItem>{result.data.topics.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></div><div className="flex gap-2"><Button type="submit" variant="signal">Filter</Button>{(topic || search) && <Button asChild variant="ghost" size="icon" aria-label="Clear filters"><Link href="/writing"><X aria-hidden="true" /></Link></Button>}</div></form>
        {featured ? <><div className="mt-10"><ArticleCard article={featured} featured /></div>{articles.length > 0 && <div className="mt-5 grid gap-5 md:grid-cols-2 xl:grid-cols-3">{articles.map((article) => <ArticleCard key={article.id} article={article} />)}</div>}</> : <EmptyState className="mt-10" icon={<BookX className="size-5" />} title="No articles match" description="Try clearing the filters. Draft writing remains unavailable until explicitly published." />}
        <Pagination page={result.data.page_info.page} totalPages={result.data.page_info.total_pages} path="/writing" query={{ topic, q: search }} />
      </section>
    </main>
  );
}
