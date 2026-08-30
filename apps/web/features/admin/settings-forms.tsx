"use client";

import type { AssistantSettings, SiteSettings } from "@portfolio/api-client";
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Button,
  Card,
  Field,
  FieldDescription,
  Input,
  Label,
  LoadingIndicator,
  Switch,
  Textarea,
} from "@portfolio/ui";
import { Bot, Save, Settings2 } from "lucide-react";
import * as React from "react";
import { getBrowserApi } from "@/lib/browser-api";

const presentationFields = [
  ["site_name", "Site name", false],
  ["default_title", "Default SEO title", false],
  ["default_description", "Default SEO description", true],
  ["locale", "Locale", false],
  ["footer_eyebrow", "Footer eyebrow", false],
  ["footer_heading", "Footer heading", true],
  ["footer_statement", "Footer closing statement", true],
  ["about_title", "Homepage profile title", true],
  ["about_intro", "Homepage profile introduction", true],
  ["achievements_title", "Achievements page title", false],
  ["achievements_intro", "Achievements page introduction", true],
  ["work_title", "Work page title", false],
  ["work_intro", "Work page introduction", true],
  ["projects_title", "Projects page title", false],
  ["projects_intro", "Projects page introduction", true],
  ["writing_title", "Writing page title", false],
  ["writing_intro", "Writing page introduction", true],
  ["sectors_title", "Sectors page title", false],
  ["sectors_intro", "Sectors page introduction", true],
  ["open_source_title", "Open-source page title", false],
  ["open_source_intro", "Open-source page introduction", true],
  ["sponsorship_title", "Sponsorship title", false],
  ["sponsorship_description", "Sponsorship introduction", true],
] as const satisfies ReadonlyArray<
  readonly [Exclude<keyof SiteSettings, "sponsorship_principles">, string, boolean]
>;

function SaveStatus({
  message,
}: {
  message?: { ok: boolean; text: string } | undefined;
}) {
  return message ? (
    <Alert variant={message.ok ? "success" : "destructive"}>
      <AlertIcon variant={message.ok ? "success" : "destructive"} />
      <AlertTitle>{message.ok ? "Saved" : "Unable to save"}</AlertTitle>
      <AlertDescription>{message.text}</AlertDescription>
    </Alert>
  ) : null;
}

