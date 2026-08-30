import { Badge, Button, Card } from "@portfolio/ui";
import { HandCoins, HeartHandshake, Mail, Route, ShieldCheck } from "lucide-react";
import type { Metadata } from "next";
import { DiscoverySignals } from "@/components/discovery-signals";
import { ExternalLink } from "@/components/external-link";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { ContactForm } from "@/features/contact/contact-form";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

const GITHUB_SPONSORS_URL = "https://github.com/sponsors/yazeedhasan97";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/sponsor", {
    title: "Sponsor Yazeed Hasan",
    description:
      "Support Yazeed Hasan through GitHub Sponsors or send a private sponsorship inquiry.",
  });
}

function isGitHubSponsorsUrl(value: string): boolean {
  try {
    const url = new URL(value);
    const path = url.pathname.split("/").filter(Boolean);
    return (
      url.protocol === "https:" &&
      url.hostname === "github.com" &&
      (url.port === "" || url.port === "443") &&
      !url.username &&
      !url.password &&
      path.length >= 2 &&
      path[0]?.toLowerCase() === "sponsors"
    );
  } catch {
    return false;
  }
}

function sponsorshipEmailHref(email: string): string {
  const subject = encodeURIComponent("Sponsorship inquiry");
  const body = encodeURIComponent(
    [
      "Hello Yazeed,",
      "",
      "I would like to discuss sponsorship for:",
      "",
      "Purpose and intended outcome:",
      "Timing:",
      "Proposed support:",
    ].join("\r\n"),
  );
  return `mailto:${email}?subject=${subject}&body=${body}`;
}

