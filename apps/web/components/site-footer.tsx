import type { NavigationItem, SiteSettings, SocialLink } from "@portfolio/api-client";
import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import { ExternalLink } from "@/components/external-link";

export function SiteFooter({
  brandName,
  contactEnabled,
  navigation,
  presentation,
  publicEmail,
  socials,
}: {
  brandName: string;
  contactEnabled: boolean;
  navigation: NavigationItem[];
  presentation: SiteSettings;
  publicEmail?: string | undefined;
  socials: SocialLink[];
}) {
  return (
    <footer className="relative overflow-hidden border-t border-border bg-foreground text-background">
      <div className="site-shell section-space pb-8">
        <div className="grid gap-10 lg:grid-cols-[1.35fr_0.65fr] lg:items-end">
          <div>
            <p className="eyebrow text-background/65">{presentation.footer_eyebrow}</p>
            <p className="mt-7 max-w-5xl whitespace-pre-line font-display text-[clamp(3.2rem,9vw,9rem)] leading-[0.78] tracking-[-0.07em]">{presentation.footer_heading}</p>
          </div>
          <div className="grid gap-2 border-t border-background/20 pt-5">
            {socials.map((social) => (
              <a key={social.id} href={social.url} target="_blank" rel="noreferrer" className="group flex min-h-11 items-center justify-between border-b border-background/15 py-3 text-sm font-semibold text-background/75 transition-colors hover:text-primary dark:hover:text-background">
                {social.label}<ArrowUpRight className="size-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden="true" />
              </a>
            ))}
            {navigation.map((item) => item.external ? (
              <ExternalLink key={item.id} href={item.href} className="group flex min-h-11 items-center justify-between border-b border-background/15 py-3 text-sm font-semibold text-background/75 transition-colors hover:text-primary dark:hover:text-background">{item.label}<ArrowUpRight className="size-4" aria-hidden="true" /></ExternalLink>
            ) : (
              <Link key={item.id} href={item.href} prefetch={false} className="group flex min-h-11 items-center justify-between border-b border-background/15 py-3 text-sm font-semibold text-background/75 transition-colors hover:text-primary dark:hover:text-background">{item.label}<ArrowUpRight className="size-4" aria-hidden="true" /></Link>
            ))}
            {contactEnabled && !navigation.some((item) => item.href === "/contact") && <Link href="/contact" prefetch={false} className="mt-3 inline-flex min-h-11 items-center text-sm font-semibold text-primary hover:underline dark:text-background">Contact <ArrowUpRight className="ml-2 size-4" aria-hidden="true" /></Link>}
            {!contactEnabled && publicEmail && <a href={`mailto:${publicEmail}`} className="mt-3 inline-flex min-h-11 items-center text-sm font-semibold text-primary hover:underline dark:text-background">Email <ArrowUpRight className="ml-2 size-4" aria-hidden="true" /></a>}
          </div>
        </div>
        <div className="mt-20 flex flex-col gap-3 border-t border-background/15 pt-6 font-mono text-[0.65rem] uppercase tracking-[0.14em] text-background/70 sm:flex-row sm:items-center sm:justify-between">
          <span>© {new Date().getFullYear()} {brandName}</span>
          <span>{presentation.footer_statement}</span>
        </div>
      </div>
    </footer>
  );
}
