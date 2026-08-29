"use client";

import { Button } from "@portfolio/ui";
import { RefreshCw } from "lucide-react";
import { useEffect } from "react";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error("Public page render failed", { digest: error.digest, message: error.message });
  }, [error]);

  return (
    <main id="main-content" className="coordinate-grid min-h-[72dvh]">
      <div className="site-shell-narrow section-space flex min-h-[72dvh] flex-col justify-center">
        <p className="eyebrow">Signal interrupted</p>
        <h1 className="display-lg mt-7 max-w-5xl">This page lost the thread.</h1>
        <p className="mt-7 max-w-xl text-base leading-7 text-muted-foreground">The interface is intact, but its content could not be resolved. Retry the request; no form data has been submitted.</p>
        <div className="mt-8"><Button onClick={reset} variant="signal" size="lg"><RefreshCw aria-hidden="true" />Try again</Button></div>
        {error.digest && <p className="mt-6 font-mono text-[0.65rem] text-muted-foreground">Reference: {error.digest}</p>}
      </div>
    </main>
  );
}
