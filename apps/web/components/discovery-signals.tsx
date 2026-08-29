import { DiscoveryBreadcrumbs } from "@/components/discovery-breadcrumbs";
import { getPublicApi, loadApi } from "@/lib/api";
import { jsonLd } from "@/lib/metadata";

export async function DiscoverySignals({ path }: { path: string }) {
  const result = await loadApi(() => getPublicApi().public.getDiscoveryPage(path));
  if (!result.ok) return null;
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(result.data.json_ld) }} />
      <DiscoveryBreadcrumbs breadcrumbs={result.data.breadcrumbs} />
    </>
  );
}
