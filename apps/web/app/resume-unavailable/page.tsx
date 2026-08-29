import { Button } from "@portfolio/ui";
import { ArrowLeft, RefreshCw } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Résumé unavailable", robots: { index: false, follow: false } };

export default function ResumeUnavailablePage() {
  return <main id="main-content" className="coordinate-grid min-h-[72dvh]"><div className="site-shell-narrow section-space flex min-h-[72dvh] flex-col justify-center"><p className="eyebrow">Stable résumé route</p><h1 className="display-lg mt-7 max-w-[11ch]">The current file could not be resolved.</h1><p className="mt-7 max-w-xl text-base leading-7 text-muted-foreground">The download link stays stable while the managed résumé can be replaced. No stale or guessed file is served when the current asset is unavailable.</p><div className="mt-8 flex flex-wrap gap-3"><Button asChild variant="signal" size="lg"><a href="/resume"><RefreshCw aria-hidden="true" />Try again</a></Button><Button asChild variant="outline" size="lg"><Link href="/"><ArrowLeft aria-hidden="true" />Return home</Link></Button></div></div></main>;
}
