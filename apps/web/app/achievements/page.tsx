import { Badge, Button, Card } from "@portfolio/ui";
import { ArrowRight, Award, BookOpenText, CheckCircle2, ExternalLink, Medal, Trophy } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { DiscoverySignals } from "@/components/discovery-signals";
import { ExternalLink as SafeExternalLink } from "@/components/external-link";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { getPublicApi, loadApi } from "@/lib/api";
import { formatMonthYear, formatYear } from "@/lib/format-date";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/achievements", {
    title: "Achievements — Yazeed Hasan",
    description: "Certifications, awards, professional milestones, academic recognition, and published research by Yazeed Hasan.",
  });
}

export default async function AchievementsPage() {
  const api = getPublicApi();
  const result = await loadApi(() => Promise.all([
    api.public.getProfilePage(),
    api.public.getArticles({ topic: "Publication", pageSize: 100 }),
  ]));
  if (!result.ok) return <PublicDataUnavailable reference={result.error.requestId} />;

  const [{ certifications, education, experience, presentation }, publications] = result.data;
  const recognition = certifications.filter((item) => item.description?.startsWith("Recognition:"));
  const credentials = certifications.filter((item) => !item.description?.startsWith("Recognition:"));
  const milestoneCount = experience.reduce((total, item) => total + item.achievements.length, 0);

  return (
    <main id="main-content">
      <DiscoverySignals path="/achievements" />
      <header className="relative overflow-hidden border-b border-border bg-foreground text-background">
        <div className="absolute inset-0 coordinate-grid opacity-20" aria-hidden="true" />
        <div className="absolute -right-40 -top-48 size-[38rem] rounded-full border border-primary/25" aria-hidden="true"><div className="absolute inset-20 rounded-full border border-primary/20" /><div className="absolute inset-40 rounded-full bg-primary/10 blur-2xl" /></div>
        <div className="site-shell section-space relative z-10">
          <p className="eyebrow text-background/70">Achievements / 02</p>
          <div className="mt-7 grid gap-8 lg:grid-cols-[1fr_0.4fr] lg:items-end">
            <div><h1 className="display-lg max-w-[11ch]">{presentation.achievements_title}</h1><p className="mt-7 max-w-3xl text-lg leading-8 text-background/65">{presentation.achievements_intro}</p></div>
            <dl className="grid grid-cols-3 overflow-hidden rounded-[var(--radius-card)] border border-background/15 bg-background/[0.045] backdrop-blur-sm">
              <div className="border-r border-background/15 p-5"><dt className="font-mono text-[0.54rem] uppercase tracking-[0.13em] text-background/70">Credentials</dt><dd className="mt-3 font-display text-4xl">{credentials.length}</dd></div>
              <div className="border-r border-background/15 p-5"><dt className="font-mono text-[0.54rem] uppercase tracking-[0.13em] text-background/70">Recognition</dt><dd className="mt-3 font-display text-4xl">{recognition.length}</dd></div>
              <div className="p-5"><dt className="font-mono text-[0.54rem] uppercase tracking-[0.13em] text-background/70">Milestones</dt><dd className="mt-3 font-display text-4xl">{milestoneCount}</dd></div>
            </dl>
          </div>
        </div>
      </header>

      {recognition.length > 0 && (
        <section className="site-shell section-space" aria-labelledby="recognition-heading">
          <div className="flex items-center gap-3"><Trophy className="size-5 text-primary" aria-hidden="true" /><p className="eyebrow">Awards & recognition</p></div>
          <h2 id="recognition-heading" className="display-md mt-7 max-w-[12ch]">Recognition attached to specific work.</h2>
          <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {recognition.map((item, index) => (
              <Card key={item.id} variant={index === 0 ? "contrast" : "raised"} className="flex min-h-72 flex-col justify-between p-7">
                <div className="flex items-start justify-between gap-4"><span className="grid size-11 place-items-center rounded-full bg-primary/14 text-primary"><Medal className="size-5" aria-hidden="true" /></span><span className={`font-mono text-[0.58rem] uppercase tracking-[0.13em] ${index === 0 ? "text-background" : "text-muted-foreground"}`}>{formatYear(item.issued_at) ?? "Recognition"}</span></div>
                <div className="mt-10"><h3 className="font-display text-3xl leading-none tracking-[-0.045em]">{item.name}</h3><p className="mt-4 text-sm font-semibold opacity-65">{item.issuer}</p>{item.description && <p className="mt-5 text-sm leading-7 opacity-65">{item.description.replace(/^Recognition:\s*/, "")}</p>}</div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {credentials.length > 0 && (
        <section className="border-y border-border bg-muted/45">
          <div className="site-shell section-space">
            <div className="flex items-center gap-3"><Award className="size-5 text-primary" aria-hidden="true" /><p className="eyebrow">Certifications</p></div>
            <div className="mt-8 overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-surface-raised">
              {credentials.map((item, index) => (
                <article key={item.id} className="grid gap-5 border-b border-border p-6 last:border-b-0 md:grid-cols-[auto_1fr_auto] md:items-center sm:p-7">
                  <span className="grid size-11 place-items-center rounded-full bg-primary/12 text-accent-ink dark:text-primary"><CheckCircle2 className="size-5" aria-hidden="true" /></span>
                  <div><div className="flex flex-wrap items-center gap-3"><h2 className="font-semibold">{item.name}</h2>{index === 0 && <Badge variant="signal">Latest</Badge>}</div><p className="mt-2 text-sm text-muted-foreground">{item.issuer}{item.issued_at ? ` · ${formatMonthYear(item.issued_at)}` : ""}</p>{item.description && <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">{item.description}</p>}</div>
                  {item.credential_url ? <Button asChild variant="outline"><SafeExternalLink href={item.credential_url}>Verify <ExternalLink aria-hidden="true" /></SafeExternalLink></Button> : <span className="font-mono text-[0.56rem] uppercase tracking-[0.12em] text-muted-foreground">Résumé-backed record</span>}
                </article>
              ))}
            </div>
          </div>
        </section>
      )}

      {publications.items.length > 0 && (
        <section className="site-shell section-space" aria-labelledby="publications-heading">
          <div className="flex items-center gap-3"><BookOpenText className="size-5 text-primary" aria-hidden="true" /><p className="eyebrow">Papers & publications</p></div>
          <div className="mt-8 grid gap-5 lg:grid-cols-[0.42fr_1fr]">
            <div><h2 id="publications-heading" className="display-md max-w-[10ch]">Research made reproducible.</h2><p className="mt-6 text-sm leading-7 text-muted-foreground">Published work is managed as canonical Writing content so the record, source link, and discovery metadata stay in one place.</p></div>
            <div className="grid gap-4">
              {publications.items.map((publication) => (
                <Card key={publication.id} variant="raised" className="p-7 sm:p-9">
                  <div className="flex flex-wrap gap-2">{publication.topics.map((topic) => <Badge key={topic} variant="muted">{topic}</Badge>)}</div>
                  <h3 className="mt-7 font-display text-[clamp(2rem,4vw,3.8rem)] leading-[0.96] tracking-[-0.052em]">{publication.title}</h3>
                  <p className="mt-6 text-sm leading-7 text-muted-foreground">{publication.excerpt}</p>
                  <Button asChild variant="text" className="mt-6"><Link href={`/writing/${publication.slug}`}>Read publication record <ArrowRight aria-hidden="true" /></Link></Button>
                </Card>
              ))}
            </div>
          </div>
        </section>
      )}

      {experience.some((item) => item.achievements.length > 0) && (
        <section className="border-t border-border bg-primary/10">
          <div className="site-shell section-space">
            <p className="eyebrow">Professional milestones</p>
            <h2 className="display-md mt-7 max-w-[12ch]">Outcomes organized by responsibility.</h2>
            <div className="mt-10 grid gap-5 lg:grid-cols-2">
              {experience.filter((item) => item.achievements.length > 0).map((item) => (
                <Card key={item.id} className="p-6 sm:p-8">
                  <p className="font-mono text-[0.58rem] uppercase tracking-[0.13em] text-muted-foreground">{item.organization}</p>
                  <h3 className="mt-4 font-display text-3xl leading-none tracking-[-0.045em]">{item.role}</h3>
                  <ul className="mt-6 grid gap-4">{item.achievements.map((achievement) => <li key={achievement} className="grid grid-cols-[auto_1fr] gap-3 text-sm leading-6"><span className="mt-2 size-1.5 rounded-full bg-primary" aria-hidden="true" />{achievement}</li>)}</ul>
                </Card>
              ))}
            </div>
          </div>
        </section>
      )}

      {education.some((item) => item.achievements.length > 0) && (
        <section className="site-shell pb-[clamp(5rem,10vw,10rem)]">
          <Card variant="contrast" className="flex flex-col gap-7 p-7 sm:p-10 lg:flex-row lg:items-end lg:justify-between">
            <div><p className="eyebrow text-background/70">Academic recognition</p><h2 className="mt-6 font-display text-4xl tracking-[-0.05em]">{education[0]?.institution}</h2><ul className="mt-6 grid gap-3">{education.flatMap((item) => item.achievements).map((achievement) => <li key={achievement} className="flex gap-3 text-sm leading-6 text-background/70"><span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary dark:bg-background" aria-hidden="true" />{achievement}</li>)}</ul></div>
            <Button asChild variant="signal"><Link href="/work">Continue to work history <ArrowRight aria-hidden="true" /></Link></Button>
          </Card>
        </section>
      )}
    </main>
  );
}
