import { Button } from "@portfolio/ui";
import { ArrowLeft, Search } from "lucide-react";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default function NotFound() {
  return (
    <main id="main-content" className="coordinate-grid min-h-[72dvh]">
      <div className="site-shell-narrow section-space flex min-h-[72dvh] flex-col justify-center">
        <p className="font-mono text-sm font-semibold tracking-[0.18em] text-primary">404 / NOT IN THE ARCHIVE</p>
        <h1 className="display-lg mt-6 max-w-5xl">The trail ends here.</h1>
        <p className="mt-7 max-w-xl text-base leading-7 text-muted-foreground">The address may have changed, or the content is no longer published. Nothing private is exposed in its place.</p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button asChild variant="signal" size="lg"><Link href="/"><ArrowLeft aria-hidden="true" />Return home</Link></Button>
          <Button asChild variant="outline" size="lg"><Link href="/projects"><Search aria-hidden="true" />Browse work</Link></Button>
        </div>
      </div>
    </main>
  );
}
