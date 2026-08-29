import { adminResourceSchema } from "@portfolio/api-client";
import { Alert, AlertDescription, AlertIcon, AlertTitle, Card } from "@portfolio/ui";
import { notFound } from "next/navigation";
import { FeatureSettings } from "@/features/admin/feature-settings";
import { HomepageComposer } from "@/features/admin/homepage-composer";
import { IdentityAssetsManager } from "@/features/admin/identity-assets-manager";
import { RESOURCE_DEFINITIONS } from "@/features/admin/resource-definitions";
import { ResourceWorkspace } from "@/features/admin/resource-workspace";
import { AssistantSettingsForm, SiteSettingsForm } from "@/features/admin/settings-forms";
import { getAdminApi, loadApi, type LoadResult } from "@/lib/api";

export const dynamic = "force-dynamic";
type Params = Promise<{ resource: string }>;

function AdminLoadError({ result }: { result: LoadResult<unknown> }) {
  if (result.ok) return null;
  return <Card className="p-8"><Alert variant="destructive"><AlertIcon variant="destructive" /><AlertTitle>Unable to load this workspace</AlertTitle><AlertDescription>{result.error.message}</AlertDescription></Alert></Card>;
}

function OwnerOnlyNotice() {
  return (
    <Card className="p-8">
      <Alert>
        <AlertIcon />
        <AlertTitle>Owner permission required</AlertTitle>
        <AlertDescription>
          This workspace changes public identity, availability, evidence, or destinations. Editors
          can continue authoring draft portfolio and writing records.
        </AlertDescription>
      </Alert>
    </Card>
  );
}

export default async function AdminResourcePage({ params }: { params: Params }) {
  const parsed = adminResourceSchema.safeParse((await params).resource);
  if (!parsed.success) notFound();
  const resource = parsed.data;
  const api = await getAdminApi();
  const session = await loadApi(() => api.admin.getSession());
  const csrfToken = session.ok ? session.data.csrf_token : undefined;
  const role = session.ok && session.data.user ? session.data.user.role : "editor";
  const isOwner = role === "owner";
  let content: React.ReactNode;

  if (
    !isOwner &&
    [
      "resumes",
      "homepage-sections",
      "feature-settings",
      "site-settings",
      "assistant-settings",
    ].includes(resource)
  ) {
    content = <OwnerOnlyNotice />;
  } else if (resource === "resumes") {
    const result = await loadApi(() => api.admin.getIdentityAssets());
    content = result.ok ? <IdentityAssetsManager initial={result.data} {...(csrfToken ? { csrfToken } : {})} /> : <AdminLoadError result={result} />;
  } else if (resource === "homepage-sections") {
    const result = await loadApi(() => api.admin.getHomepageSections());
    content = result.ok ? <HomepageComposer initial={result.data} {...(csrfToken ? { csrfToken } : {})} /> : <AdminLoadError result={result} />;
  } else if (resource === "feature-settings") {
    const result = await loadApi(() => api.admin.getFeatureSettings());
    content = result.ok ? <FeatureSettings initial={result.data} {...(csrfToken ? { csrfToken } : {})} /> : <AdminLoadError result={result} />;
  } else if (resource === "site-settings") {
    const result = await loadApi(() => api.admin.getSiteSettings());
    content = result.ok ? <SiteSettingsForm initial={result.data} {...(csrfToken ? { csrfToken } : {})} /> : <AdminLoadError result={result} />;
  } else if (resource === "assistant-settings") {
    const result = await loadApi(() => api.admin.getAssistantSettings());
    content = result.ok ? <AssistantSettingsForm initial={result.data} {...(csrfToken ? { csrfToken } : {})} /> : <AdminLoadError result={result} />;
  } else {
    const definition = RESOURCE_DEFINITIONS[resource];
    if (!definition) notFound();
    if (!isOwner && definition.ownerOnly) {
      content = <OwnerOnlyNotice />;
    } else {
      const result = await loadApi(() =>
        api.admin.list(resource, { page: 1, pageSize: 25 }),
      );
      content = result.ok ? (
        <ResourceWorkspace
          resource={resource}
          definition={definition}
          initial={result.data}
          role={role}
          {...(csrfToken ? { csrfToken } : {})}
        />
      ) : (
        <AdminLoadError result={result} />
      );
    }
  }

  return <main id="main-content" className="px-4 py-8 sm:px-6 lg:px-8 lg:py-10"><div className="mx-auto max-w-[90rem]">{content}</div></main>;
}
