"use client";

import type { NavigationItem } from "@portfolio/api-client";
import { Button, Dialog, DialogClose, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@portfolio/ui";
import { ArrowUpRight, ChevronRight, Menu } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeSwitcher } from "./theme-switcher";

type SiteHeaderProps = {
  brandName: string;
  brandMark?: string | undefined;
  navigation: NavigationItem[];
  contactEnabled: boolean;
};

function NavLink({ chapter, external, href, label }: Pick<NavigationItem, "external" | "href" | "label"> & { chapter: number }) {
  const pathname = usePathname();
  const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
  return (
    <Link
      href={href}
      prefetch={false}
      target={external ? "_blank" : undefined}
      rel={external ? "noreferrer" : undefined}
      className="group relative inline-flex min-h-11 items-center gap-2 px-2 text-sm font-semibold text-muted-foreground transition-colors hover:text-foreground focus-visible:rounded-lg"
      aria-current={active ? "page" : undefined}
    >
      <span className="font-mono text-[0.54rem] tracking-[0.08em] text-muted-foreground" aria-hidden="true">{String(chapter).padStart(2, "0")}</span>
      {label}
      {external && <ArrowUpRight className="size-3" aria-hidden="true" />}
      <span className={`absolute inset-x-2 bottom-1 h-px origin-left bg-primary transition-transform ${active ? "scale-x-100" : "scale-x-0 group-hover:scale-x-100"}`} />
    </Link>
  );
}

export function SiteHeader({ brandMark, brandName, contactEnabled, navigation }: SiteHeaderProps) {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-border/75 bg-background/82 backdrop-blur-xl supports-[backdrop-filter]:bg-background/68">
      <div className="site-shell grid min-h-18 grid-cols-[1fr_auto] items-center gap-4 lg:grid-cols-[1fr_auto_1fr]">
        <Link href="/" prefetch={false} aria-label={`${brandName} home`} className="group inline-flex min-h-11 items-center gap-3 rounded-xl pr-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <span className="grid size-9 place-items-center rounded-full bg-foreground font-mono text-[0.7rem] font-bold tracking-[-0.08em] text-background transition-transform group-hover:rotate-[-8deg] motion-reduce:transition-none">{brandMark ?? brandName.split(/\s+/).map((part) => part[0]).slice(0, 2).join("")}</span>
          <span className="hidden sm:block"><strong className="block text-sm tracking-[-0.02em]">{brandName}</strong><span className="block font-mono text-[0.52rem] uppercase tracking-[0.14em] text-muted-foreground">AI · Data · Delivery</span></span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary navigation">
          {navigation.map((item, index) => <NavLink key={item.id} {...item} chapter={index + 1} />)}
        </nav>

        <div className="flex items-center justify-end gap-1.5">
          <ThemeSwitcher />
          {contactEnabled && (
            <Button asChild variant="signal" size="sm" className="hidden sm:inline-flex">
              <Link href="/contact" prefetch={false}>Discuss a project</Link>
            </Button>
          )}
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
                <Menu aria-hidden="true" />
              </Button>
            </DialogTrigger>
            <DialogContent className="inset-x-3 bottom-3 top-auto max-h-[calc(100dvh-1.5rem)] w-auto max-w-none translate-x-0 translate-y-0 rounded-[2rem] sm:left-auto sm:right-4 sm:w-[28rem]">
              <DialogHeader>
                <DialogTitle>Navigate</DialogTitle>
                <DialogDescription>Explore Yazeed&apos;s profile, achievements, work, projects, and sponsorship paths.</DialogDescription>
              </DialogHeader>
              <nav className="grid border-t border-border" aria-label="Mobile navigation">
                {navigation.map((item, index) => {
                  const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                  return (
                  <DialogClose asChild key={item.id}>
                    <Link href={item.href} prefetch={false} target={item.external ? "_blank" : undefined} rel={item.external ? "noreferrer" : undefined} aria-current={active ? "page" : undefined} className={`group flex min-h-14 items-center justify-between border-b border-border py-3 text-xl font-semibold tracking-[-0.03em] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring ${active ? "text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                      <span><span className="mr-4 font-mono text-[0.65rem] tracking-[0.15em] text-muted-foreground">{String(index + 1).padStart(2, "0")}</span>{item.label}</span>
                      {item.external ? <ArrowUpRight className="size-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden="true" /> : <ChevronRight className={`size-4 transition-transform group-hover:translate-x-0.5 ${active ? "text-primary" : ""}`} aria-hidden="true" />}
                    </Link>
                  </DialogClose>
                );})}
              </nav>
              {contactEnabled && <DialogClose asChild><Button asChild variant="signal" size="lg"><Link href="/contact" prefetch={false}>Discuss a project</Link></Button></DialogClose>}
            </DialogContent>
          </Dialog>
        </div>
      </div>
    </header>
  );
}
