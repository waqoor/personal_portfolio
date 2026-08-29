import Link from "next/link";
import type { ReactNode } from "react";

export function ProfileCtaLink({
  children,
  url,
}: {
  children: ReactNode;
  url: string;
}) {
  if (url.startsWith("/")) return <Link href={url}>{children}</Link>;
  const external = url.startsWith("https://");
  return (
    <a
      href={url}
      {...(external ? { target: "_blank", rel: "noreferrer" } : {})}
    >
      {children}
    </a>
  );
}