export default async function SponsorPage() {
  const api = getPublicApi();
  const result = await loadApi(() =>
    Promise.all([
      api.public.getSponsorship(),
      api.public.getContactOptions(),
      api.public.getSiteShell(),
    ]),
  );
  if (!result.ok) return <PublicDataUnavailable reference={result.error.requestId} />;

  const [sponsorship, contactOptions, shell] = result.data;
  const configuredLinks = sponsorship.links.filter((link) =>
    isGitHubSponsorsUrl(link.url),
  );
  const supportLinks =
    configuredLinks.length > 0
      ? configuredLinks
      : [
          {
            label: "Open GitHub Sponsors",
            url: GITHUB_SPONSORS_URL,
            kind: "sponsor" as const,
            external: true,
          },
        ];
  const emailHref = shell.public_email
    ? sponsorshipEmailHref(shell.public_email)
    : undefined;

  return (
    <main id="main-content">
      <DiscoverySignals path="/sponsor" />
      <header className="coordinate-grid border-b border-border">
        <div className="site-shell section-space grid gap-10 lg:grid-cols-[1fr_0.48fr] lg:items-end">
          <div>
            <p className="eyebrow">Sponsor / 05</p>
            <h1 className="display-lg mt-7 max-w-[11ch]">{sponsorship.title}</h1>
            <p className="mt-7 max-w-3xl text-lg leading-8 text-muted-foreground">
              {sponsorship.description}
            </p>
          </div>
          <Card variant="contrast" className="p-7 sm:p-8">
            <HeartHandshake
              className="size-8 text-primary dark:text-background"
              aria-hidden="true"
            />
            <p className="mt-8 font-display text-3xl leading-none">
              Two sponsorship paths.
            </p>
            <ol className="mt-7 grid gap-5 text-sm leading-6 text-background/70">
              <li className="grid grid-cols-[auto_1fr] gap-4 border-t border-background/15 pt-5">
                <span
                  className="font-mono text-[0.6rem] text-primary dark:text-background"
                  aria-hidden="true"
                >
                  01
                </span>
                <span>
                  <strong className="block text-background">GitHub Sponsors</strong>
                  Use GitHub&apos;s hosted sponsorship and checkout flow.
                </span>
              </li>
              <li className="grid grid-cols-[auto_1fr] gap-4 border-t border-background/15 pt-5">
                <span
                  className="font-mono text-[0.6rem] text-primary dark:text-background"
                  aria-hidden="true"
                >
                  02
                </span>
                <span>
                  <strong className="block text-background">Private inquiry</strong>
                  Describe the initiative, timing, outcome, and proposed support.
                </span>
              </li>
            </ol>
          </Card>
        </div>
      </header>

      <section
        className="site-shell section-space"
        aria-labelledby="github-sponsors-heading"
      >
        <div className="grid gap-8 lg:grid-cols-[0.48fr_1fr] lg:items-start">
          <div>
            <div className="flex items-center gap-3">
              <HandCoins className="size-5 text-primary" aria-hidden="true" />
              <p className="eyebrow">Direct support</p>
            </div>
            <h2 id="github-sponsors-heading" className="display-md mt-7 max-w-[11ch]">
              Support through GitHub Sponsors
            </h2>
            <p className="mt-6 max-w-lg text-sm leading-7 text-muted-foreground">
              Choose a sponsorship option on GitHub. Payment and card details are entered and
              handled only by GitHub; this website never receives, processes, or stores them.
            </p>
          </div>
          <div className="grid gap-4">
            {supportLinks.map((link) => (
              <Card
                key={link.url}
                variant="raised"
                className="flex flex-col justify-between gap-8 p-7 sm:flex-row sm:items-center sm:p-9"
              >
                <div>
                  <Badge variant="verified">
                    <ShieldCheck aria-hidden="true" />
                    GitHub-hosted checkout
                  </Badge>
                  <h3 className="mt-5 font-display text-4xl">{link.label}</h3>
                  <p className="mt-3 max-w-xl text-sm leading-6 text-muted-foreground">
                    GitHub hosts the support options and checkout when Sponsors is active.
                  </p>
                </div>
                <Button asChild variant="signal" size="lg">
                  <ExternalLink
                    href={link.url}
                    rel="sponsored nofollow noopener noreferrer"
                  >
                    {link.label}
                  </ExternalLink>
                </Button>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section
        className="border-y border-border bg-muted/45"
        aria-labelledby="sponsor-inquiry-heading"
      >
        <div className="site-shell section-space grid gap-8 lg:grid-cols-[0.58fr_1fr] lg:items-start">
          <aside className="grid gap-5 lg:sticky lg:top-24">
            <Card variant="contrast" className="p-7 sm:p-9">
              <Route className="size-8 text-primary" aria-hidden="true" />
              <h2
                id="sponsor-inquiry-heading"
                className="mt-8 font-display text-5xl leading-[0.94]"
              >
                Contact me about sponsorship
              </h2>
              <p className="mt-6 text-sm leading-7 text-background/65">
                Use the form for support connected to a product, open-source contribution,
                research effort, educational initiative, or event. The inquiry stays private.
              </p>
              {sponsorship.principles.length > 0 && (
                <ul className="mt-8 grid gap-4">
                  {sponsorship.principles.map((principle) => (
                    <li
                      key={principle}
                      className="flex gap-3 border-t border-background/15 pt-4 text-sm leading-6"
                    >
                      <ShieldCheck
                        className="mt-0.5 size-4 shrink-0 text-primary"
                        aria-hidden="true"
                      />
                      {principle}
                    </li>
                  ))}
                </ul>
              )}
              {emailHref && (
                <Button
                  asChild
                  variant="primary"
                  size="lg"
                  className="mt-8 w-full sm:w-auto"
                >
                  <a href={emailHref}>
                    <Mail aria-hidden="true" />
                    Email about sponsorship
                  </a>
                </Button>
              )}
            </Card>
            <p className="rounded-[var(--radius-card)] border border-border bg-primary/10 p-5 text-sm leading-6 text-muted-foreground">
              Useful context: purpose, intended beneficiaries, expected outcome, timing,
              proposed amount or in-kind support, and any public attribution requirements.
            </p>
          </aside>
          <Card variant="raised" className="p-6 sm:p-8 lg:p-10">
            <Badge variant="signal">Private inquiry</Badge>
            <h3 className="mt-6 font-display text-4xl leading-none">
              Sponsorship inquiry
            </h3>
            <p className="mt-4 text-sm leading-7 text-muted-foreground">
              The conversation type is preselected as Sponsorship. The existing contact workflow
              validates and stores the inquiry so it is not lost if email delivery is delayed.
            </p>
            <div className="mt-9">
              <ContactForm
                options={contactOptions}
                defaultCategoryId="sponsorship"
                submitLabel="Send sponsorship inquiry"
                subjectPlaceholder="What would the sponsorship support?"
              />
            </div>
          </Card>
        </div>
      </section>
    </main>
  );
}
