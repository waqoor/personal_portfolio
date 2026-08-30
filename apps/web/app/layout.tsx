import "./globals.css";

import { PUBLIC_NAV_FALLBACK } from "@portfolio/config";
import type { NavigationItem, SiteShell } from "@portfolio/api-client";
import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, Manrope, Source_Serif_4 } from "next/font/google";
import type { ReactNode } from "react";
import { AskAssistant } from "@/components/ask-assistant";
import { AppChrome } from "@/components/app-chrome";
import { Providers } from "@/components/providers";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { getPublicApi, loadApi } from "@/lib/api";
import { siteUrl } from "@/lib/metadata";

const bodyFont = Manrope({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});
const displayFont = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});
const monoFont = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: siteUrl(),
  title: { default: "Yazeed Hasan — AI & Data Technical Leader", template: "%s · Yazeed Hasan" },
  description:
    "Enterprise AI/ML, data platforms, MLOps, strategy, technical leadership, and accountable delivery by Yazeed Hasan.",
  keywords: ["Enterprise AI", "Machine learning", "Data platforms", "MLOps", "Technical leadership", "AI strategy"],
  authors: [{ name: "Yazeed Hasan", url: "/" }],
  creator: "Yazeed Hasan",
  publisher: "Yazeed Hasan",
  category: "Technology",
  applicationName: "Yazeed Hasan Portfolio",
  formatDetection: { email: false, address: false, telephone: false },
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  colorScheme: "light dark",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f3eb" },
    { media: "(prefers-color-scheme: dark)", color: "#1b1a17" },
  ],
};

const fallbackNavigation: NavigationItem[] = PUBLIC_NAV_FALLBACK.map(
  (item, index) => ({
    id: `fallback-${item.href}`,
    label: item.label,
    href: item.href,
    external: false,
    order: index,
    location: "header",
  }),
);

const fallbackShell: SiteShell = {
  brand_name: "Yazeed Hasan",
  brand_mark: "YH",
  header_navigation: fallbackNavigation,
  footer_navigation: [],
  socials: [],
  assistant_enabled: false,
  assistant_settings: {
    enabled: false,
    greeting: "Ask about published projects, experience, skills, and writing.",
    suggested_questions: [
      "Which projects best demonstrate production engineering?",
    ],
    disclaimer: "Answers use published portfolio evidence only.",
    max_question_length: 600,
  },
  contact_enabled: false,
  presentation: {
    site_name: "Yazeed Hasan",
    default_title: "Yazeed Hasan — AI & Data Technical Leader",
    default_description: "Enterprise AI/ML, data platforms, MLOps, strategy, technical leadership, and accountable delivery by Yazeed Hasan.",
    locale: "en",
    footer_eyebrow: "Yazeed Hasan / Amman",
    footer_heading: "Align strategy. Build useful systems. Deliver accountable outcomes.",
    footer_statement: "Enterprise AI, data platforms, MLOps, strategy, and delivery.",
    about_title: "Leadership, technical depth, and accountable delivery.",
    about_intro: "A source-backed professional profile consolidated into the homepage.",
    achievements_title: "A record of earned milestones.",
    achievements_intro: "Certifications, awards, professional achievements, academic recognition, and published research.",
    work_title: "Work across roles and operating contexts.",
    work_intro: "Primary employment, independent contracts, part-time teaching, project work, and early technical practice.",
    projects_title: "Products and open work I can stand behind.",
    projects_intro: "Owned and publicly exposed products, software, and open-source contributions.",
    writing_title: "Writing",
    writing_intro: "Technical field notes and practical explanations.",
    sectors_title: "Sectors",
    sectors_intro: "Applied domains supported by published project evidence.",
    open_source_title: "Open source",
    open_source_intro: "Public repositories and contribution work.",
    sponsorship_title: "Sponsor a useful idea, project, or public contribution.",
    sponsorship_description: "Direct support runs through GitHub Sponsors. Purpose-specific sponsorship inquiries are also open.",
    sponsorship_principles: [
      "Scope and purpose are agreed before funds move.",
      "Sponsorship never purchases private access or editorial control.",
      "Public and open-source work remains technically independent.",
    ],
  },
};

export default async function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  const result = await loadApi(() => getPublicApi().public.getSiteShell());
  const shell = result.ok ? result.data : fallbackShell;
  return (
    <html lang="en" data-scroll-behavior="smooth" suppressHydrationWarning>
      <body
        className={`${bodyFont.variable} ${displayFont.variable} ${monoFont.variable} bg-background text-foreground antialiased`}
      >
        <Providers>
          <a
            href="#main-content"
            className="fixed left-4 top-3 z-[120] -translate-y-20 rounded-full bg-primary px-5 py-3 text-sm font-bold text-primary-foreground shadow-xl transition-transform focus:translate-y-0 motion-reduce:transition-none"
          >
            Skip to main content
          </a>
          <div className="grain-overlay" aria-hidden="true" />
          <AppChrome
            header={
              <SiteHeader
                brandName={shell.brand_name}
                brandLogo={shell.brand_logo}
              />
            }
            footer={
              <SiteFooter
                brandName={shell.brand_name}
                socials={shell.socials}
                navigation={shell.footer_navigation}
                contactEnabled={shell.contact_enabled}
                publicEmail={shell.public_email}
                presentation={shell.presentation}
              />
            }
            assistant={
              shell.assistant_enabled ? (
                <AskAssistant settings={shell.assistant_settings} />
              ) : null
            }
          >
            {children}
          </AppChrome>
        </Providers>
      </body>
    </html>
  );
}
