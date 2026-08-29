import type { ArticleSummary } from "@portfolio/api-client";
import { Badge } from "@portfolio/ui";
import { ArrowRight, BookOpenText } from "lucide-react";
import Link from "next/link";
import { MediaImage } from "@/components/media-image";

export function ArticleCard({ article, featured = false }: { article: ArticleSummary; featured?: boolean }) {
  return (
    <Link href={`/writing/${article.slug}`} className={`group grid h-full overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-surface-raised transition-[transform,border-color] hover:-translate-y-1 hover:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none ${featured ? "lg:grid-cols-[1.1fr_0.9fr]" : ""}`}>
      <MediaImage asset={article.cover} className={`min-h-60 ${featured ? "lg:min-h-[32rem]" : "aspect-[16/10]"}`} imageClassName="transition-transform duration-700 group-hover:scale-[1.03] motion-reduce:transition-none" fallbackLabel="Managed article cover" />
      <article className="flex flex-col justify-between p-6 sm:p-8">
        <div><div className="flex flex-wrap items-center gap-3 font-mono text-[0.62rem] uppercase tracking-[0.12em] text-muted-foreground"><BookOpenText className="size-3.5 text-primary" aria-hidden="true" /><span>{article.reading_minutes} min read</span><time dateTime={article.published_at}>{new Date(article.published_at).toLocaleDateString("en", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" })}</time></div><h2 className={`mt-6 font-display leading-[0.94] tracking-[-0.052em] ${featured ? "text-[clamp(2.8rem,5vw,5rem)]" : "text-4xl"}`}>{article.title}</h2><p className="mt-5 text-sm leading-7 text-muted-foreground">{article.excerpt}</p></div>
        <div className="mt-9 flex items-center justify-between gap-5"><div className="flex flex-wrap gap-2">{article.topics.slice(0, 3).map((topic) => <Badge key={topic} variant="muted">{topic}</Badge>)}</div><ArrowRight className="size-5 shrink-0 transition-transform group-hover:translate-x-1" aria-hidden="true" /></div>
      </article>
    </Link>
  );
}
