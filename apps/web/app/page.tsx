import type { Metadata } from "next";
import { DiscoverySignals } from "@/components/discovery-signals";
import { HomepageSections } from "@/features/home/section-registry";
import { PublicDataUnavailable } from "@/components/public-data-unavailable";
import { getPublicApi, loadApi } from "@/lib/api";
import { discoveryMetadata } from "@/lib/metadata";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  return discoveryMetadata("/", { title: "Portfolio", description: "Selected work, experience, writing, and collaboration." });
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
