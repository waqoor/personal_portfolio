"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

export function AppChrome({ assistant, children, footer, header }: { assistant: ReactNode; children: ReactNode; footer: ReactNode; header: ReactNode }) {
  const pathname = usePathname();
  const admin = pathname.startsWith("/admin");
  if (admin) return <>{children}</>;
  return <>{header}{children}{footer}{assistant}</>;
}
