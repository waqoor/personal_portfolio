"use client";

import type { AdminResource, AdminSession } from "@portfolio/api-client";
import { ADMIN_RESOURCE_GROUPS } from "@portfolio/config";
import {
  Button,
  cn,
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@portfolio/ui";
import {
  ArrowUpRight,
  ChevronRight,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings2,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import * as React from "react";
import { getBrowserApi } from "@/lib/browser-api";
import { ADMIN_RESOURCE_LABELS } from "./resource-definitions";

type User = NonNullable<AdminSession["user"]>;

const OWNER_ONLY_RESOURCES = new Set<AdminResource>([
  "assistant-settings",
  "feature-settings",
  "homepage-sections",
  "navigation",
  "profile",
  "resumes",
  "site-settings",
  "sponsorship",
]);

function AdminNavigation({
  closeOnSelect = false,
  role,
}: {
  closeOnSelect?: boolean;
  role: User["role"];
}) {
  const pathname = usePathname();
  const item = (href: string, label: string, icon?: React.ReactNode) => {
    const active = href === "/admin" ? pathname === href : pathname.startsWith(href);
    const content = (
      <Link
        href={href}
        className={cn(
          "group flex min-h-11 items-center gap-3 rounded-xl px-3 py-2 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          active
            ? "bg-primary text-primary-foreground"
            : "text-muted-foreground hover:bg-foreground/[0.055] hover:text-foreground",
        )}
        aria-current={active ? "page" : undefined}
      >
        {icon ?? <span className="size-1.5 rounded-full bg-current opacity-45" />}
        <span className="flex-1">{label}</span>
        <ChevronRight
          className={cn(
            "size-3.5 transition-opacity",
            active ? "opacity-60" : "opacity-0 group-hover:opacity-60",
          )}
          aria-hidden="true"
        />
      </Link>
    );
    return closeOnSelect ? (
      <DialogClose asChild key={href}>
        {content}
      </DialogClose>
    ) : (
      <React.Fragment key={href}>{content}</React.Fragment>
    );
  };

  return (
    <nav className="grid gap-6" aria-label="CMS navigation">
      <div className="grid gap-1">
        {item(
          "/admin",
          "Overview",
          <LayoutDashboard className="size-4" aria-hidden="true" />,
        )}
      </div>
      {ADMIN_RESOURCE_GROUPS.map((group) => (
        <div key={group.label}>
          <p className="mb-2 px-3 font-mono text-[0.58rem] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
            {group.label}
          </p>
          <div className="grid gap-1">
            {group.items
              .filter(
                (resource) =>
                  role === "owner" || !OWNER_ONLY_RESOURCES.has(resource as AdminResource),
              )
              .map((resource) =>
              item(
                `/admin/${resource}`,
                ADMIN_RESOURCE_LABELS[resource as AdminResource],
              ),
              )}
          </div>
        </div>
      ))}
    </nav>
  );
}

export function AdminShell({
  children,
  csrfToken,
  user,
}: {
  children: React.ReactNode;
  csrfToken?: string | undefined;
  user: User;
}) {
  const router = useRouter();
  const [loggingOut, startTransition] = React.useTransition();
  const logout = () =>
    startTransition(async () => {
      try {
        await getBrowserApi(csrfToken).admin.logout();
      } finally {
        router.replace("/admin/login");
        router.refresh();
      }
    });

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-border bg-surface-raised/80 px-4 py-5 backdrop-blur-xl xl:flex xl:flex-col">
        <Link
          href="/admin"
          className="flex min-h-12 items-center gap-3 rounded-xl px-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="grid size-9 place-items-center rounded-full bg-foreground font-mono text-xs font-bold text-background">
            CMS
          </span>
          <span>
            <strong className="block text-sm">Portfolio studio</strong>
            <span className="text-xs text-muted-foreground">Canonical content</span>
          </span>
        </Link>
        <div className="mt-7 flex-1 overflow-y-auto pr-1 [scrollbar-gutter:stable]">
          <AdminNavigation role={user.role} />
        </div>
        <div className="mt-5 border-t border-border pt-4">
          <p className="truncate px-3 text-xs font-semibold">{user.display_name}</p>
          <p className="mt-1 truncate px-3 text-xs text-muted-foreground">{user.email}</p>
          <Button
            variant="ghost"
            className="mt-2 w-full justify-start"
            onClick={logout}
            disabled={loggingOut}
          >
            <LogOut aria-hidden="true" />
            {loggingOut ? "Signing out…" : "Sign out"}
          </Button>
        </div>
      </aside>

      <div className="xl:pl-72">
        <header className="sticky top-0 z-20 border-b border-border bg-background/82 backdrop-blur-xl">
          <div className="flex min-h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-2">
              <Dialog>
                <DialogTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="xl:hidden"
                    aria-label="Open CMS navigation"
                  >
                    <Menu aria-hidden="true" />
                  </Button>
                </DialogTrigger>
                <DialogContent className="inset-y-3 left-3 right-auto top-3 w-[min(22rem,calc(100%-1.5rem))] max-w-none translate-x-0 translate-y-0">
                  <DialogHeader>
                    <DialogTitle>Portfolio studio</DialogTitle>
                    <DialogDescription>
                      Manage canonical public content and settings.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="overflow-y-auto">
                    <AdminNavigation closeOnSelect role={user.role} />
                  </div>
                </DialogContent>
              </Dialog>
              <div className="hidden items-center gap-2 font-mono text-[0.62rem] uppercase tracking-[0.13em] text-muted-foreground sm:flex">
                <Settings2 className="size-3.5 text-primary" aria-hidden="true" />
                Authenticated · {user.role}
              </div>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link href="/" prefetch={false} target="_blank" rel="noreferrer">
                View public site <ArrowUpRight aria-hidden="true" />
              </Link>
            </Button>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
