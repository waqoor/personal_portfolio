"use client";

import { contactRequestSchema, type ContactOptions, type ContactRequest } from "@portfolio/api-client";
import { Alert, AlertDescription, AlertIcon, AlertTitle, Button, Field, FieldDescription, FieldError, Input, Label, LoadingIndicator, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Textarea } from "@portfolio/ui";
import { Send } from "lucide-react";
import * as React from "react";
import { getBrowserApi } from "@/lib/browser-api";

type FieldErrors = Partial<Record<keyof ContactRequest, string>>;

type ContactFormProps = {
  options: ContactOptions;
  defaultCategoryId?: ContactOptions["categories"][number]["id"];
  submitLabel?: string;
  subjectPlaceholder?: string;
};

export function ContactForm({
  defaultCategoryId,
  options,
  subjectPlaceholder = "What should we explore…",
  submitLabel = "Send inquiry",
}: ContactFormProps) {
  const formRef = React.useRef<HTMLFormElement>(null);
  const operationRef = React.useRef<{ key: string; payload: string } | undefined>(undefined);
  const [errors, setErrors] = React.useState<FieldErrors>({});
  const [success, setSuccess] = React.useState<string>();
  const [requestError, setRequestError] = React.useState<string>();
  const [pending, startTransition] = React.useTransition();

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSuccess(undefined);
    setRequestError(undefined);
    const formData = new FormData(event.currentTarget);
    const organization = String(formData.get("organization") ?? "").trim();
    const candidate = {
      name: String(formData.get("name") ?? ""),
      email: String(formData.get("email") ?? ""),
      category_id: String(formData.get("category_id") ?? ""),
      ...(organization ? { organization } : {}),
      subject: String(formData.get("subject") ?? ""),
      message: String(formData.get("message") ?? ""),
      website: String(formData.get("website") ?? ""),
      consent: formData.get("consent") === "on",
    };
    const parsed = contactRequestSchema.safeParse(candidate);
    if (!parsed.success) {
      const nextErrors: FieldErrors = {};
      for (const issue of parsed.error.issues) {
        const key = issue.path[0] as keyof ContactRequest | undefined;
        if (key && !nextErrors[key]) nextErrors[key] = issue.message;
      }
      setErrors(nextErrors);
      const firstField = parsed.error.issues[0]?.path[0];
      if (typeof firstField === "string") document.querySelector<HTMLElement>(`[name="${CSS.escape(firstField)}"]`)?.focus();
      return;
    }
    setErrors({});
    const canonicalPayload = JSON.stringify(parsed.data);
    if (operationRef.current?.payload !== canonicalPayload) {
      operationRef.current = {
        key: `contact-${globalThis.crypto.randomUUID()}`,
        payload: canonicalPayload,
      };
    }
    const operation = operationRef.current;
    startTransition(async () => {
      try {
        const result = await getBrowserApi().public.submitContact(parsed.data, {
          idempotencyKey: operation.key,
        });
        setSuccess(result.message);
        operationRef.current = undefined;
        formRef.current?.reset();
      } catch (caught) {
        setRequestError(caught instanceof Error ? caught.message : "Your message could not be submitted.");
      }
    });
  };

  if (!options.accepting_messages) {
    return <Alert role="alert"><AlertIcon /><AlertTitle>Contact form paused</AlertTitle><AlertDescription>New messages are not being accepted through this form right now. Please use an approved social channel instead.</AlertDescription></Alert>;
  }

  return (
    <form ref={formRef} onSubmit={submit} noValidate className="grid gap-6" aria-describedby="contact-form-note" aria-busy={pending}>
      <div className="grid gap-6 sm:grid-cols-2">
        <Field><Label htmlFor="name">Name <span aria-hidden="true" className="text-destructive">*</span></Label><Input id="name" name="name" autoComplete="name" required aria-invalid={Boolean(errors.name)} aria-describedby={errors.name ? "name-error" : undefined} />{errors.name && <FieldError id="name-error">{errors.name}</FieldError>}</Field>
        <Field><Label htmlFor="email">Email <span aria-hidden="true" className="text-destructive">*</span></Label><Input id="email" name="email" type="email" autoComplete="email" required aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "email-error" : undefined} />{errors.email && <FieldError id="email-error">{errors.email}</FieldError>}</Field>
      </div>
      <div className="grid gap-6 sm:grid-cols-2">
        <Field><Label htmlFor="organization">Organization <span className="font-normal text-muted-foreground">(optional)</span></Label><Input id="organization" name="organization" autoComplete="organization" aria-invalid={Boolean(errors.organization)} aria-describedby={errors.organization ? "organization-error" : undefined} />{errors.organization && <FieldError id="organization-error">{errors.organization}</FieldError>}</Field>
        <Field><Label htmlFor="category_id">Conversation type <span aria-hidden="true" className="text-destructive">*</span></Label><Select name="category_id" required {...(defaultCategoryId ? { defaultValue: defaultCategoryId } : {})}><SelectTrigger id="category_id" aria-invalid={Boolean(errors.category_id)} aria-describedby={errors.category_id ? "category-error" : undefined}><SelectValue placeholder="Choose a category" /></SelectTrigger><SelectContent>{options.categories.map((category) => <SelectItem key={category.id} value={category.id}>{category.label}</SelectItem>)}</SelectContent></Select>{errors.category_id && <FieldError id="category-error">{errors.category_id}</FieldError>}</Field>
      </div>
      <Field><Label htmlFor="subject">Subject <span aria-hidden="true" className="text-destructive">*</span></Label><Input id="subject" name="subject" required maxLength={180} placeholder={subjectPlaceholder} aria-invalid={Boolean(errors.subject)} aria-describedby={errors.subject ? "subject-error" : undefined} />{errors.subject && <FieldError id="subject-error">{errors.subject}</FieldError>}</Field>
      <Field><Label htmlFor="message">Context <span aria-hidden="true" className="text-destructive">*</span></Label><Textarea id="message" name="message" required minLength={20} maxLength={5000} placeholder="Share the problem, constraints, current state, and outcome you need…" aria-invalid={Boolean(errors.message)} aria-describedby={errors.message ? "message-error contact-form-note" : "contact-form-note"} /><FieldDescription id="contact-form-note">Avoid secrets or sensitive personal information. Include enough technical or business context for a useful response.</FieldDescription>{errors.message && <FieldError id="message-error">{errors.message}</FieldError>}</Field>
      <div className="absolute -left-[9999px]" aria-hidden="true"><Label htmlFor="website">Website</Label><Input id="website" name="website" tabIndex={-1} autoComplete="off" /></div>
      <Field>
        <label className="grid cursor-pointer grid-cols-[auto_1fr] items-start gap-3 rounded-2xl border border-border bg-surface-raised p-4 text-sm leading-6 transition-colors hover:border-border-strong focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2"><input id="consent" type="checkbox" name="consent" required className="mt-0.5 size-5 accent-[var(--primary)] outline-none" aria-invalid={Boolean(errors.consent)} aria-describedby={errors.consent ? "consent-error" : undefined} /><span>I consent to this inquiry being stored and used to respond. <span className="text-muted-foreground">No marketing subscription is created.</span></span></label>
        {errors.consent && <FieldError id="consent-error">{errors.consent}</FieldError>}
      </Field>
      {requestError && <Alert variant="destructive"><AlertIcon variant="destructive" /><AlertTitle>Message not submitted</AlertTitle><AlertDescription>{requestError} Your draft remains in the form.</AlertDescription></Alert>}
      {success && <Alert variant="success"><AlertIcon variant="success" /><AlertTitle>Message received</AlertTitle><AlertDescription>{success}</AlertDescription></Alert>}
      <div className="flex flex-col-reverse gap-4 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between"><p className="text-xs leading-5 text-muted-foreground">{options.response_time_label ?? "Response timing depends on fit and availability."}</p><Button type="submit" variant="signal" size="lg" disabled={pending}>{pending ? <LoadingIndicator label="Sending" /> : <><Send aria-hidden="true" />{submitLabel}</>}</Button></div>
    </form>
  );
}
