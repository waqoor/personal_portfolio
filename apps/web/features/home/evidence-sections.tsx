import type { HomePage, HomepageSection, Metric } from "@portfolio/api-client";
import { Counter, Reveal, Stagger, StaggerItem } from "@portfolio/motion";
import { Badge } from "@portfolio/ui";
import { ArrowUpRight, CheckCircle2, Quote, ShieldCheck } from "lucide-react";
import { ExternalLink } from "@/components/external-link";
import { MediaImage } from "@/components/media-image";
import { SectionFrame, limitBySection } from "./section-frame";

function MetricValue({ metric }: { metric: Metric }) {
  const numeric = /^-?\d+(?:\.\d+)?$/.test(metric.value) ? Number(metric.value) : undefined;
  const decimals = metric.value.includes(".") ? metric.value.split(".")[1]?.length ?? 0 : 0;
  if (numeric === undefined) return <>{metric.value}{metric.unit}</>;
  return <><Counter value={numeric} decimals={decimals} />{metric.unit}</>;
}

export function MetricsSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const metrics = limitBySection(data.metrics.filter((metric) => metric.verified), section);
  const gridColumns = metrics.length === 1
    ? "max-w-xl"
    : metrics.length === 2
      ? "sm:grid-cols-2"
      : metrics.length === 3
        ? "sm:grid-cols-2 lg:grid-cols-3"
        : "sm:grid-cols-2 lg:grid-cols-4";
  return (
    <SectionFrame section={section} eyebrow="Verified impact" title="Outcomes, with the receipts kept nearby." description="Only approved metrics reach this surface. Each number includes context and, when publishable, an evidence path.">
      <Stagger className={`grid gap-px overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-border-strong ${gridColumns}`}>
        {metrics.map((metric) => (
          <StaggerItem key={metric.id} className="h-full bg-background p-6 sm:p-8">
            <div className="flex min-h-60 flex-col justify-between gap-8">
              <div className="flex items-start justify-between gap-3"><Badge variant="verified"><CheckCircle2 aria-hidden="true" />Verified</Badge>{metric.evidence_url && <ExternalLink href={metric.evidence_url} aria-label={`Open evidence for ${metric.label}`} className="grid size-11 place-items-center rounded-full border border-border text-muted-foreground transition-colors hover:border-primary hover:text-foreground"><ArrowUpRight className="size-4" aria-hidden="true" /></ExternalLink>}</div>
              <div><p className="font-display text-[clamp(3.3rem,6vw,6rem)] leading-[0.76] tracking-[-0.07em]"><MetricValue metric={metric} /></p><p className="mt-5 font-semibold">{metric.label}</p><p className="mt-2 text-xs leading-5 text-muted-foreground">{metric.context}</p>{metric.evidence_label && <p className="mt-3 font-mono text-[0.58rem] uppercase tracking-[0.12em] text-muted-foreground">Source: {metric.evidence_label}</p>}</div>
            </div>
          </StaggerItem>
        ))}
      </Stagger>
    </SectionFrame>
  );
}

export function TestimonialsSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const testimonials = limitBySection(data.testimonials.filter((item) => item.verified), section);
  const singleTestimonial = testimonials.length === 1;
  return (
    <SectionFrame section={section} eyebrow="Approved perspective" title="What collaborators chose to put on record." description="Every quote is explicitly approved and attributed. Anonymous or unverifiable praise does not appear here.">
      <div className={`grid gap-5 ${singleTestimonial ? "max-w-4xl" : "lg:grid-cols-12"}`}>
        {testimonials.map((testimonial, index) => (
          <Reveal key={testimonial.id} delay={index * 0.06} className={singleTestimonial ? undefined : index % 3 === 0 ? "lg:col-span-7" : "lg:col-span-5"}>
            <figure className="flex h-full min-h-80 flex-col justify-between rounded-[var(--radius-card)] border border-border-strong bg-surface-raised p-6 sm:p-8">
              <div><div className="flex items-center justify-between gap-3"><Quote className="size-9 text-primary" aria-hidden="true" /><Badge variant="verified"><ShieldCheck aria-hidden="true" />Approved</Badge></div><blockquote className="mt-8 font-display text-[clamp(1.8rem,3vw,3.25rem)] leading-[1.02] tracking-[-0.042em]">“{testimonial.quote}”</blockquote></div>
              <figcaption className="mt-10 flex items-center gap-4 border-t border-border pt-5">
                <MediaImage asset={testimonial.portrait} className="size-12 shrink-0 rounded-full" imageClassName="rounded-full" fallbackLabel="Portrait" />
                <div><p className="text-sm font-bold">{testimonial.attribution_name}</p><p className="mt-1 text-xs text-muted-foreground">{[testimonial.attribution_role, testimonial.attribution_organization].filter(Boolean).join(" · ")}</p>{testimonial.source_url && <ExternalLink href={testimonial.source_url} className="mt-2 text-xs font-semibold text-accent-ink dark:text-primary">{testimonial.source_label ?? "Source"}</ExternalLink>}</div>
              </figcaption>
            </figure>
          </Reveal>
        ))}
      </div>
      {testimonials.length === 0 && <p className="rounded-[var(--radius-card)] border border-dashed border-border-strong p-10 text-center text-sm text-muted-foreground">No approved testimonials are currently published.</p>}
    </SectionFrame>
  );
}
