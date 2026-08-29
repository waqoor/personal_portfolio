"use client";

import type { FeatureSetting } from "@portfolio/api-client";
import { Alert, AlertDescription, AlertIcon, AlertTitle, Badge, Card, Switch } from "@portfolio/ui";
import { Eye, EyeOff, ShieldCheck } from "lucide-react";
import * as React from "react";
import { getBrowserApi } from "@/lib/browser-api";

export function FeatureSettings({ csrfToken, initial }: { csrfToken?: string | undefined; initial: FeatureSetting[] }) {
  const [settings, setSettings] = React.useState(initial);
  const [error, setError] = React.useState<string>();
  const [pending, startTransition] = React.useTransition();
  const toggle = (setting: FeatureSetting, enabled: boolean) => startTransition(async () => {
    const previous = settings;
    setSettings((items) => items.map((item) => item.key === setting.key ? { ...item, enabled } : item));
    try { const updated = await getBrowserApi(csrfToken).admin.updateFeatureSetting(setting.key, enabled); setSettings((items) => items.map((item) => item.key === setting.key ? updated : item)); setError(undefined); }
    catch (caught) { setSettings(previous); setError(caught instanceof Error ? caught.message : "Feature setting could not be updated."); }
  });
  return <div><div><p className="eyebrow">Experience settings</p><h1 className="mt-5 font-display text-5xl leading-none tracking-[-0.055em]">Feature toggles</h1><p className="mt-4 max-w-3xl text-sm leading-6 text-muted-foreground">Disable a public capability without deleting its content. Backend publication authority remains the final source of visibility.</p></div>{error && <Alert variant="destructive" className="mt-6"><AlertIcon variant="destructive" /><AlertTitle>Update failed</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}<div className="mt-8 grid gap-4 md:grid-cols-2">{settings.map((setting) => <Card key={setting.key} className="flex min-h-44 flex-col justify-between p-6"><div className="flex items-start justify-between gap-4"><span className={`grid size-10 place-items-center rounded-full ${setting.enabled ? "bg-primary/15 text-accent-ink dark:text-primary" : "bg-muted text-muted-foreground"}`}>{setting.enabled ? <Eye className="size-4" aria-hidden="true" /> : <EyeOff className="size-4" aria-hidden="true" />}</span><Badge variant={setting.public ? "signal" : "muted"}>{setting.public ? "Public feature" : "Internal"}</Badge></div><div className="mt-6 flex items-end justify-between gap-5"><div><h2 className="font-semibold">{setting.label}</h2>{setting.description && <p className="mt-2 text-sm leading-6 text-muted-foreground">{setting.description}</p>}</div><Switch checked={setting.enabled} onCheckedChange={(enabled) => toggle(setting, enabled)} disabled={pending} aria-label={`${setting.enabled ? "Disable" : "Enable"} ${setting.label}`} /></div></Card>)}</div><p className="mt-6 flex items-center gap-2 text-xs leading-5 text-muted-foreground"><ShieldCheck className="size-4 text-primary" aria-hidden="true" />Disabling a feature never deletes its records.</p></div>;
}
