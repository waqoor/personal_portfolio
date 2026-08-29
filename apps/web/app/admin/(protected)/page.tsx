import { Badge, Button, Card } from "@portfolio/ui";
import { Activity, ArrowRight, CircleAlert, FileClock, Inbox, Layers3 } from "lucide-react";
import Link from "next/link";
import { getAdminApi, loadApi } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function AdminDashboardPage() {
  const api = await getAdminApi();
  const result = await loadApi(() => api.admin.getDashboard());

  return (
    <main id="main-content" className="px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
      <div className="mx-auto max-w-[90rem]">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="eyebrow">CMS overview</p>
            <h1 className="mt-5 font-display text-5xl leading-none tracking-[-0.055em]">Portfolio control room.</h1>
          </div>
          <Badge variant="verified" className="self-start sm:self-auto"><Activity aria-hidden="true" />Authenticated session</Badge>
        </div>

        {!result.ok ? (
          <Card className="mt-8 p-8">
            <CircleAlert className="size-6 text-destructive" aria-hidden="true" />
            <h2 className="mt-5 font-display text-3xl">Dashboard data unavailable</h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">{result.error.message}</p>
          </Card>
        ) : (
          <>
            <dl className="mt-10 grid grid-cols-[repeat(auto-fit,minmax(min(100%,10.5rem),1fr))] gap-4">
              <Card className="p-5 sm:p-6">
                <FileClock className="size-5 text-primary" aria-hidden="true" />
                <dt className="mt-6 text-sm text-muted-foreground sm:mt-8">Draft content</dt>
                <dd className="mt-2 font-display text-5xl tracking-[-0.06em]">{result.data.drafts}</dd>
              </Card>
              <Card className="p-5 sm:p-6">
                <Layers3 className="size-5 text-primary" aria-hidden="true" />
                <dt className="mt-6 text-sm text-muted-foreground sm:mt-8">Pending approvals</dt>
                <dd className="mt-2 font-display text-5xl tracking-[-0.06em]">{result.data.pending_approvals}</dd>
              </Card>
              <Card className="p-5 sm:p-6">
                <Inbox className="size-5 text-primary" aria-hidden="true" />
                <dt className="mt-6 text-sm text-muted-foreground sm:mt-8">Unread contacts</dt>
                <dd className="mt-2 font-display text-5xl tracking-[-0.06em]">{result.data.unread_contacts}</dd>
              </Card>
              <Card className="p-5 sm:p-6">
                <Layers3 className="size-5 text-primary" aria-hidden="true" />
                <dt className="mt-6 text-sm text-muted-foreground sm:mt-8">Managed content types</dt>
                <dd className="mt-2 font-display text-5xl tracking-[-0.06em]">{Object.keys(result.data.counts).length}</dd>
              </Card>
              <Card variant="contrast" className="max-sm:col-span-full p-5 sm:p-6">
                <Activity className="size-5 text-primary" aria-hidden="true" />
                <dt className="mt-6 text-sm text-background/60 sm:mt-8">Managed records</dt>
                <dd className="mt-2 font-display text-5xl tracking-[-0.06em]">{Object.values(result.data.counts).reduce((total, count) => total + count, 0)}</dd>
              </Card>
            </dl>

            <section className="mt-10" aria-labelledby="chapter-map-heading">
              <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div><p className="eyebrow">Public chapter map</p><h2 id="chapter-map-heading" className="mt-5 font-display text-3xl tracking-[-0.045em]">Where to change each page.</h2></div>
                <p className="max-w-xl text-sm leading-6 text-muted-foreground">Content remains canonical: edit the record here, publish it, and the matching public chapter reads the same source.</p>
              </div>
              <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                {[
                  { chapter: "01", title: "About", body: "Profile, portrait, résumé, links, education, and skills.", href: "/admin/profile", cta: "Edit profile" },
                  { chapter: "02", title: "Achievements", body: "Certifications, recognition records, and publication articles.", href: "/admin/certifications", cta: "Edit achievements" },
                  { chapter: "03", title: "Work", body: "Full-time, contract, part-time, and freelance experience.", href: "/admin/experience", cta: "Edit work" },
                  { chapter: "04", title: "Projects", body: "Owned products, public software, and open-source work.", href: "/admin/projects", cta: "Edit projects" },
                  { chapter: "05", title: "Sponsor", body: "Gateway destinations and private sponsorship inquiries.", href: "/admin/sponsorship", cta: "Edit sponsor" },
                ].map((item) => (
                  <Card key={item.chapter} variant={item.chapter === "01" ? "contrast" : "raised"} className="flex min-h-64 flex-col justify-between p-6">
                    <div><span className={`font-mono text-[0.58rem] uppercase tracking-[0.15em] ${item.chapter === "01" ? "text-background" : "text-muted-foreground"}`}>Chapter {item.chapter}</span><h3 className="mt-5 font-display text-[clamp(1.5rem,1.7vw,1.875rem)] leading-[1.05] tracking-[-0.045em]">{item.title}</h3><p className={`mt-4 text-sm leading-6 ${item.chapter === "01" ? "text-background/75" : "text-muted-foreground"}`}>{item.body}</p></div>
                    <Button asChild variant={item.chapter === "01" ? "signal" : "text"} className="mt-7 justify-start"><Link href={item.href}>{item.cta}<ArrowRight aria-hidden="true" /></Link></Button>
                  </Card>
                ))}
              </div>
            </section>

            <section className="mt-10">
              <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
                <h2 className="font-display text-3xl tracking-[-0.045em]">Recent activity</h2>
                <span className="font-mono text-[0.62rem] uppercase tracking-[0.12em] text-muted-foreground">Audit-aware changes</span>
              </div>
              <div className="mt-5 overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-surface-raised">
                {result.data.recent_activity.length > 0 ? result.data.recent_activity.map((item) => (
                  <div key={item.id} className="grid gap-2 border-b border-border p-5 last:border-b-0 sm:grid-cols-[auto_1fr_auto] sm:items-center">
                    <Badge variant="muted">{item.action}</Badge>
                    <p className="text-sm"><strong>{item.label}</strong><span className="text-muted-foreground"> · {item.resource}</span></p>
                    <time dateTime={item.at} className="font-mono text-[0.6rem] uppercase tracking-[0.1em] text-muted-foreground">{new Date(item.at).toLocaleString("en", { dateStyle: "medium", timeStyle: "short" })}</time>
                  </div>
                )) : (
                  <p className="p-8 text-center text-sm text-muted-foreground">No recent activity is available.</p>
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
