import type { Metadata } from "next";
import { LoginForm } from "@/features/admin/login-form";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Admin sign in", robots: { index: false, follow: false } };

export default function AdminLoginPage() {
  return (
    <main id="main-content" className="coordinate-grid min-h-dvh p-3 sm:p-6">
      <div className="mx-auto grid min-h-[calc(100dvh-1.5rem)] max-w-6xl overflow-hidden rounded-[clamp(1.5rem,4vw,3rem)] border border-border-strong bg-background shadow-[0_40px_140px_-70px_var(--shadow-ink)] sm:min-h-[calc(100dvh-3rem)] lg:grid-cols-[1fr_0.72fr]">
        <section className="relative hidden overflow-hidden bg-foreground p-10 text-background lg:flex lg:flex-col lg:justify-between"><div className="absolute -right-40 -top-40 size-[34rem] rounded-full border border-primary/30" aria-hidden="true"><div className="absolute inset-16 rounded-full border border-primary/20" /><div className="absolute inset-32 rounded-full bg-primary/10 blur-2xl" /></div><p className="eyebrow relative z-10 text-background/65">Private administration</p><div className="relative z-10"><p className="display-md max-w-[11ch]">The portfolio’s source of truth.</p><p className="mt-6 max-w-md text-sm leading-7 text-background/60">Manage publication, evidence approval, homepage composition, feature availability, media, discovery, and the assistant from one protected surface.</p></div><p className="relative z-10 font-mono text-[0.62rem] uppercase tracking-[0.13em] text-background/70">Deny by default · No public indexing</p></section>
        <section className="flex items-center p-6 sm:p-10 lg:p-14"><div className="mx-auto w-full max-w-md"><span className="grid size-12 place-items-center rounded-full bg-primary font-mono text-xs font-bold text-primary-foreground">CMS</span><h1 className="mt-8 font-display text-5xl leading-none tracking-[-0.055em]">Welcome back.</h1><p className="mt-4 text-sm leading-6 text-muted-foreground">Sign in with an authorized owner or editor account.</p><div className="mt-8"><LoginForm /></div></div></section>
      </div>
    </main>
  );
}
