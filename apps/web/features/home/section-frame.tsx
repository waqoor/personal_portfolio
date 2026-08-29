import type { HomepageSection } from "@portfolio/api-client";
import { cn } from "@portfolio/ui";
import type { ReactNode } from "react";

const themeClasses: Record<HomepageSection["theme"], string> = {
  default: "bg-background text-foreground",
  muted: "bg-muted/55 text-foreground",
  contrast: "bg-foreground text-background",
  accent: "bg-primary/12 text-foreground",
};

type SectionFrameProps = {
  section: HomepageSection;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  eyebrow?: string;
  title?: string;
  description?: string;
  headerAside?: ReactNode;
};

export function SectionFrame({ children, className, contentClassName, description, eyebrow, headerAside, section, title }: SectionFrameProps) {
  const heading = section.custom_heading ?? title;
  return (
    <section
      id={section.kind.replaceAll("_", "-")}
      data-section-kind={section.kind}
      data-variant={section.variant}
      data-motion={section.animation_variant}
      className={cn("relative overflow-hidden border-t border-border", themeClasses[section.theme], className)}
    >
      <div className={cn("site-shell section-space", contentClassName)}>
        {(eyebrow || heading || description) && (
          <header className="mb-12 grid gap-7 border-b border-current/15 pb-7 md:mb-16 md:grid-cols-[minmax(0,1fr)_minmax(16rem,0.55fr)] md:items-end">
            <div>
              {eyebrow && <p className="eyebrow opacity-75">{eyebrow}</p>}
              {heading && <h2 className="display-md mt-6 max-w-[13ch]">{heading}</h2>}
            </div>
            <div>
              {description && <p className="max-w-xl text-sm leading-6 opacity-70 md:text-base md:leading-7">{description}</p>}
              {headerAside}
            </div>
          </header>
        )}
        {children}
      </div>
    </section>
  );
}

export function limitBySection<T>(items: readonly T[], section: HomepageSection, fallback?: number): T[] {
  const limit = section.data_limit ?? fallback ?? items.length;
  return items.slice(0, Math.max(0, limit));
}
