import type { Metadata } from "next";
import type { ReactNode } from "react";
import { redirect } from "next/navigation";
import { AdminShell } from "@/features/admin/admin-shell";
import { getAdminApi, loadApi } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  robots: { index: false, follow: false, nocache: true },
};

export default async function ProtectedAdminLayout({ children }: { children: ReactNode }) {
  const api = await getAdminApi();
  const result = await loadApi(() => api.admin.getSession());
  if (!result.ok || !result.data.authenticated || !result.data.user) redirect("/admin/login");
  return <AdminShell user={result.data.user} {...(result.data.csrf_token ? { csrfToken: result.data.csrf_token } : {})}>{children}</AdminShell>;
}
