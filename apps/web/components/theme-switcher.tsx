"use client";

import { Button, cn } from "@portfolio/ui";
import { Laptop, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import * as React from "react";

const subscribe = () => () => undefined;
const options = [
  { value: "light", label: "Use light theme", icon: Sun },
  { value: "dark", label: "Use dark theme", icon: Moon },
  { value: "system", label: "Use system theme", icon: Laptop },
] as const;

export function ThemeSwitcher() {
  const { setTheme, theme } = useTheme();
  const mounted = React.useSyncExternalStore(subscribe, () => true, () => false);
  const selected = mounted ? (theme ?? "system") : "system";

  return (
    <div role="group" aria-label="Color theme" className="flex items-center rounded-full border border-border-strong bg-surface-raised/85 p-0.5 shadow-[0_8px_26px_-22px_var(--shadow-ink)]">
      {options.map(({ icon: Icon, label, value }) => (
        <Button
          key={value}
          type="button"
          variant="ghost"
          size="icon"
          aria-label={label}
          aria-pressed={selected === value}
          title={label}
          onClick={() => setTheme(value)}
          className={cn("size-11 rounded-full", selected === value && "bg-foreground text-background hover:bg-foreground hover:text-background")}
        >
          <Icon className="size-4" aria-hidden="true" />
        </Button>
      ))}
    </div>
  );
}
