"use client";

import type { MediaAsset } from "@portfolio/api-client";
import { Button, Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@portfolio/ui";
import { ChevronRight, Menu } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";
import { safeMediaUrl } from "./media-image";
import { ThemeSwitcher } from "./theme-switcher";

type SiteHeaderProps = {
  brandName: string;
  brandLogo?: MediaAsset | undefined;
};

const navigation = [
  { id: "work", label: "Work", href: "/work" },
  { id: "projects", label: "Projects", href: "/projects" },
  { id: "achievements", label: "Achievements", href: "/achievements" },
  { id: "sponsor", label: "Sponsor", href: "/sponsor" },
] as const;

function nameInitials(name: string): { main: string; mini: string } {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0]?.[0] ?? "Y";
  const last = parts.length > 1 ? parts.at(-1)?.[0] : "";
  return { main: `${first}${last}`.toUpperCase(), mini: first.toUpperCase() };
}

function BrandMark({ asset, name }: { asset?: MediaAsset | undefined; name: string }) {
  const [failedSrc, setFailedSrc] = React.useState<string>();
  const src = asset ? safeMediaUrl(asset.url) : undefined;
  const showImage = Boolean(src && src !== failedSrc);
  const initials = nameInitials(name);

  return (
    <span className="relative grid size-10 shrink-0 place-items-center overflow-hidden rounded-full border border-border-strong bg-foreground font-mono text-[0.7rem] font-bold tracking-[-0.08em] text-background shadow-[0_10px_24px_-18px_var(--shadow-ink)] transition-transform group-hover:rotate-[-4deg] motion-reduce:transition-none">
      {showImage ? (
        <Image
          src={src!}
          alt={asset?.alt || `Portrait of ${name}`}
          fill
          sizes="40px"
          unoptimized={!src!.startsWith("/")}
          className="object-cover"
          onError={() => setFailedSrc(src)}
        />
      ) : (
        <span aria-hidden="true">
          <span data-testid="brand-initial-mini" className="sm:hidden">{initials.mini}</span>
          <span data-testid="brand-initial-main" className="hidden sm:inline">{initials.main}</span>
        </span>
      )}
    </span>
  );
}

function NavLink({ href, label }: { href: string; label: string }) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(`${href}/`);
  return (
    <Link
      href={href}
      prefetch={false}
      className="group relative inline-flex min-h-11 items-center px-3 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground focus-visible:rounded-lg"
      aria-current={active ? "page" : undefined}
    >
      {label}
      <span className={`absolute inset-x-3 bottom-1 h-px origin-left bg-primary transition-transform ${active ? "scale-x-100" : "scale-x-0 group-hover:scale-x-100"}`} />
    </Link>
  );
}

export function SiteHeader({ brandLogo, brandName }: SiteHeaderProps) {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-border/75 bg-background/88 backdrop-blur-xl supports-[backdrop-filter]:bg-background/72">
      <div className="site-shell grid min-h-18 grid-cols-[1fr_auto] items-center gap-3 lg:grid-cols-[1fr_auto_1fr]">
        <Link href="/" prefetch={false} aria-label={`${brandName} home`} className="group inline-flex min-h-11 w-fit items-center gap-3 rounded-xl pr-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <BrandMark asset={brandLogo} name={brandName} />
          <span className="hidden sm:block"><strong className="block text-sm tracking-[-0.02em]">{brandName}</strong><span className="block font-mono text-[0.52rem] uppercase tracking-[0.14em] text-muted-foreground">AI · Data · Delivery</span></span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary navigation">
          {navigation.map((item) => <NavLink key={item.id} {...item} />)}
        </nav>

        <div className="flex items-center justify-end gap-2">
          <ThemeSwitcher />
          <Button asChild variant="signal" size="sm" className="hidden sm:inline-flex">
            <Link href="/contact" prefetch={false}>Contact Me</Link>
          </Button>
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
                <Menu aria-hidden="true" />
              </Button>
            </DialogTrigger>
            <DialogContent className="inset-x-3 bottom-3 top-auto max-h-[calc(100dvh-1.5rem)] w-auto max-w-none translate-x-0 translate-y-0 rounded-[2rem] sm:left-auto sm:right-4 sm:w-[28rem]">
              <DialogHeader>
                <DialogTitle>Navigate</DialogTitle>
                <DialogDescription>Explore Yazeed&apos;s work, projects, achievements, and public sponsorship path.</DialogDescription>
              </DialogHeader>
              <nav className="grid border-t border-border" aria-label="Mobile navigation">
                {navigation.map((item) => {
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  return (
                    <DialogClose asChild key={item.id}>
                      <Link href={item.href} prefetch={false} aria-current={active ? "page" : undefined} className={`group flex min-h-14 items-center justify-between border-b border-border py-3 text-xl font-semibold tracking-[-0.03em] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring ${active ? "text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                        {item.label}
                        <ChevronRight className={`size-4 transition-transform group-hover:translate-x-0.5 ${active ? "text-primary" : ""}`} aria-hidden="true" />
                      </Link>
                    </DialogClose>
                  );
                })}
              </nav>
              <DialogClose asChild><Button asChild variant="signal" size="lg"><Link href="/contact" prefetch={false}>Contact Me</Link></Button></DialogClose>
            </DialogContent>
          </Dialog>
        </div>
      </div>
    </header>
  );
}
