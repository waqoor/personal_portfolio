import { Badge, Button, Card } from "@portfolio/ui";
import { ArrowRight, Compass, Download, GraduationCap, Link2, MapPin, Sparkles } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { DiscoverySignals } from "@/components/discovery-signals";
import { ExternalLink } from "@/components/external-link";
import { MediaImage } from "@/components/media-image";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { ProfileCtaLink } from "@/components/profile-cta-link";
import { getPublicApi, loadApi } from "@/lib/api";
import { formatYear } from "@/lib/format-date";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/about", {
    title: "About Yazeed Hasan",
    description: "Personal context, strengths, interests, education, and links for Yazeed Hasan.",
  });
}

export default async function AboutPage() {
  const api = getPublicApi();
  const result = await loadApi(() => Promise.all([
    api.public.getProfilePage(),
    api.public.getSkills(),
  ]));
  if (!result.ok) return <PublicDataUnavailable reference={result.error.requestId} />;

  const [{ education, presentation, profile }, skills] = result.data;
  const skillGroups = skills.reduce((groups, skill) => {
    const category = skill.category || "Technology";
    groups.set(category, [...(groups.get(category) ?? []), skill]);
    return groups;
  }, new Map<string, typeof skills>());

  return (
    <main id="main-content">
      <DiscoverySignals path="/about" />
      <header className="coordinate-grid overflow-hidden border-b border-border">
        <div className="site-shell grid min-h-[calc(100svh-4.5rem)] gap-10 py-12 lg:grid-cols-[1.05fr_0.75fr] lg:items-center lg:py-16">
          <div className="relative z-10 py-6">
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant={profile.availability.status === "available" ? "verified" : "signal"}>
                <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />
                {profile.availability.label}
              </Badge>
              {profile.public_location && (
                <span className="inline-flex items-center gap-1.5 font-mono text-[0.66rem] uppercase tracking-[0.13em] text-muted-foreground">
                  <MapPin className="size-3.5 text-primary" aria-hidden="true" />
                  {profile.public_location}
                </span>
              )}
            </div>
            <p className="eyebrow mt-9">About / 01</p>
            <h1 className="display-lg mt-6 max-w-[10ch]">{presentation.about_title}</h1>
            <p className="mt-7 max-w-2xl font-display text-[clamp(1.35rem,2.5vw,2.1rem)] leading-[1.15] tracking-[-0.035em] text-muted-foreground">
              {presentation.about_intro}
            </p>
            <p className="mt-6 max-w-2xl text-base leading-8 text-muted-foreground">{profile.short_bio}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              {profile.resume && (
                <Button asChild variant="signal" size="lg">
                  <a href="/resume" download><Download aria-hidden="true" />Download résumé</a>
                </Button>
              )}
              <Button asChild variant="outline" size="lg">
                <Link href="/projects">Explore projects <ArrowRight aria-hidden="true" /></Link>
              </Button>
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-[35rem] self-end lg:mx-0 lg:ml-auto">
            <div className="absolute -inset-16 -z-10 rounded-full bg-primary/12 blur-3xl" aria-hidden="true" />
            <div className="relative aspect-[4/5] overflow-hidden rounded-[clamp(1.75rem,4vw,3.5rem)] border border-border-strong bg-[linear-gradient(155deg,color-mix(in_oklab,var(--primary)_12%,var(--muted)),var(--background))] shadow-[0_50px_140px_-68px_var(--shadow-ink)]">
              <MediaImage
                asset={profile.portrait}
                eager
                className="size-full bg-transparent"
                imageClassName="object-contain object-bottom"
                fallbackLabel="Managed portrait of Yazeed Hasan"
                sizes="(max-width: 1024px) 90vw, 38vw"
              />
              <div className="absolute inset-x-5 bottom-5 z-20 flex items-end justify-between gap-4 rounded-2xl border border-white/15 bg-ink/72 p-5 text-white backdrop-blur-lg">
                <div><p className="font-mono text-[0.58rem] uppercase tracking-[0.15em] text-white/55">Identity / YH</p><p className="mt-2 text-sm font-semibold">{profile.name}</p></div>
                <Sparkles className="size-5 text-primary" aria-hidden="true" />
              </div>
            </div>
          </div>
        </div>
      </header>

      <section className="site-shell section-space grid gap-10 lg:grid-cols-[0.34fr_1fr]" aria-labelledby="direction-heading">
        <div>
          <div className="flex items-center gap-3"><Compass className="size-5 text-primary" aria-hidden="true" /><p className="eyebrow">Focus & direction</p></div>
          <p className="mt-5 font-mono text-[0.65rem] uppercase leading-6 tracking-[0.13em] text-muted-foreground">Applied AI<br />Product strategy<br />Open source<br />Data-driven decisions</p>
        </div>
        <div>
          <h2 id="direction-heading" className="sr-only">Professional focus and direction</h2>
          {profile.long_bio ? (
            <div className="whitespace-pre-line font-display text-[clamp(1.8rem,3.6vw,3.7rem)] leading-[1.08] tracking-[-0.045em]">{profile.long_bio}</div>
          ) : (
            <p className="font-display text-3xl leading-tight tracking-[-0.04em]">Building useful, governed systems across AI, data, product, and delivery.</p>
          )}
          <div className="mt-9 flex flex-wrap gap-3">
            {profile.socials.map((social) => (
              <Button asChild variant="outline" key={social.id}>
                <ExternalLink href={social.url}><Link2 aria-hidden="true" />{social.label}</ExternalLink>
              </Button>
            ))}
            {profile.public_email && (
              <Button asChild variant="outline"><a href={`mailto:${profile.public_email}`}>{profile.public_email}</a></Button>
            )}
          </div>
        </div>
      </section>

      {skills.length > 0 && (
        <section className="border-y border-border bg-muted/45">
          <div className="site-shell section-space">
            <p className="eyebrow">Technical range</p>
            <div className="mt-7 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
              <h2 className="display-md max-w-[11ch]">From model thinking to operated systems.</h2>
              <p className="max-w-xl text-sm leading-7 text-muted-foreground">Every item here is managed from the Skills area in the private admin panel.</p>
            </div>
            <div className="mt-12 grid gap-5 lg:grid-cols-2">
              {[...skillGroups.entries()].map(([category, items], groupIndex) => (
                <Card key={category} variant={groupIndex === 0 ? "contrast" : "raised"} className="p-6 sm:p-8">
                  <div className="flex items-center justify-between gap-4"><h3 className="font-display text-3xl tracking-[-0.045em]">{category}</h3><span className={`font-mono text-[0.58rem] uppercase tracking-[0.14em] ${groupIndex === 0 ? "text-background" : "text-muted-foreground"}`}>{String(groupIndex + 1).padStart(2, "0")}</span></div>
                  <div className="mt-7 flex flex-wrap gap-2">
                    {items.map((skill) => <Badge key={skill.id} variant={groupIndex === 0 ? "signal" : "muted"} className={groupIndex === 0 ? "text-primary dark:text-background" : undefined}>{skill.name}</Badge>)}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </section>
      )}

      {education.length > 0 && (
        <section className="site-shell section-space">
          <div className="flex items-center gap-3"><GraduationCap className="size-5 text-primary" aria-hidden="true" /><p className="eyebrow">Education</p></div>
          <div className="mt-9 grid gap-5 lg:grid-cols-2">
            {education.map((item) => (
              <Card key={item.id} variant="raised" className="p-7 sm:p-9">
                <p className="font-mono text-[0.62rem] uppercase tracking-[0.13em] text-muted-foreground">{[formatYear(item.start_date), formatYear(item.end_date)].filter(Boolean).join(" — ")}</p>
                <h2 className="mt-5 font-display text-4xl leading-none tracking-[-0.05em]">{item.credential}</h2>
                {item.field && <p className="mt-3 font-semibold">{item.field}</p>}
                <p className="mt-4 text-sm text-muted-foreground">{item.institution}{item.location ? ` · ${item.location}` : ""}</p>
                {item.details && <p className="mt-6 border-t border-border pt-5 text-sm leading-7 text-muted-foreground">{item.details}</p>}
                {item.achievements.length > 0 && <ul className="mt-5 grid gap-3">{item.achievements.map((achievement) => <li key={achievement} className="border-l-2 border-primary pl-4 text-sm leading-6">{achievement}</li>)}</ul>}
              </Card>
            ))}
          </div>
        </section>
      )}

      <section className="border-t border-border bg-foreground text-background">
        <div className="site-shell section-space flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div><p className="eyebrow text-background/70">Next chapter</p><h2 className="display-md mt-7 max-w-[11ch]">See the evidence behind the profile.</h2></div>
          <div className="flex flex-wrap gap-3"><Button asChild variant="signal" size="lg"><Link href="/achievements">Achievements <ArrowRight aria-hidden="true" /></Link></Button>{profile.primary_cta && <Button asChild variant="outline" size="lg" className="border-background/30 text-background hover:bg-background/10"><ProfileCtaLink url={profile.primary_cta.url}>{profile.primary_cta.label}</ProfileCtaLink></Button>}</div>
        </div>
      </section>
    </main>
  );
}
