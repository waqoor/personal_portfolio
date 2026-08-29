import type { HomePage, HomepageSection } from "@portfolio/api-client";
import { Reveal, Stagger, StaggerItem } from "@portfolio/motion";
import { Badge, Button, Card } from "@portfolio/ui";
import { ArrowRight, BookOpenText, GitBranch, GitFork, HeartHandshake, Star } from "lucide-react";
import Link from "next/link";
import { ExternalLink } from "@/components/external-link";
import { MediaImage } from "@/components/media-image";
import { SectionFrame, limitBySection } from "./section-frame";

export function OpenSourceSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const items = limitBySection(data.open_source, section, 4);
  const gridColumns = items.length === 1 ? "max-w-4xl" : "md:grid-cols-2";
  return (
    <SectionFrame section={section} eyebrow="Open source" title="Built in public, maintained with intent." description="Repositories, tools, and contribution work—shown with live public signals only when the source makes them available." headerAside={section.cta_visible && <Button asChild variant="text" className="mt-5"><Link href="/open-source">Open-source index <ArrowRight aria-hidden="true" /></Link></Button>}>
      <Stagger className={`grid gap-5 ${gridColumns}`}>
        {items.map((item, index) => (
          <StaggerItem key={item.id}>
            <Card variant={index === 0 ? "contrast" : "raised"} className="group flex min-h-80 flex-col justify-between p-6 sm:p-8">
              <div>
                <div className="flex items-start justify-between gap-4"><GitBranch className={`size-7 ${index === 0 ? "text-primary" : "text-muted-foreground"}`} aria-hidden="true" /><div className="flex gap-2">{item.language && <Badge variant={index === 0 ? "outline" : "muted"}>{item.language}</Badge>}{item.status_label && <Badge variant={index === 0 ? "outline" : "signal"}>{item.status_label}</Badge>}</div></div>
                <h3 className="mt-9 font-display text-4xl leading-none tracking-[-0.05em]">{item.name}</h3><p className={`mt-4 text-sm leading-6 ${index === 0 ? "text-background/65" : "text-muted-foreground"}`}>{item.description}</p>
              </div>
              <div className="mt-8 flex items-end justify-between gap-4">
                <dl className="flex gap-4 font-mono text-[0.65rem] uppercase tracking-[0.1em] opacity-65">{item.stars !== undefined && <div className="flex items-center gap-1.5"><Star className="size-3.5" aria-hidden="true" /><dt className="sr-only">Stars</dt><dd>{item.stars}</dd></div>}{item.forks !== undefined && <div className="flex items-center gap-1.5"><GitFork className="size-3.5" aria-hidden="true" /><dt className="sr-only">Forks</dt><dd>{item.forks}</dd></div>}</dl>
                <ExternalLink href={item.repository_url} className={`font-semibold ${index === 0 ? "text-primary dark:text-background" : "text-foreground"}`}>Repository</ExternalLink>
              </div>
            </Card>
          </StaggerItem>
        ))}
      </Stagger>
    </SectionFrame>
  );
}

export function SponsorshipSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const sponsorship = data.sponsorship;
  if (!sponsorship?.enabled) return null;
  return (
    <SectionFrame section={section} className="bg-primary text-primary-foreground" contentClassName="py-[clamp(4rem,8vw,8rem)]">
      <Reveal className="grid gap-10 lg:grid-cols-[1fr_0.68fr] lg:items-end">
        <div><p className="eyebrow before:bg-primary-foreground">Open-source sponsorship</p><h2 className="display-lg mt-7 max-w-[11ch]">{section.custom_heading ?? sponsorship.title}</h2></div>
        <div><p className="max-w-xl text-base leading-7 text-primary-foreground/75">{sponsorship.description}</p>{sponsorship.principles.length > 0 && <ul className="mt-6 grid gap-2 text-sm font-semibold">{sponsorship.principles.map((principle) => <li key={principle} className="flex items-start gap-3"><HeartHandshake className="mt-0.5 size-4 shrink-0" aria-hidden="true" />{principle}</li>)}</ul>}{section.cta_visible && <div className="mt-7 flex flex-wrap gap-3">{sponsorship.links.map((link) => <Button key={link.url} asChild variant="primary"><ExternalLink href={link.url}>{link.label}</ExternalLink></Button>)}</div>}</div>
      </Reveal>
    </SectionFrame>
  );
}

export function WritingSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const items = limitBySection(data.articles, section, 4);
  const singleArticle = items.length === 1;
  return (
    <SectionFrame section={section} eyebrow="Writing / Field notes" title="Ideas made useful through explanation." description="Technical writing on intelligent systems, product engineering, data, infrastructure, and the decisions between them." headerAside={section.cta_visible && <Button asChild variant="text" className="mt-5"><Link href="/writing">Read the journal <ArrowRight aria-hidden="true" /></Link></Button>}>
      <div className={`grid gap-5 ${singleArticle ? "max-w-6xl" : "lg:grid-cols-2"}`}>
        {items.map((article, index) => (
          <Reveal key={article.id} delay={index * 0.05} className={index === 0 ? "lg:row-span-2" : undefined}>
            <Link href={`/writing/${article.slug}`} className={`group grid h-full overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-surface-raised transition-[transform,border-color] hover:-translate-y-1 hover:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none ${index === 0 ? `grid-rows-[minmax(18rem,1fr)_auto] ${singleArticle ? "lg:grid-cols-[1.05fr_0.95fr] lg:grid-rows-1" : ""}` : "sm:grid-cols-[0.5fr_1fr]"}`}>
              <MediaImage asset={article.cover} className="min-h-52 size-full" imageClassName="transition-transform duration-700 group-hover:scale-[1.03] motion-reduce:transition-none" fallbackLabel="Managed article cover" />
              <article className="flex flex-col justify-between p-6 sm:p-8">
                <div><div className="flex flex-wrap items-center gap-3 font-mono text-[0.62rem] uppercase tracking-[0.12em] text-muted-foreground"><BookOpenText className="size-3.5 text-primary" aria-hidden="true" /><span>{article.reading_minutes} min read</span><span>{new Date(article.published_at).toLocaleDateString("en", { year: "numeric", month: "short", timeZone: "UTC" })}</span></div><h3 className={`mt-5 font-display leading-[0.96] tracking-[-0.05em] ${index === 0 ? "text-4xl sm:text-5xl" : "text-3xl"}`}>{article.title}</h3><p className="mt-4 text-sm leading-6 text-muted-foreground">{article.excerpt}</p></div>
                <div className="mt-7 flex items-center justify-between gap-4"><div className="flex flex-wrap gap-2">{article.topics.slice(0, 2).map((topic) => <Badge key={topic} variant="muted">{topic}</Badge>)}</div><ArrowRight className="size-4 transition-transform group-hover:translate-x-1" aria-hidden="true" /></div>
              </article>
            </Link>
          </Reveal>
        ))}
      </div>
    </SectionFrame>
  );
}
