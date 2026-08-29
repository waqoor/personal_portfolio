import type { HomePage, HomepageSection } from "@portfolio/api-client";
import { Reveal } from "@portfolio/motion";
import { Badge, Button, Card } from "@portfolio/ui";
import { ArrowRight, Award, BookOpen, BriefcaseBusiness, ExternalLink } from "lucide-react";
import Link from "next/link";

import { ExternalLink as SafeExternalLink } from "@/components/external-link";
import { formatMonthYear } from "@/lib/format-date";

import { SectionFrame, limitBySection } from "./section-frame";

export function ExperienceSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const items = limitBySection(data.experience, section, 4);
  return (
    <SectionFrame
      section={section}
      eyebrow="Experience"
      title="A timeline of ownership, not just tenure."
      description="Roles are connected to specific achievements, domains, and technologies where that context is published."
      headerAside={section.cta_visible && <Button asChild variant="text" className="mt-5"><Link href="/work">Full work history <ArrowRight aria-hidden="true" /></Link></Button>}
    >
      <ol className="relative ml-2 border-l border-border-strong sm:ml-4">
        {items.map((item, index) => (
          <li key={item.id} className="relative pb-12 pl-8 last:pb-0 sm:pl-12">
            <span className="absolute -left-[0.46rem] top-1.5 size-3.5 rounded-full border-4 border-background bg-primary shadow-[0_0_0_1px_var(--border-strong)]" aria-hidden="true" />
            <Reveal delay={index * 0.04}>
              <div className="grid gap-6 md:grid-cols-[0.35fr_1fr]">
                <div className="font-mono text-[0.65rem] uppercase tracking-[0.14em] text-muted-foreground"><p>{formatMonthYear(item.start_date)} — {item.current ? "Present" : formatMonthYear(item.end_date)}</p>{item.location && <p className="mt-2">{item.location}</p>}</div>
                <article className="rounded-[var(--radius-card)] border border-border bg-surface-raised p-6 sm:p-8">
                  <div className="flex items-start justify-between gap-4"><div><p className="text-sm font-semibold text-muted-foreground">{item.organization}</p><h3 className="mt-2 font-display text-3xl leading-none tracking-[-0.045em]">{item.role}</h3></div><BriefcaseBusiness className="size-5 text-primary" aria-hidden="true" /></div>
                  <p className="mt-5 text-sm leading-6 text-muted-foreground">{item.summary}</p>
                  {item.achievements.length > 0 && <ul className="mt-6 grid gap-3">{item.achievements.slice(0, 3).map((achievement) => <li key={achievement} className="grid grid-cols-[auto_1fr] gap-3 text-sm leading-6"><span className="mt-2 size-1.5 rounded-full bg-primary" aria-hidden="true" />{achievement}</li>)}</ul>}
                  <div className="mt-6 flex flex-wrap gap-2">{item.skills.slice(0, 5).map((skill) => <Badge key={skill.id} variant="muted">{skill.name}</Badge>)}</div>
                </article>
              </div>
            </Reveal>
          </li>
        ))}
      </ol>
    </SectionFrame>
  );
}

export function EducationSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const education = limitBySection(data.education, section, 6);
  const gridColumns = education.length === 1 ? "max-w-4xl" : "lg:grid-cols-2";
  return (
    <SectionFrame section={section} eyebrow="Learning ledger" title="Formal learning with practical continuity." description="Education is published with only the supporting context that is useful and appropriate to share.">
      <div className={`grid gap-4 ${gridColumns}`}>
        {education.map((item) => (
          <Card key={item.id} variant="raised" className="p-6 sm:p-8">
            <div className="flex items-center gap-2 font-mono text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-muted-foreground"><BookOpen className="size-4 text-primary" aria-hidden="true" />{[item.start_date, item.end_date].filter(Boolean).join(" — ") || "Education"}</div>
            <h3 className="mt-5 font-display text-3xl leading-none tracking-[-0.045em]">{item.credential}</h3>
            {item.field && <p className="mt-2 font-semibold">{item.field}</p>}
            <p className="mt-4 text-sm text-muted-foreground">{item.institution}</p>
            {item.details && <p className="mt-4 border-t border-border pt-4 text-sm leading-6 text-muted-foreground">{item.details}</p>}
          </Card>
        ))}
      </div>
    </SectionFrame>
  );
}

export function CertificationsSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const certifications = limitBySection(data.certifications, section, 12);
  return (
    <SectionFrame section={section} eyebrow="Credentials" title="Verifiable certifications, without badge clutter." description="Credential links are shown when a public verification destination has been explicitly published." headerAside={section.cta_visible && <Button asChild variant="text" className="mt-5"><Link href="/achievements">All achievements <ArrowRight aria-hidden="true" /></Link></Button>}>
      <div className="overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-surface-raised">
        {certifications.map((item) => (
          <div key={item.id} className="grid min-h-28 grid-cols-[auto_1fr_auto] items-center gap-4 border-b border-border px-5 py-5 last:border-b-0 sm:px-6">
            <span className="grid size-10 place-items-center rounded-full bg-primary/12 text-accent-ink dark:text-primary"><Award className="size-4" aria-hidden="true" /></span>
            <div><h3 className="font-semibold leading-5">{item.name}</h3><p className="mt-1 text-xs leading-5 text-muted-foreground">{item.issuer}{item.issued_at ? ` · ${item.issued_at}` : ""}</p></div>
            {item.credential_url && <SafeExternalLink href={item.credential_url} aria-label={`Verify ${item.name}`} className="grid size-11 place-items-center rounded-full border border-border transition-colors hover:border-primary"><ExternalLink className="size-4" aria-hidden="true" /></SafeExternalLink>}
          </div>
        ))}
      </div>
    </SectionFrame>
  );
}
