import type { HomePage, HomepageSection } from "@portfolio/api-client";
import { Magnetic, Reveal, Stagger, StaggerItem } from "@portfolio/motion";
import { Badge, Button } from "@portfolio/ui";
import { cn } from "@portfolio/ui";
import { ArrowDownRight, ArrowRight, Download, MapPin } from "lucide-react";
import { AmbientField } from "@/components/ambient-field";
import { MediaImage } from "@/components/media-image";
import { ProfileCtaLink } from "@/components/profile-cta-link";

const themeClasses: Record<HomepageSection["theme"], string> = {
  default: "bg-background text-foreground",
  muted: "bg-muted/55 text-foreground",
  contrast: "bg-foreground text-background",
  accent: "bg-primary/12 text-foreground",
};

export function HeroSection({ data, section }: { data: HomePage; section: HomepageSection }) {
  const { profile } = data;
  return (
    <section id="hero" data-section-kind="hero" data-variant={section.variant} data-motion={section.animation_variant} className={cn("relative isolate min-h-[calc(100svh-4.5rem)] overflow-hidden", themeClasses[section.theme])}>
      <div className="absolute inset-0 -z-20 coordinate-grid opacity-65" aria-hidden="true" />
      <div className="absolute -right-[18rem] top-[-16rem] -z-10 size-[50rem] rounded-full bg-primary/12 blur-3xl" aria-hidden="true" />
      <div className="site-shell grid min-h-[calc(100svh-4.5rem)] items-center gap-10 py-12 lg:grid-cols-[minmax(0,1.1fr)_minmax(23rem,0.68fr)] lg:py-16">
        <div className="relative z-10 flex flex-col justify-center py-6">
          <Reveal>
            <div className="flex flex-wrap items-center gap-3">
              <Badge variant={profile.availability.status === "available" ? "verified" : "signal"}>
                <span className="size-1.5 rounded-full bg-current" aria-hidden="true" />{profile.availability.label}
              </Badge>
              {profile.public_location && <span className="inline-flex items-center gap-1.5 font-mono text-[0.68rem] uppercase tracking-[0.12em] text-muted-foreground"><MapPin className="size-3" aria-hidden="true" />{profile.public_location}</span>}
            </div>
          </Reveal>

          <Stagger className="mt-7">
            <StaggerItem><p className="mb-3 font-mono text-[0.7rem] font-semibold uppercase tracking-[0.19em] text-muted-foreground">{profile.eyebrow ?? "Builder / Engineer / Product thinker"}</p></StaggerItem>
            <StaggerItem><h1 className="display-xl max-w-[9.5ch]">{section.custom_heading ?? profile.name}</h1></StaggerItem>
            <StaggerItem><p className="mt-6 max-w-[25ch] font-display text-[clamp(1.45rem,3vw,2.55rem)] leading-[1.02] tracking-[-0.04em] text-muted-foreground">{profile.headline}</p></StaggerItem>
          </Stagger>

          <Reveal delay={0.24}>
            <p className="mt-7 max-w-xl text-base leading-7 text-muted-foreground md:text-lg md:leading-8">{profile.short_bio}</p>
            {section.cta_visible && <div className="mt-8 flex flex-wrap items-center gap-3">
              <Magnetic><Button asChild variant="signal" size="lg"><ProfileCtaLink url={profile.primary_cta?.url ?? "/projects"}>{profile.primary_cta?.label ?? "Explore selected work"} <ArrowRight aria-hidden="true" /></ProfileCtaLink></Button></Magnetic>
              {profile.secondary_cta ? <Button asChild variant="outline" size="lg"><ProfileCtaLink url={profile.secondary_cta.url}>{profile.secondary_cta.label}</ProfileCtaLink></Button> : profile.resume && <Button asChild variant="outline" size="lg"><a href="/resume" download><Download aria-hidden="true" />Résumé</a></Button>}
            </div>}
          </Reveal>
        </div>

        <Reveal className="relative mx-auto w-full max-w-[36rem] lg:mx-0 lg:ml-auto" delay={0.12} distance={32}>
          <div className="absolute -inset-16 -z-10 opacity-75" aria-hidden="true"><AmbientField className="size-full" density={32} /></div>
          <div className="relative aspect-[4/5] overflow-hidden rounded-[clamp(1.5rem,4vw,3.5rem)] border border-border-strong bg-muted shadow-[0_50px_140px_-65px_var(--shadow-ink)]">
            <MediaImage asset={profile.portrait} eager className="size-full" imageClassName="grayscale-[0.12] contrast-[1.03]" fallbackLabel="Managed personal portrait" sizes="(max-width: 1024px) 90vw, 38vw" />
            <div className="absolute inset-x-0 bottom-0 z-20 bg-gradient-to-t from-ink/85 via-ink/20 to-transparent p-6 pt-28 text-white sm:p-8">
              <div className="flex items-end justify-between gap-5">
                <div><p className="font-mono text-[0.62rem] uppercase tracking-[0.16em] text-white/60">Current signal</p><p className="mt-2 max-w-xs text-sm font-medium leading-6 text-white/90">{profile.availability.details ?? profile.availability.label}</p></div>
                <ArrowDownRight className="size-7 text-primary" aria-hidden="true" />
              </div>
            </div>
            <div className="absolute right-4 top-4 z-20 rounded-full border border-white/20 bg-ink/40 px-3 py-1.5 font-mono text-[0.58rem] uppercase tracking-[0.14em] text-white/75 backdrop-blur-md">Portrait / Identity</div>
          </div>
        </Reveal>
      </div>
      <a href="#selected-work" className="absolute bottom-4 left-1/2 z-20 hidden min-h-11 -translate-x-1/2 items-center gap-2 rounded-full px-3 font-mono text-[0.62rem] uppercase tracking-[0.15em] text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:inline-flex">Scroll to the work <ArrowDownRight className="size-3.5" aria-hidden="true" /></a>
    </section>
  );
}
