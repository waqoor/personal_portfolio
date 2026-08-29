import { Skeleton } from "@portfolio/ui";

export default function Loading() {
  return (
    <main id="main-content" className="site-shell section-space" aria-busy="true" aria-label="Loading page">
      <div className="grid min-h-[70dvh] items-center gap-10 lg:grid-cols-[1fr_0.75fr]">
        <div className="grid gap-5">
          <Skeleton className="h-4 w-36" />
          <Skeleton className="h-28 w-full max-w-3xl sm:h-44" />
          <Skeleton className="h-20 w-full max-w-xl" />
          <div className="flex gap-3"><Skeleton className="h-12 w-36 rounded-full" /><Skeleton className="h-12 w-28 rounded-full" /></div>
        </div>
        <Skeleton className="aspect-[4/5] w-full rounded-[2rem]" />
      </div>
    </main>
  );
}
