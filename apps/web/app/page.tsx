import type { Metadata } from "next";
import { DiscoverySignals } from "@/components/discovery-signals";
import { HomepageSections } from "@/features/home/section-registry";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/", {
    title: "Yazeed Hasan — AI & Data Technical Leader",
    description: "Enterprise AI/ML, data platforms, MLOps, strategy, technical leadership, and accountable delivery by Yazeed Hasan.",
  });
}

export default async function HomePage() {
  const result = await loadApi(() => getPublicApi().public.getHomePage());
  if (!result.ok) return <PublicDataUnavailable reference={result.error.requestId} />;
  return (
    <main id="main-content">
      <DiscoverySignals path="/" />
      <HomepageSections data={result.data} />
    </main>
  );
}
