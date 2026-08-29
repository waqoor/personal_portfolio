"use client";

import { Alert, AlertDescription, AlertIcon, AlertTitle, Button, Field, Input, Label, LoadingIndicator } from "@portfolio/ui";
import { LockKeyhole, LogIn } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { getBrowserApi } from "@/lib/browser-api";

export function LoginForm() {
  const router = useRouter();
  const [error, setError] = React.useState<string>();
  const [pending, startTransition] = React.useTransition();
  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(undefined);
    const data = new FormData(event.currentTarget);
    startTransition(async () => {
      try {
        const session = await getBrowserApi().admin.login({ email: String(data.get("email") ?? ""), password: String(data.get("password") ?? "") });
        if (!session.authenticated) throw new Error("Authentication was not established.");
        router.replace("/admin");
        router.refresh();
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Sign-in failed.");
      }
    });
  };
  return (
    <form onSubmit={submit} className="grid gap-5">
      <Field><Label htmlFor="admin-email">Email</Label><Input id="admin-email" name="email" type="email" autoComplete="username" required /></Field>
      <Field><Label htmlFor="admin-password">Password</Label><Input id="admin-password" name="password" type="password" autoComplete="current-password" required minLength={12} /></Field>
      {error && <Alert variant="destructive"><AlertIcon variant="destructive" /><AlertTitle>Sign-in failed</AlertTitle><AlertDescription>{error}</AlertDescription></Alert>}
      <Button type="submit" variant="signal" size="lg" disabled={pending}>{pending ? <LoadingIndicator label="Signing in" /> : <><LogIn aria-hidden="true" />Sign in securely</>}</Button>
      <p className="flex items-start gap-2 text-xs leading-5 text-muted-foreground"><LockKeyhole className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />Authentication uses the server-managed secure session. Credentials are never stored in browser application state.</p>
    </form>
  );
}
