import { ArrowUpRight } from "lucide-react";
import type { AnchorHTMLAttributes } from "react";
import { cn } from "@portfolio/ui";

function safeExternalUrl(value: string): string | undefined {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.toString() : undefined;
  } catch {
    return undefined;
  }
}

type ExternalLinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
  href: string;
  showIcon?: boolean;
};

export function ExternalLink({ children, className, href, showIcon = true, ...props }: ExternalLinkProps) {
  const safeHref = safeExternalUrl(href);
  if (!safeHref) return <span className={className}>{children}</span>;
  return (
    <a href={safeHref} target="_blank" rel="noreferrer" className={cn("inline-flex min-h-11 items-center gap-1.5", className)} {...props}>
      {children}{showIcon && <ArrowUpRight className="size-[0.9em]" aria-hidden="true" />}
    </a>
  );
}
