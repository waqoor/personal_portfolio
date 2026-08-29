import { Badge, Card } from "@portfolio/ui";
import { Clock3, Database, MailCheck, ShieldCheck } from "lucide-react";
import type { Metadata } from "next";
import { DiscoverySignals } from "@/components/discovery-signals";
import { PageIntro } from "@/components/page-intro";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { ContactForm } from "@/features/contact/contact-form";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/contact", {
    title: "Contact",
    description: "Start a focused conversation about a project, role, open-source work, or technical collaboration.",
  });
}

export default async function ContactPage() {
  const result = await loadApi(() => getPublicApi().public.getContactOptions());
  if (!result.ok) return <PublicDataUnavailable reference={result.error.requestId} />;
  return (
    <main id="main-content">
      <DiscoverySignals path="/contact" />
      <PageIntro eyebrow="Contact / Collaboration" title="Start with the useful context." description="For projects, roles, open-source work, speaking, or technical collaboration. Describe the problem and desired outcome; the workflow handles delivery failures without losing a valid inquiry." />
      <section className="site-shell section-space grid gap-8 lg:grid-cols-[0.62fr_1fr] lg:items-start">
        <aside className="grid gap-4 lg:sticky lg:top-24" aria-label="Contact process">
          <Card variant="contrast" className="p-6 sm:p-8"><MailCheck className="size-7 text-primary" aria-hidden="true" /><h2 className="mt-8 font-display text-4xl leading-none tracking-[-0.05em]">What happens next</h2><ol className="mt-8 grid gap-5">{[{ icon: Database, title: "Stored first", text: "A valid inquiry is persisted before notification is attempted." }, { icon: ShieldCheck, title: "Handled privately", text: "Contact data is excluded from the public site and AI retrieval." }, { icon: Clock3, title: "Reviewed for fit", text: result.data.response_time_label ?? "Response timing depends on availability and fit." }].map(({ icon: Icon, text, title }, index) => <li key={title} className="grid grid-cols-[auto_1fr] gap-4 border-t border-background/15 pt-5"><span className="grid size-9 place-items-center rounded-full bg-primary/12 text-primary"><Icon className="size-4" aria-hidden="true" /><span className="sr-only">Step {index + 1}</span></span><div><h3 className="font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-background/60">{text}</p></div></li>)}</ol></Card>
          <div className="rounded-[var(--radius-card)] border border-border bg-primary/10 p-5"><Badge variant="signal">Privacy boundary</Badge><p className="mt-4 text-sm leading-6 text-muted-foreground">Do not send passwords, private keys, regulated data, or sensitive personal information through this form.</p></div>
        </aside>
        <Card variant="raised" className="p-6 sm:p-8 lg:p-10"><h2 className="font-display text-4xl leading-none tracking-[-0.05em]">Your inquiry</h2><p className="mt-4 text-sm leading-6 text-muted-foreground">Fields marked with an asterisk are required.</p><div className="mt-8"><ContactForm options={result.data} /></div></Card>
      </section>
    </main>
  );
}
