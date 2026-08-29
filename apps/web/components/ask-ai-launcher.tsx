"use client";

import { Button } from "@portfolio/ui";
import { Bot } from "lucide-react";

export function AskAiLauncher({ className }: { className?: string }) {
  return (
    <Button type="button" variant="signal" size="lg" className={className} onClick={() => window.dispatchEvent(new Event("portfolio:ask-ai"))}>
      <Bot aria-hidden="true" />Ask my AI
    </Button>
  );
}
