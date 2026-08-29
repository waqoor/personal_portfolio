import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "./utils";

const cardVariants = cva(
  "relative overflow-hidden rounded-[var(--radius-card)] border text-card-foreground",
  {
    variants: {
      variant: {
        surface: "border-border bg-card shadow-[0_24px_70px_-48px_var(--shadow-ink)]",
        raised:
          "border-border-strong bg-surface-raised shadow-[0_30px_90px_-56px_var(--shadow-ink)]",
        editorial:
          "rounded-none border-x-0 border-b-0 border-t-border-strong bg-transparent",
        contrast: "border-foreground/10 bg-foreground text-background",
        glass:
          "border-white/15 bg-background/65 shadow-[0_30px_80px_-46px_var(--shadow-ink)] backdrop-blur-2xl supports-[backdrop-filter]:bg-background/55",
        accent: "border-primary/40 bg-primary/10 shadow-[inset_0_1px_0_color-mix(in_oklab,var(--primary)_25%,transparent)]",
      },
    },
    defaultVariants: { variant: "surface" },
  },
);

export type CardProps = React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof cardVariants>;

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, ...props }, ref) => (
    <div ref={ref} className={cn(cardVariants({ variant }), className)} {...props} />
  ),
);
Card.displayName = "Card";

export const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-2 p-6 md:p-8", className)} {...props} />
  ),
);
CardHeader.displayName = "CardHeader";

export const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3 ref={ref} className={cn("font-display text-2xl leading-[1.05] tracking-[-0.035em]", className)} {...props} />
  ),
);
CardTitle.displayName = "CardTitle";

export const CardDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(
  ({ className, ...props }, ref) => (
    <p ref={ref} className={cn("max-w-prose text-sm leading-6 text-muted-foreground", className)} {...props} />
  ),
);
CardDescription.displayName = "CardDescription";

export const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("px-6 pb-6 md:px-8 md:pb-8", className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

export const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center gap-3 border-t border-border px-6 py-4 md:px-8", className)} {...props} />
  ),
);
CardFooter.displayName = "CardFooter";
