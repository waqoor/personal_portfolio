import { Button } from "@portfolio/ui";
import { RefreshCw } from "lucide-react";
import Link from "next/link";

export function PublicDataUnavailable({ reference }: { reference?: string | undefined }) {
  return (
    <main id="main-content" className="coordinate-grid min-h-[72dvh]">
      <div className="site-shell-narrow section-space flex min-h-[72dvh] flex-col justify-center">
        <p className="eyebrow">Content service offline</p>
        <h1 className="display-lg mt-7 max-w-5xl">The studio is here. Its live archive is reconnecting.</h1>
        <p className="mt-7 max-w-2xl text-base leading-7 text-muted-foreground">Published content is served from the canonical portfolio API and is never replaced with invented data. Please retry when the content service is available.</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button asChild variant="signal" size="lg"><Link href="/"><RefreshCw aria-hidden="true" />Retry</Link></Button>
          <Button asChild variant="outline" size="lg"><Link href="/contact">Contact</Link></Button>
        </div>
        {reference && <p className="mt-6 font-mono text-[0.65rem] uppercase tracking-[0.12em] text-muted-foreground">Request reference: {reference}</p>}
      </div>
    </main>
  );
}
