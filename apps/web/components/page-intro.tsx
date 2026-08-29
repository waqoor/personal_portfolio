import type { ReactNode } from "react";

export function PageIntro({ actions, description, eyebrow, title }: { actions?: ReactNode; description: string; eyebrow: string; title: string }) {
  return (
    <header className="coordinate-grid border-b border-border">
      <div className="site-shell section-space pb-[clamp(4rem,8vw,7rem)]">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="display-lg mt-8 max-w-[12ch]">{title}</h1>
        <div className="mt-8 grid gap-7 border-t border-border pt-6 md:grid-cols-[1fr_auto] md:items-end">
          <p className="max-w-2xl text-base leading-7 text-muted-foreground md:text-lg md:leading-8">{description}</p>
          {actions}
        </div>
      </div>
    </header>
  );
}
