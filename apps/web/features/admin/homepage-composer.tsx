"use client";

import type {
  HomepageSection,
  HomepageSectionKind,
} from "@portfolio/api-client";
import {
  MOTION_VARIANTS,
  SECTION_DEFINITIONS,
  SECTION_KINDS,
  SECTION_THEMES,
} from "@portfolio/config";
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Badge,
  Button,
  Card,
  Field,
  FieldDescription,
  Input,
  Label,
  LoadingIndicator,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Switch,
  Textarea,
} from "@portfolio/ui";
import {
  ArrowDown,
  ArrowUp,
  Eye,
  ListOrdered,
  Plus,
  Save,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import * as React from "react";
import { getBrowserApi } from "@/lib/browser-api";

export function HomepageComposer({
  csrfToken,
  initial,
}: {
  csrfToken?: string | undefined;
  initial: HomepageSection[];
}) {
  const [sections, setSections] = React.useState(() =>
    [...initial].sort((a, b) => a.order - b.order),
  );
  const [configurationDrafts, setConfigurationDrafts] = React.useState<
    Record<string, string>
  >(() =>
    Object.fromEntries(
      initial.map((section) => [
        section.id,
        JSON.stringify(section.configuration, null, 2),
      ]),
    ),
  );
  const [newKind, setNewKind] = React.useState<HomepageSectionKind>();
  const [message, setMessage] = React.useState<{
    type: "error" | "success";
    text: string;
  }>();
  const [pending, startTransition] = React.useTransition();
  const availableKinds = SECTION_KINDS.filter(
    (kind) => !sections.some((section) => section.kind === kind),
  );

  const normalize = (items: HomepageSection[]) =>
    items.map((item, order) => ({ ...item, order }));
  const update = (id: string, patch: Partial<HomepageSection>) =>
    setSections((current) =>
      current.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    );
  const updateLimit = (id: string, value: string) =>
    setSections((current) =>
      current.map((item) => {
        if (item.id !== id) return item;
        if (value) return { ...item, data_limit: Number(value) };
        const withoutLimit = { ...item };
        delete withoutLimit.data_limit;
        return withoutLimit;
      }),
    );
  const move = (index: number, direction: -1 | 1) =>
    setSections((current) => {
      const target = index + direction;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      const item = next[index];
      const other = next[target];
      if (!item || !other) return current;
      next[index] = other;
      next[target] = item;
      return normalize(next);
    });
  const add = () => {
    if (!newKind) return;
    const definition = SECTION_DEFINITIONS[newKind];
    const id = `new:${newKind}`;
    setSections((current) =>
      normalize([
        ...current,
        {
          id,
          kind: newKind,
          enabled: true,
          order: current.length,
          variant: definition.defaultVariant,
          animation_variant: "reveal",
          cta_visible: true,
          theme: "default",
          configuration: {},
        },
      ]),
    );
    setConfigurationDrafts((current) => ({ ...current, [id]: "{}" }));
    setNewKind(undefined);
  };
  const save = () => {
    let configured: HomepageSection[];
    try {
      configured = normalize(sections).map((section) => {
        const parsed = JSON.parse(
          configurationDrafts[section.id] ?? "{}",
        ) as unknown;
        if (
          typeof parsed !== "object" ||
          parsed === null ||
          Array.isArray(parsed)
        ) {
          throw new Error(
            `${SECTION_DEFINITIONS[section.kind].label} configuration must be a JSON object.`,
          );
        }
        return { ...section, configuration: parsed as Record<string, unknown> };
      });
    } catch (caught) {
      setMessage({
        type: "error",
        text:
          caught instanceof Error
            ? caught.message
            : "Module configuration must contain valid JSON.",
      });
      return;
    }
    startTransition(async () => {
      try {
        const saved =
          await getBrowserApi(csrfToken).admin.saveHomepageSections(configured);
        const ordered = [...saved].sort((a, b) => a.order - b.order);
        setSections(ordered);
        setConfigurationDrafts(
          Object.fromEntries(
            ordered.map((section) => [
              section.id,
              JSON.stringify(section.configuration, null, 2),
            ]),
          ),
        );
        setMessage({ type: "success", text: "Homepage composition saved." });
      } catch (caught) {
        setMessage({
          type: "error",
          text:
            caught instanceof Error
              ? caught.message
              : "Homepage composition could not be saved.",
        });
      }
    });
  };

  return (
    <div>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="eyebrow">Experience settings</p>
          <h1 className="mt-5 font-display text-5xl leading-none tracking-[-0.055em]">
            Homepage composition
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-muted-foreground">
            Order a closed registry of supported modules, control visibility and
            variants, and tune motion without executing arbitrary component
            names.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline">
            <Link href="/" prefetch={false} target="_blank">
              <Eye aria-hidden="true" />
              Preview site
            </Link>
          </Button>
          <Button variant="signal" onClick={save} disabled={pending}>
            {pending ? (
              <LoadingIndicator label="Saving" />
            ) : (
              <>
                <Save aria-hidden="true" />
                Save composition
              </>
            )}
          </Button>
        </div>
      </div>
      {message && (
        <Alert
          variant={message.type === "success" ? "success" : "destructive"}
          className="mt-6"
        >
          <AlertIcon variant={message.type === "success" ? "success" : "destructive"} />
          <AlertTitle>
            {message.type === "success" ? "Saved" : "Unable to save"}
          </AlertTitle>
          <AlertDescription>{message.text}</AlertDescription>
        </Alert>
      )}
      <div className="mt-8 grid gap-4">
        {sections.map((section, index) => {
          const definition = SECTION_DEFINITIONS[section.kind];
          return (
            <Card key={section.id} variant="raised" className="p-5 sm:p-6">
              <div className="grid gap-6 xl:grid-cols-[auto_minmax(14rem,0.7fr)_minmax(0,1fr)_auto] xl:items-center">
                <div className="flex items-center gap-2">
                  <ListOrdered
                    className="size-5 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <span className="grid size-9 place-items-center rounded-full bg-foreground font-mono text-[0.62rem] text-background">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="font-semibold">{definition.label}</h2>
                    <Badge variant={section.enabled ? "verified" : "muted"}>
                      {section.enabled ? "Visible" : "Hidden"}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">
                    {definition.description}
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                  <Field>
                    <Label htmlFor={`${section.id}-variant`}>Variant</Label>
                    <Select
                      value={section.variant}
                      onValueChange={(variant) =>
                        update(section.id, { variant })
                      }
                    >
                      <SelectTrigger id={`${section.id}-variant`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {definition.variants.map((variant) => (
                          <SelectItem key={variant} value={variant}>
                            {variant}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>
                  <Field>
                    <Label htmlFor={`${section.id}-motion`}>Motion</Label>
                    <Select
                      value={section.animation_variant}
                      onValueChange={(animation_variant) =>
                        update(section.id, {
                          animation_variant:
                            animation_variant as HomepageSection["animation_variant"],
                        })
                      }
                    >
                      <SelectTrigger id={`${section.id}-motion`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {MOTION_VARIANTS.map((variant) => (
                          <SelectItem key={variant} value={variant}>
                            {variant}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>
                  <Field>
                    <Label htmlFor={`${section.id}-theme`}>Theme</Label>
                    <Select
                      value={section.theme}
                      onValueChange={(theme) =>
                        update(section.id, {
                          theme: theme as HomepageSection["theme"],
                        })
                      }
                    >
                      <SelectTrigger id={`${section.id}-theme`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {SECTION_THEMES.map((theme) => (
                          <SelectItem key={theme} value={theme}>
                            {theme}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>
                  {definition.supportsLimit && (
                    <Field>
                      <Label htmlFor={`${section.id}-limit`}>Item limit</Label>
                      <Input
                        id={`${section.id}-limit`}
                        type="number"
                        min={1}
                        value={section.data_limit ?? ""}
                        onChange={(event) =>
                          updateLimit(section.id, event.target.value)
                        }
                      />
                    </Field>
                  )}
                  <div className="flex items-end pb-3">
                    <label className="flex items-center gap-3 text-sm font-semibold">
                      <Switch
                        checked={section.cta_visible}
                        onCheckedChange={(cta_visible) =>
                          update(section.id, { cta_visible })
                        }
                      />
                      Show CTA
                    </label>
                  </div>
                </div>
                <div className="flex items-center justify-end gap-1">
                  <label className="mr-2 inline-flex items-center gap-2 text-sm font-semibold">
                    <Switch
                      checked={section.enabled}
                      onCheckedChange={(enabled) =>
                        update(section.id, { enabled })
                      }
                      aria-label={`Show ${definition.label}`}
                    />
                    <span className="hidden 2xl:inline">Visible</span>
                  </label>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => move(index, -1)}
                    disabled={index === 0}
                    aria-label={`Move ${definition.label} up`}
                  >
                    <ArrowUp aria-hidden="true" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => move(index, 1)}
                    disabled={index === sections.length - 1}
                    aria-label={`Move ${definition.label} down`}
                  >
                    <ArrowDown aria-hidden="true" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() =>
                      setSections((current) =>
                        normalize(
                          current.filter((item) => item.id !== section.id),
                        ),
                      )
                    }
                    aria-label={`Remove ${definition.label} from homepage`}
                  >
                    <Trash2 aria-hidden="true" />
                  </Button>
                </div>
              </div>
              <Field className="mt-6 border-t border-border pt-5">
                <Label htmlFor={`${section.id}-heading`}>
                  Custom heading{" "}
                  <span className="text-muted-foreground">(optional)</span>
                </Label>
                <Input
                  id={`${section.id}-heading`}
                  value={section.custom_heading ?? ""}
                  onChange={(event) =>
                    update(section.id, {
                      custom_heading: event.target.value || undefined,
                    })
                  }
                />
                <FieldDescription>
                  Leave empty to use the module&apos;s content-owned default heading.
                </FieldDescription>
              </Field>
              {section.kind === "editorial" && (
                <Field className="mt-5">
                  <Label htmlFor={`${section.id}-configuration`}>
                    Curated editorial blocks
                  </Label>
                  <Textarea
                    id={`${section.id}-configuration`}
                    value={configurationDrafts[section.id] ?? "{}"}
                    onChange={(event) =>
                      setConfigurationDrafts((current) => ({
                        ...current,
                        [section.id]: event.target.value,
                      }))
                    }
                    className="min-h-52 font-mono text-xs"
                    spellCheck={false}
                    aria-describedby={`${section.id}-configuration-description`}
                  />
                  <FieldDescription
                    id={`${section.id}-configuration-description`}
                  >
                    Use a JSON object with a blocks array. Each block requires a
                    title and body; id, eyebrow, link, and media are optional.
                  </FieldDescription>
                </Field>
              )}
            </Card>
          );
        })}
      </div>
      {availableKinds.length > 0 && (
        <Card className="mt-5 flex flex-col gap-4 border-dashed p-5 sm:flex-row sm:items-end">
          <Field className="flex-1">
            <Label htmlFor="new-section">Add a supported module</Label>
            <Select
              value={newKind ?? ""}
              onValueChange={(value) =>
                setNewKind(value as HomepageSectionKind)
              }
            >
              <SelectTrigger id="new-section">
                <SelectValue placeholder="Choose section type" />
              </SelectTrigger>
              <SelectContent>
                {availableKinds.map((kind) => (
                  <SelectItem key={kind} value={kind}>
                    {SECTION_DEFINITIONS[kind].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Button variant="outline" onClick={add} disabled={!newKind}>
            <Plus aria-hidden="true" />
            Add module
          </Button>
        </Card>
      )}
    </div>
  );
}
