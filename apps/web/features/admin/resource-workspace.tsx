"use client";

import type {
  AdminListResponse,
  AdminProjectMedia,
  AdminRepositoryMetadata,
  AdminRecord,
  AdminResource,
} from "@portfolio/api-client";
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Field,
  FieldDescription,
  FieldError,
  Input,
  Label,
  LoadingIndicator,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Textarea,
} from "@portfolio/ui";
import {
  Archive,
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  FilePlus2,
  Pencil,
  Search,
  RefreshCw,
  Upload,
  X,
} from "lucide-react";
import * as React from "react";
import { getBrowserApi } from "@/lib/browser-api";
import type {
  AdminFieldDefinition,
  AdminResourceDefinition,
} from "./resource-definitions";

type ResourceWorkspaceProps = {
  resource: AdminResource;
  definition: AdminResourceDefinition;
  initial: AdminListResponse;
  role: "owner" | "editor";
  csrfToken?: string | undefined;
};

const OWNER_CONTROLLED_FIELDS = new Set([
  "featured_rank",
  "is_approved",
  "is_visible",
  "noindex",
  "repository_metadata_refresh_enabled",
]);

const adminDateFormatter = new Intl.DateTimeFormat("en", {
  year: "numeric",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

const adminDateTimeFormatter = new Intl.DateTimeFormat("en", {
  year: "numeric",
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZone: "UTC",
  timeZoneName: "short",
});

function displayValue(
  value: unknown,
  field: AdminFieldDefinition,
): string | number | readonly string[] | undefined {
  if (value === undefined || value === null) return undefined;
  if (field.type === "json") return JSON.stringify(value, null, 2);
  if (field.type === "date" && typeof value === "string")
    return value.slice(0, 10);
  if (field.type === "datetime" && typeof value === "string")
    return value.slice(0, 16);
  if (typeof value === "string" || typeof value === "number") return value;
  return String(value);
}

type RelationOption = { id: string; label: string; unavailable?: boolean };

function relationLabel(value: Record<string, unknown>, fallback: string) {
  for (const key of ["name", "title", "organization", "original_filename", "label"]) {
    if (typeof value[key] === "string" && value[key]) return String(value[key]);
  }
  return fallback;
}

export function initialRelationOptions(
  field: AdminFieldDefinition,
  record?: AdminRecord,
): RelationOption[] {
  if (!record) return [];
  const direct = record.data[field.key];
  const nested = field.relation?.selectedDataKey
    ? record.data[field.relation.selectedDataKey]
    : undefined;
  const values = Array.isArray(nested) ? nested : nested ? [nested] : [];
  const options: RelationOption[] = values.flatMap((value) => {
    if (typeof value !== "object" || value === null || !("id" in value)) return [];
    const id = String(value.id);
    const relationRecord = value as Record<string, unknown>;
    return [{
      id,
      label: relationLabel(relationRecord, id),
      unavailable:
        relationRecord.status === "archived" ||
        relationRecord.archived_at != null ||
        relationRecord.is_visible === false,
    }];
  });
  const directIds = Array.isArray(direct)
    ? direct.map(String)
    : typeof direct === "string"
      ? [direct]
      : [];
  for (const id of directIds) {
    if (!options.some((option) => option.id === id))
      options.push({ id, label: id, unavailable: true });
  }
  return options;
}

export function RelationField({
  csrfToken,
  field,
  record,
}: {
  csrfToken?: string | undefined;
  field: AdminFieldDefinition;
  record?: AdminRecord | undefined;
}) {
  const relation = field.relation;
  if (!relation) throw new Error(`Relation field ${field.key} has no relation definition.`);
  const multiple = field.type === "relation-many";
  const [selected, setSelected] = React.useState<RelationOption[]>(() =>
    initialRelationOptions(field, record),
  );
  const [options, setOptions] = React.useState<RelationOption[]>([]);
  const [query, setQuery] = React.useState("");
  const [activeQuery, setActiveQuery] = React.useState("");
  const [page, setPage] = React.useState(1);
  const [hasMore, setHasMore] = React.useState(false);
  const [error, setError] = React.useState<string>();
  const [loading, startTransition] = React.useTransition();
  const searchId = `${field.key}-relation-search`;

  const load = React.useCallback(
    (nextPage: number, append = false) => {
      startTransition(async () => {
        try {
          const result = await getBrowserApi(csrfToken).admin.list(relation.resource, {
            page: nextPage,
            pageSize: 25,
            ...(activeQuery ? { search: activeQuery } : {}),
            ...relation.filters,
          });
          const incoming = result.items
            .filter((item) => item.status !== "archived")
            .map((item) => ({ id: item.id, label: item.label }));
          setOptions((current) => {
            const values = append ? [...current, ...incoming] : incoming;
            return [...new Map(values.map((item) => [item.id, item])).values()];
          });
          setPage(nextPage);
          setHasMore(nextPage < result.page_info.total_pages);
          setError(undefined);
        } catch (caught) {
          setError(caught instanceof Error ? caught.message : "Related records could not be loaded.");
        }
      });
    },
    [activeQuery, csrfToken, relation.filters, relation.resource],
  );

  React.useEffect(() => {
    load(1);
  }, [load]);

  const merged = [...new Map([...selected, ...options].map((item) => [item.id, item])).values()];
  const selectedIds = new Set(selected.map((item) => item.id));
  const toggle = (option: RelationOption) => {
    setSelected((current) => {
      if (!multiple) return current.some((item) => item.id === option.id) ? [] : [option];
      return current.some((item) => item.id === option.id)
        ? current.filter((item) => item.id !== option.id)
        : [...current, option];
    });
  };
  const search = () => {
    const normalized = query.trim();
    if (normalized === activeQuery) load(1);
    else setActiveQuery(normalized);
  };

  return (
    <Field className="sm:col-span-2">
      <fieldset className="grid gap-3 rounded-2xl border border-border p-4">
        <legend className="px-2 text-sm font-semibold">
          {field.label}{field.required && <span className="text-destructive"> *</span>}
        </legend>
        {selected.map((item) => (
          <input key={item.id} type="hidden" name={field.key} value={item.id} />
        ))}
        <div className="flex gap-2">
          <Input
            id={searchId}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={`Search ${field.label.toLowerCase()}`}
            aria-label={`Search ${field.label.toLowerCase()}`}
          />
          <Button type="button" variant="outline" onClick={search} disabled={loading}>
            <Search aria-hidden="true" /> Search
          </Button>
        </div>
        {selected.length > 0 && (
          <div className="flex flex-wrap gap-2" aria-label={`Selected ${field.label.toLowerCase()}`}>
            {selected.map((item) => (
              <Badge key={item.id} variant="outline" className="gap-2">
                {item.label}{item.unavailable ? " (unavailable)" : ""}
                <button type="button" onClick={() => toggle(item)} aria-label={`Remove ${item.label}`}>
                  <X className="size-3" aria-hidden="true" />
                </button>
              </Badge>
            ))}
          </div>
        )}
        <div className="grid max-h-56 gap-1 overflow-y-auto" role={multiple ? "group" : "radiogroup"}>
          {merged.map((option) => {
            const checked = selectedIds.has(option.id);
            return (
              <label key={option.id} className="flex min-h-11 cursor-pointer items-center gap-3 rounded-xl px-3 py-2 hover:bg-muted">
                <input
                  type={multiple ? "checkbox" : "radio"}
                  checked={checked}
                  onChange={() => toggle(option)}
                  className="size-4 accent-[var(--primary)]"
                />
                <span className="text-sm">{option.label}</span>
              </label>
            );
          })}
          {!loading && merged.length === 0 && <p className="p-3 text-sm text-muted-foreground">No matching records.</p>}
        </div>
        {hasMore && (
          <Button type="button" variant="ghost" onClick={() => load(page + 1, true)} disabled={loading}>
            Load more
          </Button>
        )}
        {loading && <LoadingIndicator label="Loading related records" />}
        {error && <FieldError role="alert">{error}</FieldError>}
        {field.description && <FieldDescription>{field.description}</FieldDescription>}
      </fieldset>
    </Field>
  );
}

function RecordField({
  csrfToken,
  field,
  record,
}: {
  csrfToken?: string | undefined;
  field: AdminFieldDefinition;
  record?: AdminRecord | undefined;
}) {
  if (field.type === "relation-one" || field.type === "relation-many") {
    return (
      <RelationField
        key={`${field.key}:${record?.id ?? "new"}`}
        csrfToken={csrfToken}
        field={field}
        record={record}
      />
    );
  }
  const value = displayValue(record?.data[field.key], field);
  const describedBy = `${field.key}-description`;
  if (field.type === "switch") {
    return (
      <Field>
        <label className="flex min-h-12 cursor-pointer items-center justify-between gap-5 rounded-2xl border border-border bg-surface-raised px-4 py-3 text-sm font-semibold">
          <span>{field.label}</span>
          <input
            type="checkbox"
            name={field.key}
            defaultChecked={
              record
                ? Boolean(record.data[field.key])
                : Boolean(field.defaultChecked)
            }
            disabled={field.readOnly}
            className="size-4 accent-[var(--primary)]"
          />
        </label>
        {field.description && (
          <FieldDescription id={describedBy}>
            {field.description}
          </FieldDescription>
        )}
      </Field>
    );
  }
  if (field.type === "select") {
    return (
      <Field>
        <Label htmlFor={field.key}>
          {field.label}
          {field.required && <span className="text-destructive"> *</span>}
        </Label>
        <Select
          name={field.key}
          defaultValue={
            typeof value === "string"
              ? value
              : (field.options?.[0]?.value ?? "")
          }
          disabled={Boolean(field.readOnly)}
          required={Boolean(field.required)}
        >
          <SelectTrigger
            id={field.key}
            aria-describedby={field.description ? describedBy : undefined}
          >
            <SelectValue placeholder={`Choose ${field.label.toLowerCase()}`} />
          </SelectTrigger>
          <SelectContent>
            {field.options?.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {field.description && (
          <FieldDescription id={describedBy}>
            {field.description}
          </FieldDescription>
        )}
      </Field>
    );
  }
  if (field.type === "textarea" || field.type === "json") {
    return (
      <Field className={field.type === "json" ? "sm:col-span-2" : undefined}>
        <Label htmlFor={field.key}>
          {field.label}
          {field.required && <span className="text-destructive"> *</span>}
        </Label>
        <Textarea
          id={field.key}
          name={field.key}
          defaultValue={value}
          required={field.required}
          readOnly={field.readOnly}
          placeholder={field.placeholder}
          aria-describedby={field.description ? describedBy : undefined}
          className={
            field.type === "json" ? "min-h-52 font-mono text-xs" : undefined
          }
        />
        {field.description && (
          <FieldDescription id={describedBy}>
            {field.description}
          </FieldDescription>
        )}
      </Field>
    );
  }
  const inputType = field.type === "slug" ? "text" : field.type;
  return (
    <Field>
      <Label htmlFor={field.key}>
        {field.label}
        {field.required && <span className="text-destructive"> *</span>}
      </Label>
      <Input
        id={field.key}
        name={field.key}
        type={inputType}
        defaultValue={value}
        required={field.required}
        readOnly={field.readOnly}
        min={field.min}
        max={field.max}
        step={field.type === "number" ? "any" : undefined}
        placeholder={field.placeholder}
        aria-describedby={field.description ? describedBy : undefined}
      />
      {field.description && (
        <FieldDescription id={describedBy}>
          {field.description}
        </FieldDescription>
      )}
    </Field>
  );
}

export function parseRecordForm(
  form: HTMLFormElement,
  fields: readonly AdminFieldDefinition[],
): { data?: Record<string, unknown>; error?: string } {
  const formData = new FormData(form);
  const data: Record<string, unknown> = {};
  for (const field of fields) {
    if (field.readOnly) continue;
    if (field.type === "relation-many") {
      data[field.key] = formData.getAll(field.key).map(String);
      continue;
    }
    if (field.type === "relation-one") {
      const selected = formData.get(field.key);
      data[field.key] = selected ? String(selected) : null;
      if (field.required && !selected) return { error: `${field.label} is required.` };
      continue;
    }
    if (field.type === "switch") {
      data[field.key] = formData.get(field.key) === "on";
      continue;
    }
    const raw = String(formData.get(field.key) ?? "").trim();
    if (!raw && field.required) return { error: `${field.label} is required.` };
    if (!raw) {
      data[field.key] = field.type === "json" ? [] : null;
      continue;
    }
    if (field.type === "number") {
      const number = Number(raw);
      if (!Number.isFinite(number))
        return { error: `${field.label} must be a number.` };
      data[field.key] = number;
      continue;
    }
    if (field.type === "json") {
      try {
        data[field.key] = JSON.parse(raw) as unknown;
      } catch {
        return { error: `${field.label} must contain valid JSON.` };
      }
      continue;
    }
    data[field.key] = raw;
  }
  return { data };
}

function projectMediaFromRecord(record: AdminRecord): AdminProjectMedia[] {
  const media = record.data.media;
  if (!Array.isArray(media)) return [];
  return media.flatMap((value) => {
    if (
      typeof value !== "object" ||
      value === null ||
      !("id" in value) ||
      !("project_id" in value) ||
      !("media_type" in value) ||
      !("alt_text" in value)
    )
      return [];
    return [value as AdminProjectMedia];
  });
}

function repositoryMetadataFromRecord(
  record: AdminRecord,
): AdminRepositoryMetadata | undefined {
  const value = record.data.repository_metadata;
  if (!value || typeof value !== "object" || !("status" in value)) return undefined;
  return value as AdminRepositoryMetadata;
}

function ProjectMediaManager({
  canRefreshRepository,
  csrfToken,
  onChanged,
  project,
}: {
  canRefreshRepository: boolean;
  csrfToken?: string | undefined;
  onChanged: () => Promise<void>;
  project: AdminRecord;
}) {
  const [media, setMedia] = React.useState(() =>
    projectMediaFromRecord(project),
  );
  const [repositoryMetadata, setRepositoryMetadata] = React.useState(() =>
    repositoryMetadataFromRecord(project),
  );
  const [error, setError] = React.useState<string>();
  const [pending, startTransition] = React.useTransition();
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const file = form.get("project_media_file");
    const altText = String(form.get("project_media_alt") ?? "").trim();
    const isDecorative = form.get("project_media_decorative") === "on";
    if (!(file instanceof File) || file.size === 0) {
      setError("Choose a project media file.");
      return;
    }
    if (!altText && !isDecorative) {
      setError("Alternative text is required for project media.");
      return;
    }
    if (altText && isDecorative) {
      setError("Decorative images must use empty alternative text.");
      return;
    }
    if (isDecorative && !file.type.startsWith("image/")) {
      setError("Only images can be marked decorative.");
      return;
    }
    startTransition(async () => {
      try {
        const uploaded = await getBrowserApi(
          csrfToken,
        ).admin.uploadProjectMedia(file, {
          projectId: project.id,
          altText,
          isDecorative,
          caption: String(form.get("project_media_caption") ?? "").trim(),
          sortOrder: Number(form.get("project_media_order") ?? media.length),
        });
        setMedia((current) => [...current, uploaded]);
        setError(undefined);
        formElement.reset();
        await onChanged();
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : "Project media upload failed.",
        );
      }
    });
  };
  const archive = (mediaId: string) =>
    startTransition(async () => {
      try {
        await getBrowserApi(csrfToken).admin.archiveProjectMedia(mediaId);
        setMedia((current) => current.filter((item) => item.id !== mediaId));
        setError(undefined);
        await onChanged();
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : "Project media could not be archived.",
        );
      }
    });
  const refreshRepository = (force: boolean) =>
    startTransition(async () => {
      try {
        const refreshed = await getBrowserApi(
          csrfToken,
        ).admin.refreshRepositoryMetadata(project.id, force);
        setRepositoryMetadata(refreshed);
        setError(undefined);
        await onChanged();
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : "Repository metadata could not be refreshed.",
        );
      }
    });

  return (
    <section className="rounded-2xl border border-border bg-surface-raised p-5">
      <div>
        <h3 className="font-semibold">Project media</h3>
        <p className="mt-1 text-xs leading-5 text-muted-foreground">
          Upload validated files to managed storage or retain existing external
          media.
        </p>
      </div>
      {canRefreshRepository && project.data.repository_metadata_refresh_enabled === true && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-border bg-muted/40 p-4">
          <div className="min-w-0 text-sm">
            <p className="font-semibold">Repository source-of-record</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {repositoryMetadata
                ? `${repositoryMetadata.status}${repositoryMetadata.repository_identity ? ` · ${repositoryMetadata.repository_identity}` : ""}${repositoryMetadata.last_error_code ? ` · ${repositoryMetadata.last_error_code}` : ""}`
                : "No snapshot has been fetched."}
            </p>
            {repositoryMetadata?.fetched_at && (
              <time className="mt-1 block font-mono text-[0.62rem] text-muted-foreground" dateTime={repositoryMetadata.fetched_at}>
                Last source read {new Date(repositoryMetadata.fetched_at).toLocaleString("en", { timeZone: "UTC" })} UTC
              </time>
            )}
          </div>
          <Button type="button" variant="outline" onClick={() => refreshRepository(Boolean(repositoryMetadata))} disabled={pending}>
            <RefreshCw aria-hidden="true" />
            {repositoryMetadata ? "Refresh again" : "Fetch signals"}
          </Button>
        </div>
      )}
      {media.length > 0 && (
        <ul className="mt-4 grid gap-2">
          {media.map((item) => (
            <li
              key={item.id}
              className="flex min-h-12 items-center justify-between gap-4 rounded-xl border border-border px-3 py-2"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">
                  {item.original_filename ?? item.alt_text}
                </p>
                <p className="mt-1 font-mono text-[0.62rem] text-muted-foreground">
                  {item.external_url ? "External source" : "Managed storage"} ·{" "}
                  {item.media_type}
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                onClick={() => archive(item.id)}
                disabled={pending}
                aria-label={`Archive ${item.original_filename ?? item.alt_text}`}
              >
                <Archive aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={submit} className="mt-5 grid gap-4 sm:grid-cols-2">
        <Field className="sm:col-span-2">
          <Label htmlFor={`project-media-file-${project.id}`}>Media file</Label>
          <Input
            id={`project-media-file-${project.id}`}
            name="project_media_file"
            type="file"
            accept="image/jpeg,image/png,image/webp,image/avif,video/mp4,video/webm,application/pdf"
            required
          />
        </Field>
        <Field>
          <Label htmlFor={`project-media-alt-${project.id}`}>
            Alternative text
          </Label>
          <Input
            id={`project-media-alt-${project.id}`}
            name="project_media_alt"
          />
        </Field>
        <Field className="self-end">
          <label className="flex min-h-10 items-center gap-3 rounded-xl border border-border px-3 text-sm">
            <input type="checkbox" name="project_media_decorative" className="size-4 accent-primary" />
            Decorative image (empty alternative text)
          </label>
        </Field>
        <Field>
          <Label htmlFor={`project-media-order-${project.id}`}>
            Display order
          </Label>
          <Input
            id={`project-media-order-${project.id}`}
            name="project_media_order"
            type="number"
            min={0}
            defaultValue={media.length}
          />
        </Field>
        <Field className="sm:col-span-2">
          <Label htmlFor={`project-media-caption-${project.id}`}>
            Caption <span className="text-muted-foreground">(optional)</span>
          </Label>
          <Input
            id={`project-media-caption-${project.id}`}
            name="project_media_caption"
          />
        </Field>
        {error && <FieldError className="sm:col-span-2">{error}</FieldError>}
        <div className="flex justify-end sm:col-span-2">
          <Button type="submit" variant="outline" disabled={pending}>
            {pending ? (
              <LoadingIndicator label="Uploading" />
            ) : (
              <>
                <Upload aria-hidden="true" />
                Upload project media
              </>
            )}
          </Button>
        </div>
      </form>
    </section>
  );
}

function EditorDialog({
  canManageSensitive,
  definition,
  onSaved,
  open,
  record,
  resource,
  setOpen,
  csrfToken,
}: {
  canManageSensitive: boolean;
  definition: AdminResourceDefinition;
  onSaved: () => Promise<void>;
  open: boolean;
  record?: AdminRecord | undefined;
  resource: AdminResource;
  setOpen: (open: boolean) => void;
  csrfToken?: string | undefined;
}) {
  const fields = canManageSensitive
    ? definition.fields
    : definition.fields.filter((field) => !OWNER_CONTROLLED_FIELDS.has(field.key));
  const [error, setError] = React.useState<string>();
  const [pending, startTransition] = React.useTransition();
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = parseRecordForm(event.currentTarget, fields);
    if (!parsed.data) {
      setError(parsed.error ?? "Review the form.");
      return;
    }
    const nextData = parsed.data;
    startTransition(async () => {
      try {
        const api = getBrowserApi(csrfToken).admin;
        if (record) await api.update(resource, record.id, nextData);
        else await api.create(resource, nextData);
        await onSaved();
        setOpen(false);
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : "The record could not be saved.",
        );
      }
    });
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            {record
              ? `Edit ${definition.singular}`
              : `New ${definition.singular}`}
          </DialogTitle>
          <DialogDescription>{definition.description}</DialogDescription>
        </DialogHeader>
        {resource === "projects" && record && (
          <ProjectMediaManager
            canRefreshRepository={canManageSensitive}
            csrfToken={csrfToken}
            onChanged={onSaved}
            project={record}
          />
        )}
        <form onSubmit={submit} className="grid gap-6">
          <div className="grid gap-5 sm:grid-cols-2">
            {fields.map((field) => (
              <RecordField key={field.key} csrfToken={csrfToken} field={field} record={record} />
            ))}
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertIcon variant="destructive" />
              <AlertTitle>Unable to save</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="signal" disabled={pending}>
              {pending ? (
                <LoadingIndicator label="Saving" />
              ) : (
                <>
                  <Check aria-hidden="true" />
                  Save {definition.singular}
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function MediaUpload({
  csrfToken,
  onUploaded,
}: {
  csrfToken?: string | undefined;
  onUploaded: () => Promise<void>;
}) {
  const [open, setOpen] = React.useState(false);
  const [error, setError] = React.useState<string>();
  const [pending, startTransition] = React.useTransition();
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    if (!(file instanceof File) || file.size === 0) {
      setError("Choose a file to upload.");
      return;
    }
    startTransition(async () => {
      try {
        await getBrowserApi(csrfToken).admin.uploadMedia(file, {
          alt: String(form.get("alt") ?? ""),
          caption: String(form.get("caption") ?? "").trim(),
          isDecorative: form.get("decorative") === "on",
        });
        await onUploaded();
        setOpen(false);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Upload failed.");
      }
    });
  };
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button asChild={false} variant="signal" onClick={() => setOpen(true)}>
        <Upload aria-hidden="true" />
        Upload media
      </Button>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload managed media</DialogTitle>
          <DialogDescription>
            Server validation controls file type, size, storage, and safe public
            URLs.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="grid gap-5">
          <Field>
            <Label htmlFor="media-file">File</Label>
            <Input id="media-file" name="file" type="file" required />
          </Field>
          <Field>
            <Label htmlFor="media-alt">Alternative text</Label>
            <Textarea
              id="media-alt"
              name="alt"
              placeholder="Describe the image’s purpose and content…"
            />
            <FieldDescription>
              Documents and decorative assets may use an empty alternative only
              when appropriate.
            </FieldDescription>
          </Field>
          <Field>
            <Label htmlFor="media-caption">Accessible caption</Label>
            <Input id="media-caption" name="caption" />
            <FieldDescription>
              Required for informative documents or videos when alternative text is empty.
            </FieldDescription>
          </Field>
          <Field>
            <label className="flex min-h-10 items-center gap-3 rounded-xl border border-border px-3 text-sm">
              <input type="checkbox" name="decorative" className="size-4 accent-primary" />
              Decorative image (empty alternative text)
            </label>
          </Field>
          {error && <FieldError>{error}</FieldError>}
          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => setOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" variant="signal" disabled={pending}>
              {pending ? <LoadingIndicator label="Uploading" /> : "Upload"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function FeaturedOrderManager({
  csrfToken,
  onChanged,
}: {
  csrfToken?: string | undefined;
  onChanged: () => Promise<void>;
}) {
  const [projects, setProjects] = React.useState<AdminRecord[]>([]);
  const [limit, setLimit] = React.useState(5);
  const [query, setQuery] = React.useState("");
  const [candidates, setCandidates] = React.useState<AdminRecord[]>([]);
  const [message, setMessage] = React.useState<string>();
  const [error, setError] = React.useState<string>();
  const [pending, startTransition] = React.useTransition();

  const load = React.useCallback(() => {
    startTransition(async () => {
      try {
        const state = await getBrowserApi(csrfToken).admin.getFeaturedProjectOrder();
        setLimit(state.limit);
        setProjects(state.projects);
        setError(undefined);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Featured order could not be loaded.");
      }
    });
  }, [csrfToken]);

  React.useEffect(() => load(), [load]);

  const search = () => {
    startTransition(async () => {
      try {
        const result = await getBrowserApi(csrfToken).admin.list("projects", {
          page: 1,
          pageSize: 25,
          status: "published",
          ...(query.trim() ? { search: query.trim() } : {}),
        });
        setCandidates(
          result.items.filter(
            (item) => item.data.is_visible === true && !projects.some(({ id }) => id === item.id),
          ),
        );
        setError(undefined);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Projects could not be searched.");
      }
    });
  };

  const move = (index: number, direction: -1 | 1) => {
    const destination = index + direction;
    if (destination < 0 || destination >= projects.length) return;
    setProjects((current) => {
      const next = [...current];
      [next[index], next[destination]] = [next[destination]!, next[index]!];
      return next;
    });
    setMessage(undefined);
  };

  const save = () => {
    startTransition(async () => {
      try {
        const saved = await getBrowserApi(csrfToken).admin.replaceFeaturedProjectOrder(
          projects.map(({ id }) => id),
        );
        setProjects(saved);
        setMessage("Featured order saved atomically.");
        setError(undefined);
        await onChanged();
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : "Featured order changed concurrently. Reload and retry.",
        );
      }
    });
  };

  return (
    <section
      className="mt-8 grid gap-5 rounded-[var(--radius-card)] border border-border-strong bg-surface-raised p-5"
      aria-labelledby="featured-order-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="eyebrow">Homepage presentation</p>
          <h2 id="featured-order-heading" className="mt-2 text-xl font-semibold">
            Featured project slots
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {projects.length} of {limit} active public slots occupied. Changes save as one
            transaction.
          </p>
        </div>
        <Button type="button" variant="signal" onClick={save} disabled={pending}>
          {pending ? <LoadingIndicator label="Saving order" /> : "Save order"}
        </Button>
      </div>

      <ol className="grid gap-2">
        {projects.map((project, index) => (
          <li
            key={project.id}
            className="flex min-h-14 flex-wrap items-center gap-3 rounded-xl border border-border px-3 py-2"
          >
            <Badge variant="outline">Slot {index + 1}</Badge>
            <span className="min-w-0 flex-1 truncate text-sm font-semibold">{project.label}</span>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              onClick={() => move(index, -1)}
              disabled={index === 0 || pending}
              aria-label={`Move ${project.label} up`}
            >
              <ChevronUp aria-hidden="true" />
            </Button>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              onClick={() => move(index, 1)}
              disabled={index === projects.length - 1 || pending}
              aria-label={`Move ${project.label} down`}
            >
              <ChevronDown aria-hidden="true" />
            </Button>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              onClick={() => setProjects((current) => current.filter(({ id }) => id !== project.id))}
              disabled={pending}
              aria-label={`Remove ${project.label} from featured slots`}
            >
              <X aria-hidden="true" />
            </Button>
          </li>
        ))}
        {projects.length === 0 && (
          <li className="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground">
            No occupied slots. Search for a published, visible project to add one.
          </li>
        )}
      </ol>

      {projects.length < limit && (
        <div className="grid gap-3">
          <div className="flex gap-2">
            <Input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search published projects"
              aria-label="Search projects for a featured slot"
            />
            <Button type="button" variant="outline" onClick={search} disabled={pending}>
              <Search aria-hidden="true" /> Search
            </Button>
          </div>
          {candidates.length > 0 && (
            <div className="flex flex-wrap gap-2" aria-label="Featured project candidates">
              {candidates.map((candidate) => (
                <Button
                  key={candidate.id}
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setProjects((current) => [...current, candidate].slice(0, limit));
                    setCandidates((current) => current.filter(({ id }) => id !== candidate.id));
                    setMessage(undefined);
                  }}
                >
                  Add {candidate.label}
                </Button>
              ))}
            </div>
          )}
        </div>
      )}
      {message && <p role="status" className="text-sm text-success">{message}</p>}
      {error && <FieldError role="alert">{error}</FieldError>}
    </section>
  );
}


export function ResourceWorkspace({
  csrfToken,
  definition,
  initial,
  role,
  resource,
}: ResourceWorkspaceProps) {
  const canManageSensitive = role === "owner";
  const [data, setData] = React.useState(initial);
  const [query, setQuery] = React.useState("");
  const [status, setStatus] = React.useState("all");
  const [editorOpen, setEditorOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<AdminRecord>();
  const [deleting, setDeleting] = React.useState<AdminRecord>();
  const [error, setError] = React.useState<string>();
  const [pending, startTransition] = React.useTransition();

  const refresh = React.useCallback(
    async (page = data.page_info.page) => {
      try {
        const next = await getBrowserApi(csrfToken).admin.list(resource, {
          page,
          pageSize: data.page_info.page_size,
          ...(query ? { search: query } : {}),
          ...(status !== "all" ? { status } : {}),
        });
        setData(next);
        setError(undefined);
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to refresh records.",
        );
      }
    },
    [
      csrfToken,
      data.page_info.page,
      data.page_info.page_size,
      query,
      resource,
      status,
    ],
  );

  const publish = (
    record: AdminRecord,
    nextStatus: "draft" | "published" | "hidden" | "archived",
  ) =>
    startTransition(async () => {
      try {
        await getBrowserApi(csrfToken).admin.publish(
          resource,
          record.id,
          nextStatus,
        );
        await refresh();
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : "Publication state could not be changed.",
        );
      }
    });

  const remove = () => {
    if (!deleting) return;
    startTransition(async () => {
      try {
        await getBrowserApi(csrfToken).admin.remove(resource, deleting.id);
        setDeleting(undefined);
        await refresh();
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : "The record could not be deleted.",
        );
      }
    });
  };

  return (
    <div>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="eyebrow">Managed content</p>
          <h1 className="mt-5 font-display text-5xl leading-none tracking-[-0.055em]">
            {definition.label}
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-muted-foreground">
            {definition.description}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {resource === "media" && (
            <MediaUpload csrfToken={csrfToken} onUploaded={refresh} />
          )}
          {definition.createEnabled && resource !== "media" && !(resource === "profile" && data.page_info.total > 0) && (
            <Button
              variant="signal"
              onClick={() => {
                setEditing(undefined);
                setEditorOpen(true);
              }}
            >
              <FilePlus2 aria-hidden="true" />
              New {definition.singular}
            </Button>
          )}
        </div>
      </div>
      {resource === "projects" && canManageSensitive && (
        <FeaturedOrderManager csrfToken={csrfToken} onChanged={refresh} />
      )}
      <div className="mt-8 grid gap-3 rounded-[var(--radius-card)] border border-border-strong bg-surface-raised p-4 sm:grid-cols-[1fr_13rem_auto] sm:items-end">
        <Field>
          <Label htmlFor="admin-search">Search</Label>
          <div className="relative">
            <Search
              className="absolute left-4 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              id="admin-search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="pl-11"
              placeholder={`Search ${definition.label.toLowerCase()}…`}
            />
          </div>
        </Field>
        {definition.supportsPublication ? (
          <Field>
            <Label htmlFor="admin-status">Publication</Label>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger id="admin-status">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All states</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
                <SelectItem value="published">Published</SelectItem>
                <SelectItem value="hidden">Hidden</SelectItem>
                <SelectItem value="archived">Archived</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        ) : (
          <span />
        )}
        <Button
          variant="outline"
          onClick={() => startTransition(() => refresh(1))}
          disabled={pending}
        >
          Apply
        </Button>
      </div>
      {error && (
        <Alert variant="destructive" className="mt-5">
          <AlertIcon variant="destructive" />
          <AlertTitle>CMS request failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="mt-6">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-48 sm:min-w-64 lg:min-w-80">Record</TableHead>
              <TableHead className="hidden sm:table-cell">Status</TableHead>
              <TableHead className="hidden min-w-40 md:table-cell">Updated</TableHead>
              <TableHead className="sticky right-0 z-10 bg-surface-raised px-2 text-right shadow-[-12px_0_20px_-20px_var(--shadow-ink)] sm:px-4">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((record) => (
              <TableRow key={record.id}>
                <TableCell>
                  <div className="max-w-xl">
                    <p className="font-semibold">{record.label}</p>
                    {record.slug && (
                      <p className="mt-1 font-mono text-[0.62rem] text-muted-foreground">
                        /{record.slug}
                      </p>
                    )}
                    <div className="mt-3 sm:hidden">
                      {record.status ? (
                        <Badge
                          variant={
                            record.status === "published"
                              ? "verified"
                              : record.status === "draft"
                                ? "signal"
                                : "muted"
                          }
                        >
                          {record.status}
                        </Badge>
                      ) : (
                        <Badge variant="muted">managed</Badge>
                      )}
                    </div>
                    <p className="mt-2 font-mono text-[0.58rem] uppercase tracking-[0.08em] text-muted-foreground md:hidden">
                      Updated {adminDateFormatter.format(new Date(record.updated_at))}
                    </p>
                  </div>
                </TableCell>
                <TableCell className="hidden sm:table-cell">
                  {record.status ? (
                    <Badge
                      variant={
                        record.status === "published"
                          ? "verified"
                          : record.status === "draft"
                            ? "signal"
                            : "muted"
                      }
                    >
                      {record.status}
                    </Badge>
                  ) : (
                    <Badge variant="muted">managed</Badge>
                  )}
                </TableCell>
                <TableCell className="hidden font-mono text-[0.62rem] text-muted-foreground md:table-cell">
                  {adminDateTimeFormatter.format(new Date(record.updated_at))}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background p-2 shadow-[-12px_0_20px_-20px_var(--shadow-ink)] transition-colors group-hover:bg-surface-hover sm:p-4">
                  <div className="flex justify-end gap-2">
                    {definition.editEnabled !== false && (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => {
                          setEditing(record);
                          setEditorOpen(true);
                        }}
                        aria-label={`Edit ${record.label}`}
                      >
                        <Pencil aria-hidden="true" />
                      </Button>
                    )}
                    {canManageSensitive && definition.supportsPublication &&
                      record.status !== "published" && (
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => publish(record, "published")}
                          disabled={pending}
                          aria-label={`Publish ${record.label}`}
                        >
                          <Check aria-hidden="true" />
                        </Button>
                      )}
                    {canManageSensitive && definition.supportsPublication &&
                      record.status === "published" && (
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => publish(record, "hidden")}
                          disabled={pending}
                          aria-label={`Hide ${record.label}`}
                        >
                          <Archive aria-hidden="true" />
                        </Button>
                      )}
                    {canManageSensitive && definition.deleteEnabled && (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => setDeleting(record)}
                        aria-label={`Archive ${record.label}`}
                        className="hover:text-destructive"
                      >
                        <Archive aria-hidden="true" />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {data.items.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="h-40 text-center text-muted-foreground"
                >
                  No records match the current view.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      {data.page_info.total_pages > 1 && (
        <div className="mt-5 flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            disabled={data.page_info.page <= 1 || pending}
            onClick={() =>
              startTransition(() => refresh(data.page_info.page - 1))
            }
          >
            <ChevronLeft aria-hidden="true" />
            Previous
          </Button>
          <span className="font-mono text-[0.62rem] uppercase tracking-[0.12em] text-muted-foreground">
            Page {data.page_info.page} / {data.page_info.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={
              data.page_info.page >= data.page_info.total_pages || pending
            }
            onClick={() =>
              startTransition(() => refresh(data.page_info.page + 1))
            }
          >
            Next
            <ChevronRight aria-hidden="true" />
          </Button>
        </div>
      )}
      {editorOpen && (
        <EditorDialog
          canManageSensitive={canManageSensitive}
          open
          setOpen={setEditorOpen}
          record={editing}
          resource={resource}
          definition={definition}
          csrfToken={csrfToken}
          onSaved={refresh}
        />
      )}
      <Dialog
        open={Boolean(deleting)}
        onOpenChange={(open) => {
          if (!open) setDeleting(undefined);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Archive {definition.singular}?</DialogTitle>
            <DialogDescription>
              This removes “{deleting?.label}” from public and active CMS views
              while retaining recoverable history.
            </DialogDescription>
          </DialogHeader>
          <Alert>
            <AlertIcon />
            <AlertTitle>Publication impact</AlertTitle>
            <AlertDescription>
              Referenced content may disappear from related public pages after
              the archive succeeds.
            </AlertDescription>
          </Alert>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDeleting(undefined)}>
              <X aria-hidden="true" />
              Cancel
            </Button>
            <Button variant="destructive" onClick={remove} disabled={pending}>
              {pending ? (
                <LoadingIndicator label="Archiving" />
              ) : (
                <>
                  <Archive aria-hidden="true" />
                  Archive
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
