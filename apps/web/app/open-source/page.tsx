import { Badge, Button, Card, EmptyState } from "@portfolio/ui";
import { ArrowRight, GitBranch, GitFork, HeartHandshake, PackageOpen, Star } from "lucide-react";
import type { Metadata } from "next";
import { DiscoverySignals } from "@/components/discovery-signals";
import { ExternalLink } from "@/components/external-link";
import { PageIntro } from "@/components/page-intro";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/open-source", { title: "Open source" });
}

export default async function OpenSourcePage() {
  const result = await loadApi(() => getPublicApi().public.getOpenSource());
  if (!result.ok) return <PublicDataUnavailable reference={result.error.requestId} />;
  return (
    <main id="main-content">
      <DiscoverySignals path="/open-source" />
      <PageIntro eyebrow="Open source" title={result.data.presentation.open_source_title} description={result.data.presentation.open_source_intro} />
      <section className="site-shell section-space">{result.data.items.length > 0 ? <div className={`grid gap-5 ${result.data.items.length === 1 ? "max-w-4xl" : "md:grid-cols-2"}`}>{result.data.items.map((item, index) => <Card key={item.id} variant={index === 0 ? "contrast" : "raised"} className="flex min-h-96 flex-col justify-between p-6 sm:p-8"><div><div className="flex items-start justify-between gap-4"><GitBranch className={`size-8 ${index === 0 ? "text-primary dark:text-background" : "text-muted-foreground"}`} aria-hidden="true" /><div className="flex gap-2">{item.language && <Badge variant={index === 0 ? "outline" : "muted"}>{item.language}</Badge>}{item.status_label && <Badge variant={index === 0 ? "outline" : "signal"}>{item.status_label}</Badge>}</div></div><h2 className="mt-10 font-display text-5xl leading-[0.9] tracking-[-0.055em]">{item.name}</h2><p className={`mt-5 text-sm leading-7 ${index === 0 ? "text-background/65" : "text-muted-foreground"}`}>{item.description}</p><div className="mt-6 flex flex-wrap gap-2">{item.skills.map((skill) => <Badge key={skill.id} variant={index === 0 ? "outline" : "muted"}>{skill.name}</Badge>)}</div>{item.metadata_fetched_at && <p className={`mt-6 font-mono text-[0.62rem] uppercase tracking-[0.1em] ${index === 0 ? "text-background/70" : "text-muted-foreground"}`}>{item.metadata_provider} source · {item.metadata_freshness === "stale" ? "stale snapshot" : "current snapshot"} · <time dateTime={item.metadata_fetched_at}>{new Date(item.metadata_fetched_at).toLocaleDateString("en", { dateStyle: "medium", timeZone: "UTC" })}</time></p>}</div><div className="mt-10 flex items-end justify-between gap-5"><div className={`flex gap-4 font-mono text-[0.65rem] uppercase tracking-[0.1em] ${index === 0 ? "text-background/70" : "text-muted-foreground"}`}>{item.stars !== undefined && <span className="inline-flex items-center gap-1.5"><Star className="size-3.5" aria-hidden="true" />{item.stars}</span>}{item.forks !== undefined && <span className="inline-flex items-center gap-1.5"><GitFork className="size-3.5" aria-hidden="true" />{item.forks}</span>}</div><Button asChild variant={index === 0 ? "signal" : "outline"}><ExternalLink href={item.repository_url}>Repository <ArrowRight aria-hidden="true" /></ExternalLink></Button></div></Card>)}</div> : <EmptyState icon={<PackageOpen className="size-5" />} title="No open-source work is published" description="Published repositories and contribution work will appear here when they are available." />}</section>
      {result.data.sponsorship?.enabled && <section className="border-t border-border bg-primary text-primary-foreground"><div className="site-shell section-space grid gap-10 lg:grid-cols-[1fr_0.65fr] lg:items-end"><div><HeartHandshake className="size-9" aria-hidden="true" /><h2 className="display-lg mt-8 max-w-[11ch]">{result.data.sponsorship.title}</h2></div><div><p className="text-base leading-7 text-primary-foreground/75">{result.data.sponsorship.description}</p><ul className="mt-6 grid gap-2 text-sm font-semibold">{result.data.sponsorship.principles.map((principle) => <li key={principle} className="flex gap-3"><span aria-hidden="true">—</span>{principle}</li>)}</ul><div className="mt-7 flex flex-wrap gap-3">{result.data.sponsorship.links.map((link) => <Button key={link.url} asChild variant="primary"><ExternalLink href={link.url}>{link.label}</ExternalLink></Button>)}</div></div></div></section>}
    </main>
  );
}
