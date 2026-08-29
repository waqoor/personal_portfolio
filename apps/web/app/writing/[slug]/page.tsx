import { Badge, Button } from "@portfolio/ui";
import { ArrowLeft, ArrowRight, Clock3 } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { DiscoverySignals } from "@/components/discovery-signals";
import { MediaImage } from "@/components/media-image";
import { ArticleContent } from "@/features/writing/article-content";
import { ArticleCard } from "@/features/writing/article-card";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";
type Params = Promise<{ slug: string }>;

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  return discoveryMetadata(`/writing/${slug}`, { title: "Article" });
}

export default async function ArticlePage({ params }: { params: Params }) {
  const { slug } = await params;
  const result = await loadApi(() => getPublicApi().public.getArticle(slug));
  if (!result.ok) { if (result.error.status === 404) notFound(); throw new Error(result.error.message); }
  const article = result.data;
  return (
    <main id="main-content">
      <DiscoverySignals path={`/writing/${slug}`} />
      <header className="coordinate-grid border-b border-border"><div className="site-shell-narrow section-space pb-12"><Button asChild variant="text"><Link href="/writing" prefetch={false}><ArrowLeft aria-hidden="true" />Writing index</Link></Button><div className="mt-10 flex flex-wrap gap-2">{article.topics.map((topic) => <Badge key={topic} variant="signal">{topic}</Badge>)}</div><h1 className="display-lg mt-7 max-w-[12ch]">{article.title}</h1><p className="mt-7 max-w-3xl text-lg leading-8 text-muted-foreground">{article.excerpt}</p><div className="mt-7 flex flex-wrap items-center gap-4 font-mono text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground"><time dateTime={article.published_at}>{new Date(article.published_at).toLocaleDateString("en", { dateStyle: "long", timeZone: "UTC" })}</time><span className="inline-flex items-center gap-1.5"><Clock3 className="size-3.5" aria-hidden="true" />{article.reading_minutes} min read</span></div></div><div className="site-shell pb-10"><MediaImage asset={article.cover} eager className="aspect-[16/8] rounded-[clamp(1.5rem,4vw,3.5rem)] border border-border-strong" fallbackLabel="Managed article cover" sizes="95vw" /></div></header>
      <article className="site-shell-narrow section-space"><ArticleContent blocks={article.blocks} /></article>
      {article.related_articles.length > 0 && <section className="border-t border-border bg-muted/45"><div className="site-shell section-space"><div className="flex flex-col items-start gap-6 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">Keep reading</p><h2 className="display-md mt-6">Related field notes.</h2></div><Button asChild variant="text"><Link href="/writing" prefetch={false}>All writing <ArrowRight aria-hidden="true" /></Link></Button></div><div className={`mt-10 grid gap-5 ${article.related_articles.length === 1 ? "max-w-2xl" : article.related_articles.length === 2 ? "md:grid-cols-2" : "md:grid-cols-2 xl:grid-cols-3"}`}>{article.related_articles.slice(0, 3).map((related) => <ArticleCard key={related.id} article={related} />)}</div></div></section>}
    </main>
  );
}
