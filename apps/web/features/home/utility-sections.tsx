import type { HomePage, HomepageSection } from "@portfolio/api-client";
import { Magnetic, Reveal } from "@portfolio/motion";
import { Badge, Button, Card } from "@portfolio/ui";
import { ArrowRight, Check, Clock3, Download, FileText, Mail, MessageCircle, Sparkles } from "lucide-react";
import Link from "next/link";
import { ExternalLink } from "@/components/external-link";
import { AskAiLauncher } from "@/components/ask-ai-launcher";
import { MediaImage } from "@/components/media-image";
import { SectionFrame, limitBySection } from "./section-frame";

function fileSize(bytes?: number): string | undefined {
  if (bytes === undefined) return undefined;
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ResumeSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const resume = data.profile.resume;
  if (!resume) return null;
  return (
    <SectionFrame section={section} contentClassName="py-[clamp(3.5rem,7vw,6rem)]">
      <Reveal className="grid gap-8 rounded-[var(--radius-card)] border border-border-strong bg-surface-raised p-6 shadow-[0_32px_90px_-62px_var(--shadow-ink)] sm:p-8 lg:grid-cols-[auto_1fr_auto] lg:items-center">
        <div className="grid size-16 place-items-center rounded-2xl bg-foreground text-background"><FileText className="size-7" aria-hidden="true" /></div>
        <div><div className="flex flex-wrap items-center gap-2"><Badge variant="verified"><Check aria-hidden="true" />Current version</Badge>{resume.version && <Badge variant="muted">v{resume.version}</Badge>}</div><h2 className="mt-4 font-display text-4xl leading-none tracking-[-0.05em]">{section.custom_heading ?? resume.label}</h2><p className="mt-3 text-sm leading-6 text-muted-foreground">Stable download route · Updated {new Date(resume.updated_at).toLocaleDateString("en", { dateStyle: "medium", timeZone: "UTC" })}{fileSize(resume.file_size_bytes) ? ` · ${fileSize(resume.file_size_bytes)}` : ""}</p></div>
        {section.cta_visible && <Magnetic><Button asChild variant="signal" size="lg"><a href="/resume" download><Download aria-hidden="true" />Download résumé</a></Button></Magnetic>}
      </Reveal>
    </SectionFrame>
  );
}

export function AvailabilitySection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const { availability } = data.profile;
  return (
    <SectionFrame section={section} contentClassName="py-[clamp(3.5rem,7vw,6rem)]">
      <div className="grid gap-6 border-y border-border-strong py-8 md:grid-cols-[auto_1fr_auto] md:items-center">
        <span className={`relative flex size-5 ${availability.status === "available" ? "text-success" : "text-primary"}`} aria-hidden="true"><span className="absolute inline-flex size-full animate-ping rounded-full bg-current opacity-25 motion-reduce:animate-none" /><span className="relative inline-flex size-5 rounded-full border-[6px] border-background bg-current shadow-[0_0_0_1px_current]" /></span>
        <div><p className="eyebrow">Availability signal</p><h2 className="mt-4 font-display text-4xl leading-none tracking-[-0.05em]">{section.custom_heading ?? availability.label}</h2>{availability.details && <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">{availability.details}</p>}</div>
        {section.cta_visible && <Button asChild variant="outline"><Link href="/contact">Discuss a fit <ArrowRight aria-hidden="true" /></Link></Button>}
      </div>
    </SectionFrame>
  );
}

export function AssistantCtaSection({ section }: { data: HomePage; section: HomepageSection }) {
  return (
    <SectionFrame section={section} className="bg-foreground text-background" contentClassName="py-[clamp(5rem,10vw,9rem)]">
      <Reveal className="relative isolate overflow-hidden rounded-[clamp(1.5rem,4vw,3rem)] border border-background/15 bg-ink p-7 sm:p-10 lg:p-14">
        <div className="absolute inset-0 coordinate-grid opacity-15" aria-hidden="true" />
        <div className="absolute -right-20 -top-20 size-80 rounded-full bg-primary/15 blur-3xl" aria-hidden="true" />
        <div className="relative z-10 grid gap-9 lg:grid-cols-[1fr_0.6fr] lg:items-end">
          <div><div className="grid size-12 place-items-center rounded-full border border-primary/45 bg-primary/10 text-primary"><Sparkles className="size-5" aria-hidden="true" /></div><p className="eyebrow mt-8 text-background/60">Portfolio-aware AI</p><h2 className="display-md mt-6 max-w-[12ch]">{section.custom_heading ?? "Ask for the thread connecting the work."}</h2></div>
          <div><p className="text-sm leading-6 text-background/65">Ask about published projects, experience, technologies, or collaboration fit. Answers cite public portfolio sources and show uncertainty rather than inventing facts.</p>{section.cta_visible && <AskAiLauncher className="mt-7" />}</div>
        </div>
      </Reveal>
    </SectionFrame>
  );
}

