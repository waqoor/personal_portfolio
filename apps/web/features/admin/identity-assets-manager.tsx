"use client";

import type { AdminIdentityAssets, AdminSocialLinkInput } from "@portfolio/api-client";
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Badge,
  Button,
  Card,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Field,
  FieldDescription,
  Input,
  Label,
  LoadingIndicator,
  Textarea,
} from "@portfolio/ui";
import { Archive, Check, FileUp, ImagePlus, Link2, Pencil, Plus, Star, Trash2 } from "lucide-react";
import * as React from "react";

import { getBrowserApi } from "@/lib/browser-api";

type Props = {
  initial: AdminIdentityAssets;
  csrfToken?: string;
};

type Social = AdminIdentityAssets["social_links"][number];
type ConfirmAction = { label: string; description: string; run: () => Promise<unknown> };

export function IdentityAssetsManager({ csrfToken, initial }: Props) {
  const [assets, setAssets] = React.useState(initial);
  const profileIsPublished = assets.profile.status === "published";
  const [portraitOpen, setPortraitOpen] = React.useState(false);
  const [resumeOpen, setResumeOpen] = React.useState(false);
  const [socialOpen, setSocialOpen] = React.useState(false);
  const [editingSocial, setEditingSocial] = React.useState<Social>();
  const [confirm, setConfirm] = React.useState<ConfirmAction>();
  const [error, setError] = React.useState<string>();
  const [notice, setNotice] = React.useState<string>();
  const [pending, startTransition] = React.useTransition();

  const api = React.useCallback(() => getBrowserApi(csrfToken).admin, [csrfToken]);
  const refresh = React.useCallback(async () => setAssets(await api().getIdentityAssets()), [api]);
  const execute = (operation: () => Promise<unknown>, success: string, after?: () => void) => {
    setError(undefined);
    setNotice(undefined);
    startTransition(async () => {
      try {
        await operation();
        await refresh();
        setNotice(success);
        after?.();
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "The identity asset could not be updated.");
      }
    });
  };

  const uploadPortrait = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    const altText = String(form.get("alt_text") ?? "").trim();
    if (!(file instanceof File) || file.size === 0) return setError("Choose a portrait image.");
    if (!altText) return setError("Portrait alternative text is required.");
    execute(
      () => api().uploadPortrait(file, { profileId: assets.profile.id, altText, makePrimary: form.get("make_primary") === "on", sortOrder: Number(form.get("sort_order") ?? 0) }),
      "Portrait uploaded and validated.",
      () => setPortraitOpen(false),
    );
  };

  const uploadResume = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    const versionLabel = String(form.get("version_label") ?? "").trim();
    const downloadName = String(form.get("download_name") ?? "resume.pdf").trim();
    if (!(file instanceof File) || file.size === 0) return setError("Choose a PDF résumé.");
    if (!versionLabel || !downloadName) return setError("Version and download name are required.");
    const effectiveDate = String(form.get("effective_date") ?? "").trim();
    execute(
      () => api().uploadResume(file, { profileId: assets.profile.id, versionLabel, downloadName, ...(effectiveDate ? { effectiveDate } : {}) }),
      "Résumé version uploaded. Publish it when it is ready to become current.",
      () => setResumeOpen(false),
    );
  };

  const saveSocial = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const input: AdminSocialLinkInput = {
      platform: String(form.get("platform") ?? "").trim(),
      label: String(form.get("label") ?? "").trim(),
      url: String(form.get("url") ?? "").trim(),
      handle: String(form.get("handle") ?? "").trim() || null,
      sort_order: Number(form.get("sort_order") ?? 0),
      is_visible: form.get("is_visible") === "on",
    };
    if (!input.platform || !input.label || !input.url) return setError("Platform, label, and URL are required.");
    execute(
      () => editingSocial ? api().updateSocialLink(editingSocial.id, input) : api().createSocialLink(assets.profile.id, input),
      editingSocial ? "Social link updated." : "Social link created.",
      () => { setSocialOpen(false); setEditingSocial(undefined); },
    );
  };

  return (
    <div>
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div><p className="eyebrow">Identity authority</p><h1 className="mt-5 font-display text-5xl leading-none tracking-[-0.055em]">Portraits, résumé & socials</h1><p className="mt-4 max-w-3xl text-sm leading-6 text-muted-foreground">Manage the files and public identity links attached to <strong>{assets.profile.full_name}</strong>. Uploads are validated by the identity service and never bypass the typed client.</p></div>
        <Badge variant={profileIsPublished ? "verified" : "muted"}><Check aria-hidden="true" />Canonical profile {profileIsPublished ? "published" : assets.profile.status}</Badge>
      </div>

      {error && <Alert variant="destructive" className="mt-6"><AlertIcon variant="destructive" /><AlertTitle>Identity update failed</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
      {notice && <Alert variant="success" className="mt-6"><AlertIcon variant="success" /><AlertTitle>Saved</AlertTitle><AlertDescription>{notice}</AlertDescription></Alert>}
      {!profileIsPublished && <Alert className="mt-6"><AlertIcon /><AlertTitle>Public release is locked</AlertTitle><AlertDescription>Assets can be uploaded and reviewed now. Publish the canonical profile before selecting a current public résumé.</AlertDescription></Alert>}

      <section className="mt-10" aria-labelledby="portraits-heading">
        <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow">Hero photography</p><h2 id="portraits-heading" className="mt-3 font-display text-4xl tracking-[-0.05em]">Portraits</h2></div><Button variant="signal" onClick={() => setPortraitOpen(true)}><ImagePlus aria-hidden="true" />Upload portrait</Button></div>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          {assets.portraits.map((portrait) => <Card key={portrait.id} variant="raised" className="grid gap-5 p-6 sm:grid-cols-[1fr_auto] sm:items-center"><div><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{portrait.original_filename}</h3>{portrait.is_primary && <Badge variant="verified"><Star aria-hidden="true" />Primary</Badge>}{!portrait.is_active && <Badge variant="muted">Archived</Badge>}</div><p className="mt-2 text-sm text-muted-foreground">{portrait.alt_text}</p><p className="mt-3 font-mono text-[0.62rem] uppercase tracking-[0.1em] text-muted-foreground">{portrait.media_type} · {portrait.width ?? "?"} × {portrait.height ?? "?"} · {Math.round(portrait.size_bytes / 1024)} KB</p></div><div className="flex gap-2">{!portrait.is_primary && portrait.is_active && <Button size="sm" variant="outline" onClick={() => execute(() => api().setPrimaryPortrait(portrait.id), "Primary portrait updated.")} disabled={pending}><Star aria-hidden="true" />Set primary</Button>}{portrait.is_active && <Button size="icon-sm" variant="ghost" aria-label={`Archive ${portrait.original_filename}`} onClick={() => setConfirm({ label: `Archive ${portrait.original_filename}?`, description: "The image will stop appearing in the public portrait set but its audit history is retained.", run: () => api().archivePortrait(portrait.id) })}><Archive aria-hidden="true" /></Button>}</div></Card>)}
          {assets.portraits.length === 0 && <Card className="p-8 text-sm text-muted-foreground">No portrait has been uploaded. The public hero will use its non-photo fallback until one is available.</Card>}
        </div>
      </section>

      <section className="mt-14 border-t border-border pt-10" aria-labelledby="resumes-heading">
        <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow">Stable download</p><h2 id="resumes-heading" className="mt-3 font-display text-4xl tracking-[-0.05em]">Résumé versions</h2></div><Button variant="signal" onClick={() => setResumeOpen(true)}><FileUp aria-hidden="true" />Upload PDF version</Button></div>
        <div className="mt-5 overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-surface-raised">
          {assets.resumes.map((resume) => <div key={resume.id} className="grid gap-4 border-b border-border p-5 last:border-b-0 lg:grid-cols-[1fr_auto] lg:items-center"><div><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{resume.version_label}</h3>{resume.is_current && <Badge variant="verified">Current</Badge>}<Badge variant={resume.status === "published" ? "verified" : "muted"}>{resume.status}</Badge></div><p className="mt-2 text-sm text-muted-foreground">{resume.original_filename} → {resume.download_name}</p><p className="mt-2 font-mono text-[0.62rem] uppercase tracking-[0.1em] text-muted-foreground">{resume.effective_date ?? "No effective date"} · {Math.round(resume.size_bytes / 1024)} KB</p></div><div className="flex flex-wrap gap-2">{!resume.is_current && resume.status !== "archived" && (profileIsPublished ? <Button size="sm" variant="outline" onClick={() => execute(() => api().publishCurrentResume(resume.id), "Current résumé changed atomically.")} disabled={pending}><Check aria-hidden="true" />Publish current</Button> : <Button size="sm" variant="outline" disabled title="Publish the canonical profile first"><Check aria-hidden="true" />Publish profile first</Button>)}{resume.status !== "archived" && <Button size="icon-sm" variant="ghost" aria-label={`Archive résumé ${resume.version_label}`} onClick={() => setConfirm({ label: `Archive résumé ${resume.version_label}?`, description: resume.is_current ? "The public stable route will be unavailable until another version is published current." : "This version will leave active history but remain recoverable.", run: () => api().archiveResume(resume.id) })}><Archive aria-hidden="true" /></Button>}</div></div>)}
          {assets.resumes.length === 0 && <p className="p-8 text-sm text-muted-foreground">No résumé versions are available. Upload a validated PDF, then publish it as current.</p>}
        </div>
      </section>

      <section className="mt-14 border-t border-border pt-10" aria-labelledby="socials-heading">
        <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="eyebrow">Public identity links</p><h2 id="socials-heading" className="mt-3 font-display text-4xl tracking-[-0.05em]">Social links</h2></div><Button variant="signal" onClick={() => { setEditingSocial(undefined); setSocialOpen(true); }}><Plus aria-hidden="true" />Add link</Button></div>
        <div className="mt-5 grid gap-3">
          {assets.social_links.map((social) => <Card key={social.id} className="grid gap-4 p-5 sm:grid-cols-[1fr_auto] sm:items-center"><div><div className="flex items-center gap-2"><Link2 className="size-4 text-primary" aria-hidden="true" /><h3 className="font-semibold">{social.label}</h3><Badge variant={social.is_visible ? "verified" : "muted"}>{social.is_visible ? "Visible" : "Hidden"}</Badge></div><p className="mt-2 break-all text-sm text-muted-foreground">{social.url}</p></div><div className="flex gap-1"><Button size="icon-sm" variant="ghost" aria-label={`Edit ${social.label}`} onClick={() => { setEditingSocial(social); setSocialOpen(true); }}><Pencil aria-hidden="true" /></Button><Button size="icon-sm" variant="ghost" aria-label={`Delete ${social.label}`} onClick={() => setConfirm({ label: `Delete ${social.label}?`, description: "The link will be removed from the canonical profile and public navigation surfaces.", run: () => api().deleteSocialLink(social.id) })}><Trash2 aria-hidden="true" /></Button></div></Card>)}
          {assets.social_links.length === 0 && <Card className="p-8 text-sm text-muted-foreground">No public social links are configured.</Card>}
        </div>
      </section>

      <Dialog open={portraitOpen} onOpenChange={setPortraitOpen}><DialogContent><DialogHeader><DialogTitle>Upload portrait</DialogTitle><DialogDescription>Images are type-, size-, and metadata-validated by the identity service.</DialogDescription></DialogHeader><form onSubmit={uploadPortrait} className="grid gap-5"><Field><Label htmlFor="portrait-file">Image</Label><Input id="portrait-file" name="file" type="file" accept="image/jpeg,image/png,image/webp,image/avif" required /></Field><Field><Label htmlFor="portrait-alt">Alternative text</Label><Textarea id="portrait-alt" name="alt_text" required /><FieldDescription>Describe the person and the image purpose concisely.</FieldDescription></Field><Field><Label htmlFor="portrait-order">Display order</Label><Input id="portrait-order" name="sort_order" type="number" min={0} defaultValue={assets.portraits.length} /></Field><label className="flex min-h-12 items-center justify-between rounded-2xl border border-border px-4 text-sm font-semibold"><span>Make primary now</span><input name="make_primary" type="checkbox" className="size-4 accent-[var(--primary)]" /></label><DialogFooter><Button type="button" variant="ghost" onClick={() => setPortraitOpen(false)}>Cancel</Button><Button type="submit" variant="signal" disabled={pending}>{pending ? <LoadingIndicator label="Uploading" /> : "Upload portrait"}</Button></DialogFooter></form></DialogContent></Dialog>

      <Dialog open={resumeOpen} onOpenChange={setResumeOpen}><DialogContent><DialogHeader><DialogTitle>Upload résumé version</DialogTitle><DialogDescription>The file remains immutable after upload. Publishing current is a separate, explicit action.</DialogDescription></DialogHeader><form onSubmit={uploadResume} className="grid gap-5"><Field><Label htmlFor="resume-file">PDF file</Label><Input id="resume-file" name="file" type="file" accept="application/pdf" required /></Field><Field><Label htmlFor="resume-version">Version label</Label><Input id="resume-version" name="version_label" placeholder="2026.08" required /></Field><Field><Label htmlFor="resume-date">Effective date</Label><Input id="resume-date" name="effective_date" type="date" /></Field><Field><Label htmlFor="resume-download">Public download filename</Label><Input id="resume-download" name="download_name" defaultValue="yazeed-hasan-resume.pdf" required /></Field><DialogFooter><Button type="button" variant="ghost" onClick={() => setResumeOpen(false)}>Cancel</Button><Button type="submit" variant="signal" disabled={pending}>{pending ? <LoadingIndicator label="Uploading" /> : "Upload version"}</Button></DialogFooter></form></DialogContent></Dialog>

      <Dialog open={socialOpen} onOpenChange={(open) => { setSocialOpen(open); if (!open) setEditingSocial(undefined); }}><DialogContent><DialogHeader><DialogTitle>{editingSocial ? "Edit social link" : "Add social link"}</DialogTitle><DialogDescription>Only links explicitly marked visible are returned by the public profile API.</DialogDescription></DialogHeader><form key={editingSocial?.id ?? "new-social"} onSubmit={saveSocial} className="grid gap-5 sm:grid-cols-2"><Field><Label htmlFor="social-platform">Platform</Label><Input id="social-platform" name="platform" defaultValue={editingSocial?.platform} required /></Field><Field><Label htmlFor="social-label">Public label</Label><Input id="social-label" name="label" defaultValue={editingSocial?.label} required /></Field><Field className="sm:col-span-2"><Label htmlFor="social-url">URL</Label><Input id="social-url" name="url" type="url" defaultValue={editingSocial?.url} required /></Field><Field><Label htmlFor="social-handle">Handle</Label><Input id="social-handle" name="handle" defaultValue={editingSocial?.handle ?? ""} /></Field><Field><Label htmlFor="social-order">Order</Label><Input id="social-order" name="sort_order" type="number" min={0} defaultValue={editingSocial?.sort_order ?? assets.social_links.length} /></Field><label className="sm:col-span-2 flex min-h-12 items-center justify-between rounded-2xl border border-border px-4 text-sm font-semibold"><span>Visible publicly</span><input name="is_visible" type="checkbox" defaultChecked={editingSocial?.is_visible ?? true} className="size-4 accent-[var(--primary)]" /></label><DialogFooter className="sm:col-span-2"><Button type="button" variant="ghost" onClick={() => setSocialOpen(false)}>Cancel</Button><Button type="submit" variant="signal" disabled={pending}>{pending ? <LoadingIndicator label="Saving" /> : "Save link"}</Button></DialogFooter></form></DialogContent></Dialog>

      <Dialog open={Boolean(confirm)} onOpenChange={(open) => { if (!open) setConfirm(undefined); }}><DialogContent><DialogHeader><DialogTitle>{confirm?.label}</DialogTitle><DialogDescription>{confirm?.description}</DialogDescription></DialogHeader><DialogFooter><Button variant="ghost" onClick={() => setConfirm(undefined)}>Cancel</Button><Button variant="destructive" disabled={pending} onClick={() => { if (!confirm) return; execute(confirm.run, "Identity asset updated.", () => setConfirm(undefined)); }}>{pending ? <LoadingIndicator label="Updating" /> : "Confirm"}</Button></DialogFooter></DialogContent></Dialog>
    </div>
  );
}
