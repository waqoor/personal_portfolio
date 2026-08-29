import { Badge, Button, Card } from "@portfolio/ui";
import { ArrowRight, BriefcaseBusiness, CalendarRange, MapPin } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { DiscoverySignals } from "@/components/discovery-signals";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { getPublicApi, loadApi } from "@/lib/api";
import { formatMonthYear } from "@/lib/format-date";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/work", {
    title: "Work — Yazeed Hasan",
    description: "Yazeed Hasan's full-time, contract, part-time, freelance, and project-based experience.",
  });
}

export default async function WorkPage() {
  const result = await loadApi(() => getPublicApi().public.getProfilePage());
  if (!result.ok) return <PublicDataUnavailable reference={result.error.requestId} />;
  const { experience, presentation } = result.data;
  const organizations = new Set(experience.map((item) => item.organization)).size;
  const contexts = new Set(experience.map((item) => item.employment_type).filter(Boolean)).size;

  return (
    <main id="main-content">
      <DiscoverySignals path="/work" />
      <header className="coordinate-grid border-b border-border">
        <div className="site-shell section-space">
          <p className="eyebrow">Work / 03</p>
          <div className="mt-7 grid gap-8 lg:grid-cols-[1fr_0.45fr] lg:items-end">
            <div><h1 className="display-lg max-w-[11ch]">{presentation.work_title}</h1><p className="mt-7 max-w-3xl text-lg leading-8 text-muted-foreground">{presentation.work_intro}</p></div>
            <dl className="grid grid-cols-3 overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-surface-raised">
              <div className="border-r border-border p-5"><dt className="font-mono text-[0.56rem] uppercase tracking-[0.13em] text-muted-foreground">Roles</dt><dd className="mt-3 font-display text-4xl tracking-[-0.05em]">{experience.length}</dd></div>
              <div className="border-r border-border p-5"><dt className="font-mono text-[0.56rem] uppercase tracking-[0.13em] text-muted-foreground">Organizations</dt><dd className="mt-3 font-display text-4xl tracking-[-0.05em]">{organizations}</dd></div>
              <div className="p-5"><dt className="font-mono text-[0.56rem] uppercase tracking-[0.13em] text-muted-foreground">Formats</dt><dd className="mt-3 font-display text-4xl tracking-[-0.05em]">{contexts}</dd></div>
            </dl>
          </div>
        </div>
      </header>

      <section className="site-shell section-space" aria-labelledby="work-ledger-heading">
        <div className="flex items-center gap-3"><BriefcaseBusiness className="size-5 text-primary" aria-hidden="true" /><h2 id="work-ledger-heading" className="eyebrow">Professional ledger</h2></div>
        {experience.length > 0 ? (
          <ol className="relative mt-12 ml-2 border-l border-border-strong sm:ml-4">
            {experience.map((item, index) => (
              <li key={item.id} id={`experience-${item.id}`} className="relative pb-10 pl-8 last:pb-0 sm:pl-12">
                <span className="absolute -left-[0.48rem] top-8 size-3.5 rounded-full border-4 border-background bg-primary shadow-[0_0_0_1px_var(--border-strong)]" aria-hidden="true" />
                <Card variant={index === 0 ? "contrast" : "raised"} className="overflow-hidden">
                  <div className="grid lg:grid-cols-[0.3fr_0.7fr]">
                    <div className={`border-b p-6 lg:border-r lg:border-b-0 sm:p-8 ${index === 0 ? "border-background/15" : "border-border"}`}>
                      <p className={`font-mono text-[0.62rem] uppercase leading-6 tracking-[0.13em] ${index === 0 ? "text-background/70" : "text-muted-foreground"}`}>
                        {formatMonthYear(item.start_date)} — {item.current ? "Present" : formatMonthYear(item.end_date)}
                      </p>
                      {item.employment_type && <Badge variant={index === 0 ? "signal" : "muted"} className={index === 0 ? "mt-5 text-primary dark:text-background" : "mt-5"}>{item.employment_type}</Badge>}
                      <div className={`mt-6 grid gap-3 text-sm ${index === 0 ? "text-background/65" : "text-muted-foreground"}`}>
                        {item.location && <span className="flex items-center gap-2"><MapPin className="size-4 text-primary" aria-hidden="true" />{item.location}</span>}
                        <span className="flex items-center gap-2"><CalendarRange className="size-4 text-primary" aria-hidden="true" />{item.current ? "Current role" : "Completed engagement"}</span>
                      </div>
                    </div>
                    <article className="p-6 sm:p-8 lg:p-10">
                      <p className={`text-sm font-semibold ${index === 0 ? "text-background/65" : "text-muted-foreground"}`}>{item.organization}</p>
                      <h3 className="mt-3 font-display text-[clamp(2rem,4vw,4rem)] leading-[0.95] tracking-[-0.052em]">{item.role}</h3>
                      <p className={`mt-6 max-w-4xl text-sm leading-7 ${index === 0 ? "text-background/70" : "text-muted-foreground"}`}>{item.summary}</p>
                      {item.achievements.length > 0 && (
                        <div className={`mt-8 border-t pt-7 ${index === 0 ? "border-background/15" : "border-border"}`}>
                          <p className={`font-mono text-[0.58rem] uppercase tracking-[0.14em] ${index === 0 ? "text-background/70" : "text-muted-foreground"}`}>Selected responsibilities and engagements</p>
                          <ul className="mt-5 grid gap-4 xl:grid-cols-2">
                            {item.achievements.map((achievement) => <li key={achievement} className="grid grid-cols-[auto_1fr] gap-3 text-sm leading-6"><span className="mt-2 size-1.5 rounded-full bg-primary" aria-hidden="true" />{achievement}</li>)}
                          </ul>
                        </div>
                      )}
                      {item.skills.length > 0 && <div className="mt-7 flex flex-wrap gap-2">{item.skills.map((skill) => <Badge key={skill.id} variant={index === 0 ? "signal" : "muted"} className={index === 0 ? "text-primary dark:text-background" : undefined}>{skill.name}</Badge>)}</div>}
                    </article>
                  </div>
                </Card>
              </li>
            ))}
          </ol>
        ) : (
          <Card className="mt-10 p-8"><p className="text-muted-foreground">No published work history is available yet.</p></Card>
        )}
      </section>

      <section className="border-t border-border bg-primary/10">
        <div className="site-shell section-space flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div><p className="eyebrow">Owned work</p><h2 className="display-md mt-7 max-w-[12ch]">The products and open work live separately.</h2></div>
          <Button asChild variant="signal" size="lg"><Link href="/projects">Open the project archive <ArrowRight aria-hidden="true" /></Link></Button>
        </div>
      </section>
    </main>
  );
}