export function ContactCtaSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  return (
    <SectionFrame section={section}>
      <div className="grid gap-8 lg:grid-cols-[1fr_0.82fr] lg:items-stretch">
        <Reveal className="coordinate-grid flex min-h-[32rem] flex-col justify-between rounded-[var(--radius-card)] border border-border-strong bg-surface-raised p-7 sm:p-10">
          <div className="flex items-center justify-between gap-4"><Badge variant="signal"><MessageCircle aria-hidden="true" />Direct channel</Badge><Mail className="size-6 text-muted-foreground" aria-hidden="true" /></div>
          <div><p className="eyebrow">Contact</p><h2 className="display-md mt-7 max-w-[11ch]">{section.custom_heading ?? "Bring a useful problem."}</h2><p className="mt-6 max-w-xl text-base leading-7 text-muted-foreground">Share the context, constraints, and outcome you are aiming for. The contact workflow stores valid inquiries before attempting delivery.</p>{section.cta_visible && <Magnetic className="mt-8 inline-block"><Button asChild variant="signal" size="lg"><Link href="/contact">Start a conversation <ArrowRight aria-hidden="true" /></Link></Button></Magnetic>}</div>
        </Reveal>
        <div className="grid gap-4">
          <Card variant="contrast" className="flex min-h-40 flex-col justify-between p-6 sm:p-8"><Clock3 className="size-5 text-primary dark:text-background" aria-hidden="true" /><div><p className="text-xs uppercase tracking-[0.14em] text-background/70">Current status</p><p className="mt-3 font-display text-3xl leading-none tracking-[-0.045em]">{data.profile.availability.label}</p></div></Card>
          <Card variant="raised" className="flex min-h-40 flex-col justify-between p-6 sm:p-8"><FileText className="size-5 text-primary" aria-hidden="true" /><div><p className="text-xs uppercase tracking-[0.14em] text-muted-foreground">Prefer context first?</p>{section.cta_visible && <Button asChild variant="text" className="mt-3"><Link href="/projects">Browse the case studies <ArrowRight aria-hidden="true" /></Link></Button>}</div></Card>
        </div>
      </div>
    </SectionFrame>
  );
}

export function SocialLinksSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const socials = limitBySection(data.profile.socials, section);
  if (socials.length === 0) return null;
  return (
    <SectionFrame section={section} contentClassName="py-8">
      <div className="overflow-hidden" aria-label="Social links">
        <div className="flex w-max animate-signal-marquee items-center gap-4 motion-reduce:w-full motion-reduce:flex-wrap motion-reduce:animate-none">
          {[...socials, ...socials].map((social, index) => (
            <ExternalLink key={`${social.id}-${index}`} href={social.url} aria-hidden={index >= socials.length ? true : undefined} tabIndex={index >= socials.length ? -1 : undefined} className="group min-h-11 rounded-full border border-border-strong bg-surface-raised px-5 py-3 text-sm font-semibold transition-colors hover:border-primary hover:bg-primary/8">{social.label}</ExternalLink>
          ))}
        </div>
      </div>
    </SectionFrame>
  );
}

export function EditorialSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const items = limitBySection(data.editorial_blocks, section);
  if (items.length === 0) return null;
  return (
    <SectionFrame section={section}>
      <div className="grid gap-6">
        {items.map((item, index) => (
          <Reveal id={item.id} key={item.id} className={`grid scroll-mt-28 overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-surface-raised ${item.media ? "lg:grid-cols-2" : ""}`}>
            <div className={`flex min-h-96 flex-col justify-between p-7 sm:p-10 ${item.media && index % 2 === 1 ? "lg:order-2" : ""}`}><div>{item.eyebrow && <p className="eyebrow">{item.eyebrow}</p>}<h2 className={`display-md mt-7 ${item.media ? "max-w-[12ch]" : "max-w-[18ch]"}`}>{section.custom_heading ?? item.title}</h2></div><div><p className={`${item.media ? "max-w-xl" : "max-w-4xl"} whitespace-pre-line text-base leading-7 text-muted-foreground`}>{item.body}</p>{section.cta_visible && item.link && (item.link.external ? <Button asChild variant="text" className="mt-7"><ExternalLink href={item.link.url}>{item.link.label}</ExternalLink></Button> : <Button asChild variant="text" className="mt-7"><Link href={item.link.url}>{item.link.label}<ArrowRight aria-hidden="true" /></Link></Button>)}</div></div>
            {item.media && <MediaImage asset={item.media} className={`min-h-96 ${index % 2 === 1 ? "lg:order-1" : ""}`} fallbackLabel="Managed editorial media" />}
          </Reveal>
        ))}
      </div>
    </SectionFrame>
  );
}
