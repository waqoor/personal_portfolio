import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "./utils";

export const buttonVariants = cva(
  "group relative inline-flex min-h-11 shrink-0 cursor-pointer items-center justify-center gap-2 overflow-hidden rounded-full border text-sm font-semibold tracking-[-0.01em] transition-[transform,background-color,color,border-color,box-shadow] duration-300 ease-out active:scale-[0.985] active:duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-45 motion-reduce:transform-none motion-reduce:transition-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary:
          "border-foreground bg-foreground text-background shadow-[0_12px_36px_-18px_var(--shadow-ink)] hover:-translate-y-0.5 hover:bg-primary hover:text-primary-foreground hover:shadow-[0_18px_46px_-20px_var(--shadow-accent)]",
        signal:
          "border-primary bg-primary text-primary-foreground shadow-[0_0_0_1px_color-mix(in_oklab,var(--primary)_25%,transparent),0_14px_38px_-20px_var(--shadow-accent)] before:absolute before:inset-y-0 before:left-[-30%] before:w-1/4 before:skew-x-[-22deg] before:bg-white/45 before:blur-sm before:transition-transform before:duration-700 hover:-translate-y-0.5 hover:before:translate-x-[600%]",
        secondary:
          "border-border-strong bg-surface-raised text-foreground shadow-[0_12px_30px_-24px_var(--shadow-ink)] hover:-translate-y-0.5 hover:border-foreground/30 hover:bg-surface-hover",
        outline:
          "border-border-strong bg-transparent text-foreground hover:-translate-y-0.5 hover:border-primary hover:bg-primary/10",
        ghost:
          "border-transparent bg-transparent text-foreground hover:bg-foreground/[0.06]",
        text:
          "min-h-11 rounded-none border-0 bg-transparent p-0 text-foreground active:scale-100 after:absolute after:inset-x-0 after:bottom-1 after:h-px after:origin-right after:scale-x-0 after:bg-current after:transition-transform hover:after:origin-left hover:after:scale-x-100",
        destructive:
          "border-destructive bg-destructive text-destructive-foreground hover:-translate-y-0.5 hover:brightness-95",
      },
      size: {
        sm: "min-h-11 px-4 text-xs",
        md: "px-5 py-2.5",
        lg: "min-h-13 px-7 text-base",
        icon: "size-11 p-0",
        "icon-sm": "size-11 min-h-11 p-0",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean;
  };

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ asChild = false, className, size, variant, ...props }, ref) => {
    const Component = asChild ? Slot : "button";
    return <Component className={cn(buttonVariants({ size, variant }), className)} ref={ref} {...props} />;
  },
);
Button.displayName = "Button";
