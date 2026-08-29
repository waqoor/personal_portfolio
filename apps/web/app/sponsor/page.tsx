import { Badge, Button, Card } from "@portfolio/ui";
import { ArrowUpRight, CircleDashed, HandCoins, HeartHandshake, Route, ShieldCheck } from "lucide-react";
import type { Metadata } from "next";
import { DiscoverySignals } from "@/components/discovery-signals";
import { ExternalLink } from "@/components/external-link";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { ContactForm } from "@/features/contact/contact-form";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/sponsor", {
    title: "Sponsor Yazeed Hasan",
    description: "Direct sponsorship routes and purpose-specific sponsorship inquiries for Yazeed Hasan's work.",
  });
}

export default async function SponsorPage() {
  const api = getPublicApi();
  const result = await loadApi(() => Promise.all([
    api.public.getSponsorship(),
    api.public.getContactOptions(),
  ]));
  if (!result.ok) return <PublicDataUnavailable reference={result.error.requestId} />;

  const [sponsorship, contactOptions] = result.data;

  return (
    <main id="main-content">
      <DiscoverySignals path="/sponsor" />
      <header className="coordinate-grid border-b border-border">
        <div className="site-shell section-space grid gap-10 lg:grid-cols-[1fr_0.48fr] lg:items-end">
          <div><p className="eyebrow">Sponsor / 05</p><h1 className="display-lg mt-7 max-w-[11ch]">{sponsorship.title}</h1><p className="mt-7 max-w-3xl text-lg leading-8 text-muted-foreground">{sponsorship.description}</p></div>
          <Card variant="contrast" className="p-7 sm:p-8">
            <HeartHandshake className="size-8 text-primary dark:text-background" aria-hidden="true" />
            <p className="mt-8 font-display text-3xl leading-none tracking-[-0.045em]">Two clear paths.</p>
            <ol className="mt-7 grid gap-5 text-sm leading-6 text-background/70">
              <li className="grid grid-cols-[auto_1fr] gap-4 border-t border-background/15 pt-5"><span className="font-mono text-[0.6rem] text-primary dark:text-background">01</span><span><strong className="block text-background">Direct gateway</strong>Use a published, reviewed sponsorship destination when one is available.</span></li>
              <li className="grid grid-cols-[auto_1fr] gap-4 border-t border-background/15 pt-5"><span className="font-mono text-[0.6rem] text-primary dark:text-background">02</span><span><strong className="block text-background">Purpose-specific request</strong>Describe the initiative, intended outcome, timing, and proposed support.</span></li>
            </ol>
          </Card>
        </div>
      </header>

      <section className="site-shell section-space" aria-labelledby="gateway-heading">
        <div className="grid gap-8 lg:grid-cols-[0.42fr_1fr]">
          <div><div className="flex items-center gap-3"><HandCoins className="size-5 text-primary" aria-hidden="true" /><p className="eyebrow">Direct gateway</p></div><h2 id="gateway-heading" className="display-md mt-7 max-w-[9ch]">A reviewed route for direct support.</h2><p className="mt-6 max-w-md text-sm leading-7 text-muted-foreground">Gateway destinations are published only after the provider, terms, currency, and purpose have been reviewed in the admin panel.</p></div>
          {sponsorship.enabled && sponsorship.links.length > 0 ? (
            <div className="grid gap-4">
              {sponsorship.links.map((link) => (
                <Card key={link.url} variant="raised" className="flex flex-col justify-between gap-8 p-7 sm:flex-row sm:items-center sm:p-9">
                  <div><Badge variant="verified"><ShieldCheck aria-hidden="true" />Reviewed destination</Badge><h3 className="mt-5 font-display text-4xl tracking-[-0.05em]">{link.label}</h3></div>
                  <Button asChild variant="signal" size="lg"><ExternalLink href={link.url}>{link.label}<ArrowUpRight aria-hidden="true" /></ExternalLink></Button>
                </Card>
              ))}
            </div>
          ) : (
            <Card className="relative overflow-hidden border-dashed p-8 sm:p-10">
              <div className="absolute -right-20 -top-20 size-60 rounded-full bg-primary/12 blur-3xl" aria-hidden="true" />
              <CircleDashed className="size-8 text-primary" aria-hidden="true" />
              <Badge variant="muted" className="mt-8">Details pending</Badge>
              <h3 className="mt-5 font-display text-4xl leading-none tracking-[-0.05em]">The gateway is intentionally not guessed.</h3>
              <p className="mt-6 max-w-2xl text-sm leading-7 text-muted-foreground">No payment destination has been supplied yet. Once Yazeed provides the gateway and terms, it can be added and published from Admin → Sponsorship without a code change.</p>
            </Card>
          )}
        </div>
      </section>

      <section className="border-y border-border bg-muted/45" aria-labelledby="sponsor-inquiry-heading">
        <div className="site-shell section-space grid gap-8 lg:grid-cols-[0.58fr_1fr] lg:items-start">
          <aside className="grid gap-5 lg:sticky lg:top-24">
            <Card variant="contrast" className="p-7 sm:p-9"><Route className="size-8 text-primary" aria-hidden="true" /><h2 id="sponsor-inquiry-heading" className="mt-8 font-display text-5xl leading-[0.94] tracking-[-0.055em]">Sponsor for a purpose.</h2><p className="mt-6 text-sm leading-7 text-background/65">Use this route when support is connected to a particular product, open-source contribution, research effort, educational initiative, or event. The form creates a private sponsorship inquiry, not a public endorsement.</p><ul className="mt-8 grid gap-4">{sponsorship.principles.map((principle) => <li key={principle} className="flex gap-3 border-t border-background/15 pt-4 text-sm leading-6"><ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />{principle}</li>)}</ul></Card>
            <p className="rounded-[var(--radius-card)] border border-border bg-primary/10 p-5 text-sm leading-6 text-muted-foreground">Useful context: purpose, intended beneficiaries, expected outcome, timing, proposed amount or in-kind support, and any public attribution requirements.</p>
          </aside>
          <Card variant="raised" className="p-6 sm:p-8 lg:p-10"><Badge variant="signal">Private inquiry</Badge><h2 className="mt-6 font-display text-4xl leading-none tracking-[-0.05em]">Tell me what the sponsorship should make possible.</h2><p className="mt-4 text-sm leading-7 text-muted-foreground">The conversation type is preselected as Sponsorship. You can still change it if a different path fits better.</p><div className="mt-9"><ContactForm options={contactOptions} defaultCategoryId="sponsorship" submitLabel="Send sponsorship inquiry" subjectPlaceholder="What would the sponsorship support?" /></div></Card>
        </div>
      </section>
    </main>
  );
}
