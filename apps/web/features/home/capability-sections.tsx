import type { HomePage, HomepageSection } from "@portfolio/api-client";
import { Reveal, Stagger, StaggerItem } from "@portfolio/motion";
import { Badge, Button, Card } from "@portfolio/ui";
import { ArrowRight, Blocks, Compass, CornerDownRight } from "lucide-react";
import Link from "next/link";
import { SectionFrame, limitBySection } from "./section-frame";
import { TechnologyUniverse } from "./technology-universe";

export function CategoriesSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const items = limitBySection(data.categories, section);
  const gridColumns = items.length === 1 ? "max-w-2xl" : items.length === 2 ? "md:grid-cols-2" : "md:grid-cols-2 lg:grid-cols-3";
  return (
    <SectionFrame section={section} eyebrow="What I build" title="From intelligent systems to the infrastructure beneath them." description="Configurable capability areas connect disciplines to real work, rather than presenting skills in isolation.">
      <Stagger className={`grid gap-px overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-border-strong ${gridColumns}`}>
        {items.map((category, index) => (
          <StaggerItem key={category.id} className="h-full">
            <Link href={`/projects?category=${encodeURIComponent(category.slug)}`} className="group flex h-full min-h-80 flex-col justify-between bg-background p-6 transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring sm:p-8">
              <div className="flex items-start justify-between gap-4"><span className="font-display text-5xl tracking-[-0.07em] text-accent-ink dark:text-primary">0{index + 1}</span><Blocks className="size-5 text-muted-foreground transition-transform group-hover:rotate-6 group-hover:text-foreground motion-reduce:transition-none" aria-hidden="true" /></div>
              <div><h3 className="font-display text-4xl leading-[0.93] tracking-[-0.05em]">{category.name}</h3><p className="mt-4 text-sm leading-6 text-muted-foreground">{category.description}</p>{category.statement && <p className="mt-5 border-l-2 border-primary pl-4 text-sm font-semibold leading-6">{category.statement}</p>}<span className="mt-7 inline-flex items-center gap-2 text-sm font-semibold">See related work <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" aria-hidden="true" /></span></div>
            </Link>
          </StaggerItem>
        ))}
      </Stagger>
    </SectionFrame>
  );
}

export function SectorsSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const items = limitBySection(data.sectors, section);
  const lead = items[0];
  const secondary = items.slice(1);
  return (
    <SectionFrame section={section} eyebrow="Applied domains" title="Context changes the engineering." description="Sector experience is shown through connected projects and outcomes, with no inferred claims beyond published evidence.">
      {items.length > 0 && (
        <div className={`grid gap-6 ${secondary.length > 0 ? "lg:grid-cols-[1.1fr_0.9fr]" : "max-w-5xl"}`}>
          <Reveal className="relative isolate min-h-[36rem] overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-foreground p-7 text-background sm:p-10">
            <div className="absolute inset-0 coordinate-grid opacity-20" aria-hidden="true" />
            <div className="absolute left-1/2 top-1/2 size-[28rem] -translate-x-1/2 -translate-y-1/2 rounded-full border border-primary/35" aria-hidden="true"><div className="absolute inset-[18%] rounded-full border border-primary/25" /><div className="absolute inset-[38%] rounded-full border border-primary/20 bg-primary/10" /></div>
            <div className="relative z-10 flex min-h-[31rem] flex-col justify-between">
              <div className="flex items-center justify-between gap-4"><Badge variant="outline" className="text-background/75">Domain radar</Badge><Compass className="size-5 text-primary" aria-hidden="true" /></div>
              {lead && <div className="max-w-lg"><p className="font-mono text-[0.65rem] uppercase tracking-[0.15em] text-background/70">Lead published domain</p><h3 className="mt-4 font-display text-[clamp(3.4rem,7vw,6rem)] leading-[0.83] tracking-[-0.06em]">{lead.name}</h3><p className="mt-5 text-sm leading-6 text-background/65">{lead.evidence_summary ?? lead.description}</p><p className="mt-4 text-xs font-semibold text-background/70">{lead.project_count} published {lead.project_count === 1 ? "project" : "projects"}</p><Button asChild variant="signal" className="mt-7"><Link href={`/sectors/${lead.slug}`} aria-label={`${lead.name} ${lead.project_count} published ${lead.project_count === 1 ? "project" : "projects"}`}>Explore evidence <ArrowRight aria-hidden="true" /></Link></Button></div>}
            </div>
          </Reveal>
          {secondary.length > 0 && <div className="grid content-start gap-3">
            {secondary.map((sector, index) => (
              <Reveal key={sector.id} delay={index * 0.05}>
                <Link href={`/sectors/${sector.slug}`} className="group grid min-h-28 grid-cols-[auto_1fr_auto] items-center gap-5 rounded-[var(--radius-card)] border border-border bg-surface-raised px-5 py-5 transition-[transform,border-color,background-color] hover:-translate-y-0.5 hover:border-primary hover:bg-primary/8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none sm:px-6">
                  <span className="font-display text-3xl tracking-[-0.06em] text-muted-foreground">{String(index + 2).padStart(2, "0")}</span><span><strong className="block text-lg tracking-[-0.02em]">{sector.name}</strong><span className="mt-1 block text-xs leading-5 text-muted-foreground">{sector.project_count} published {sector.project_count === 1 ? "project" : "projects"}</span></span><CornerDownRight className="size-4 transition-transform group-hover:translate-x-1 group-hover:translate-y-1" aria-hidden="true" />
                </Link>
              </Reveal>
            ))}
          </div>}
        </div>
      )}
    </SectionFrame>
  );
}

export function TechnologyUniverseSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const skills = limitBySection(data.skills, section, 36);
  return (
    <SectionFrame section={section} eyebrow="Technology universe" title="Tools arranged by the work they enable." description="The canvas is an enhancement. Every technology remains keyboard-accessible, readable, and connected to public project evidence.">
      {skills.length > 0 ? <TechnologyUniverse skills={skills} /> : <Card className="p-10 text-center text-sm text-muted-foreground">No technologies are currently published.</Card>}
    </SectionFrame>
  );
}