export function SiteSettingsForm({
  csrfToken,
  initial,
}: {
  csrfToken?: string | undefined;
  initial: SiteSettings;
}) {
  const [message, setMessage] = React.useState<{ ok: boolean; text: string }>();
  const [pending, startTransition] = React.useTransition();
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    startTransition(async () => {
      try {
        await getBrowserApi(csrfToken).admin.updateSiteSettings({
          ...Object.fromEntries(
            presentationFields.map(([key]) => [key, String(form.get(key))]),
          ) as Omit<SiteSettings, "sponsorship_principles">,
          sponsorship_principles: String(form.get("sponsorship_principles"))
            .split("\n")
            .map((item) => item.trim())
            .filter(Boolean),
        });
        setMessage({ ok: true, text: "Site and discovery defaults saved." });
      } catch (caught) {
        setMessage({
          ok: false,
          text:
            caught instanceof Error
              ? caught.message
              : "Settings could not be saved.",
        });
      }
    });
  };
  return (
    <div>
      <div>
        <p className="eyebrow">Experience settings</p>
        <h1 className="mt-5 font-display text-5xl leading-none tracking-[-0.055em]">
          Site settings
        </h1>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-muted-foreground">
          Public identity, page introductions, sponsorship framing, footer copy,
          and metadata defaults.
        </p>
      </div>
      <Alert className="mt-8 max-w-4xl">
        <AlertIcon />
        <h2 className="font-semibold leading-5">Presentation configuration</h2>
        <AlertDescription>
          These values feed public metadata and structured discovery responses.
          The canonical hostname remains deployment-owned so an admin edit
          cannot redirect production URLs.
        </AlertDescription>
      </Alert>
      <Card variant="raised" className="mt-5 max-w-4xl p-6 sm:p-8">
        <form onSubmit={submit} className="grid gap-6">
          <div className="grid gap-5 sm:grid-cols-2">
            {presentationFields.map(([key, label, multiline]) => (
              <Field key={key} className={multiline ? "sm:col-span-2" : undefined}>
                <Label htmlFor={key}>{label}</Label>
                {multiline ? (
                  <Textarea id={key} name={key} defaultValue={initial[key]} required />
                ) : (
                  <Input id={key} name={key} defaultValue={initial[key]} required />
                )}
              </Field>
            ))}
            <Field className="sm:col-span-2">
              <Label htmlFor="sponsorship_principles">Sponsorship principles</Label>
              <Textarea
                id="sponsorship_principles"
                name="sponsorship_principles"
                defaultValue={initial.sponsorship_principles.join("\n")}
                required
              />
              <FieldDescription>One reviewed public principle per line, up to eight.</FieldDescription>
            </Field>
          </div>
          <div className="rounded-2xl border border-border bg-foreground p-6 text-background" aria-label="Footer preview">
            <p className="eyebrow text-background/65">{initial.footer_eyebrow}</p>
            <p className="mt-4 font-display text-4xl">{initial.footer_heading}</p>
            <p className="mt-4 text-sm text-background/65">Live preview refreshes after save.</p>
          </div>
          <SaveStatus message={message} />
          <div className="flex justify-end">
            <Button type="submit" variant="signal" disabled={pending}>
              {pending ? (
                <LoadingIndicator label="Saving" />
              ) : (
                <>
                  <Save aria-hidden="true" />
                  Save settings
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

export function AssistantSettingsForm({
  csrfToken,
  initial,
}: {
  csrfToken?: string | undefined;
  initial: AssistantSettings;
}) {
  const [enabled, setEnabled] = React.useState(initial.enabled);
  const [message, setMessage] = React.useState<{ ok: boolean; text: string }>();
  const [pending, startTransition] = React.useTransition();
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const suggestions = String(form.get("suggested_questions") ?? "")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    startTransition(async () => {
      try {
        await getBrowserApi(csrfToken).admin.updateAssistantSettings({
          enabled,
          greeting: String(form.get("greeting")),
          suggested_questions: suggestions,
          disclaimer: String(form.get("disclaimer")),
          max_question_length: Number(form.get("max_question_length")),
        });
        setMessage({
          ok: true,
          text: "Assistant settings saved. Public-data isolation remains enforced by the backend.",
        });
      } catch (caught) {
        setMessage({
          ok: false,
          text:
            caught instanceof Error
              ? caught.message
              : "Assistant settings could not be saved.",
        });
      }
    });
  };
  return (
    <div>
      <div>
        <p className="eyebrow">Experience settings</p>
        <h1 className="mt-5 font-display text-5xl leading-none tracking-[-0.055em]">
          Assistant settings
        </h1>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-muted-foreground">
          Control the public entry point and copy. Provider choice and retrieval
          privacy remain server-owned.
        </p>
      </div>
      <Card variant="raised" className="mt-8 max-w-4xl p-6 sm:p-8">
        <form onSubmit={submit} className="grid gap-6">
          <label className="flex items-center justify-between gap-5 rounded-2xl border border-border bg-surface-raised p-4">
            <span className="flex items-start gap-3">
              <Bot className="mt-0.5 size-5 text-primary" aria-hidden="true" />
              <span>
                <span className="block text-sm font-semibold">
                  Public assistant enabled
                </span>
                <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                  When disabled, all public entry points disappear.
                </span>
              </span>
            </span>
            <Switch checked={enabled} onCheckedChange={setEnabled} />
          </label>
          <Field>
            <Label htmlFor="greeting">Greeting</Label>
            <Textarea
              id="greeting"
              name="greeting"
              defaultValue={initial.greeting}
              required
            />
          </Field>
          <Field>
            <Label htmlFor="suggested_questions">Suggested questions</Label>
            <Textarea
              id="suggested_questions"
              name="suggested_questions"
              defaultValue={initial.suggested_questions.join("\n")}
              required
            />
            <FieldDescription>
              One factual, portfolio-scoped question per line.
            </FieldDescription>
          </Field>
          <Field>
            <Label htmlFor="disclaimer">Public disclaimer</Label>
            <Textarea
              id="disclaimer"
              name="disclaimer"
              defaultValue={initial.disclaimer}
              required
            />
          </Field>
          <Field>
            <Label htmlFor="max_question_length">Maximum question length</Label>
            <Input
              id="max_question_length"
              name="max_question_length"
              type="number"
              min={50}
              max={2000}
              defaultValue={initial.max_question_length}
              required
            />
          </Field>
          <SaveStatus message={message} />
          <div className="flex justify-end">
            <Button type="submit" variant="signal" disabled={pending}>
              {pending ? (
                <LoadingIndicator label="Saving" />
              ) : (
                <>
                  <Settings2 aria-hidden="true" />
                  Save assistant settings
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
