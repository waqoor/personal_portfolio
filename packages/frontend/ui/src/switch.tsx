import * as SwitchPrimitive from "@radix-ui/react-switch";
import * as React from "react";
import { cn } from "./utils";

export const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root>
>(({ className, ...props }, ref) => (
  <SwitchPrimitive.Root
    ref={ref}
    className={cn(
      "peer relative inline-flex h-11 w-12 shrink-0 cursor-pointer items-center rounded-full bg-transparent outline-none before:absolute before:inset-x-0 before:top-1/2 before:h-7 before:-translate-y-1/2 before:rounded-full before:border before:border-border-strong before:bg-muted before:transition-colors data-[state=checked]:before:border-primary data-[state=checked]:before:bg-primary focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:before:transition-none",
      className,
    )}
    {...props}
  >
    <SwitchPrimitive.Thumb className="pointer-events-none relative z-10 ml-1 block size-5 rounded-full bg-background shadow-md transition-transform data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-0 motion-reduce:transition-none" />
  </SwitchPrimitive.Root>
));
Switch.displayName = SwitchPrimitive.Root.displayName;
