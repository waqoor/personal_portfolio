import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";
import { cn } from "./utils";

const badgeVariants = cva(
  "inline-flex min-h-6 items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[0.68rem] font-medium uppercase leading-none tracking-[0.12em]",
  {
    variants: {
      variant: {
        default: "border-border-strong bg-surface-raised text-foreground",
        signal: "border-primary/45 bg-primary/12 text-accent-ink dark:text-primary",
        verified: "border-success/35 bg-success/10 text-success-foreground",
        outline: "border-current bg-transparent text-current",
        muted: "border-transparent bg-foreground/[0.06] text-muted-foreground",
        destructive: "border-destructive/35 bg-destructive/10 text-destructive",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>;

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
