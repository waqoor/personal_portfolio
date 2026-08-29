import { cva, type VariantProps } from "class-variance-authority";
import { AlertCircle, CheckCircle2, Inbox, Info, LoaderCircle } from "lucide-react";
import * as React from "react";
import { cn } from "./utils";

export const Skeleton = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("animate-pulse rounded-xl bg-foreground/[0.08] motion-reduce:animate-none", className)} {...props} />
  ),
);
Skeleton.displayName = "Skeleton";

const alertVariants = cva(
  "grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-2xl border p-4 text-sm text-foreground [&>svg]:mt-0.5 [&>svg]:size-4",
  {
    variants: {
      variant: {
        default: "border-border-strong bg-surface-raised/70 [&>svg]:text-muted-foreground",
        destructive: "border-destructive/30 bg-destructive/8 [&>svg]:text-destructive",
        success: "border-success/35 bg-success/10 [&>svg]:text-success",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

type AlertVariant = NonNullable<VariantProps<typeof alertVariants>["variant"]>;
type AlertProps = React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>;

export function Alert({ className, role, variant = "default", ...props }: AlertProps) {
  const resolvedRole = role ?? (variant === "destructive" ? "alert" : variant === "success" ? "status" : undefined);
  return <div role={resolvedRole} className={cn(alertVariants({ variant }), className)} {...props} />;
}

export function AlertIcon({ variant = "default" }: { variant?: AlertVariant }) {
  if (variant === "success") return <CheckCircle2 aria-hidden="true" />;
  if (variant === "destructive") return <AlertCircle aria-hidden="true" />;
  return <Info aria-hidden="true" />;
}

export function AlertTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("font-semibold leading-5", className)} {...props} />;
}

export function AlertDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("col-start-2 leading-6 text-muted-foreground", className)} {...props} />;
}

type EmptyStateProps = React.HTMLAttributes<HTMLDivElement> & {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
};

export function EmptyState({ action, className, description, icon, title, ...props }: EmptyStateProps) {
  return (
    <div className={cn("mx-auto flex min-h-64 max-w-xl flex-col items-center justify-center rounded-[var(--radius-card)] border border-dashed border-border-strong bg-surface-raised/45 px-6 py-12 text-center", className)} {...props}>
      <div className="mb-5 grid size-12 place-items-center rounded-full border border-border bg-background text-muted-foreground">{icon ?? <Inbox className="size-5" />}</div>
      <h2 className="font-display text-2xl tracking-[-0.035em]">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

export function LoadingIndicator({ label = "Loading" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted-foreground" role="status">
      <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
      {label}
    </span>
  );
}
