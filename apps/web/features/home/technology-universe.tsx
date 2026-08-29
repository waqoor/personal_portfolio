"use client";

import type { Skill } from "@portfolio/api-client";
import { Badge, Button, cn } from "@portfolio/ui";
import { Box, Layers3, Orbit, X } from "lucide-react";
import * as React from "react";
import { AmbientField } from "@/components/ambient-field";

export function TechnologyUniverse({ skills }: { skills: Skill[] }) {
  const categories = React.useMemo(() => Array.from(new Set(skills.map((skill) => skill.category))), [skills]);
  const [activeCategory, setActiveCategory] = React.useState<string>(categories[0] ?? "");
  const [activeSkill, setActiveSkill] = React.useState<Skill>();
  const effectiveCategory = categories.includes(activeCategory) ? activeCategory : (categories[0] ?? "");
  const visibleSkills = skills.filter((skill) => !effectiveCategory || skill.category === effectiveCategory);

  return (
    <div className="grid gap-6 lg:grid-cols-[0.72fr_1.28fr]">
      <div className="flex flex-col justify-between gap-8 rounded-[var(--radius-card)] border border-border-strong bg-surface-raised p-6 sm:p-8">
        <div>
          <div className="flex items-center gap-2 font-mono text-[0.65rem] font-semibold uppercase tracking-[0.15em] text-muted-foreground"><Layers3 className="size-4 text-primary" aria-hidden="true" />Select a layer</div>
          <div className="mt-6 flex flex-wrap gap-2" role="group" aria-label="Technology categories">
            {categories.map((category) => (
              <Button key={category} type="button" size="sm" variant={effectiveCategory === category ? "signal" : "outline"} onClick={() => { setActiveCategory(category); setActiveSkill(undefined); }} aria-pressed={effectiveCategory === category}>{category}</Button>
            ))}
          </div>
        </div>
        <div className="border-t border-border pt-6" aria-live="polite">
          {activeSkill ? (
            <div>
              <div className="flex items-start justify-between gap-3"><div><Badge variant="signal">{activeSkill.category}</Badge><h3 className="mt-4 font-display text-4xl leading-none tracking-[-0.05em]">{activeSkill.name}</h3></div><Button variant="ghost" size="icon-sm" onClick={() => setActiveSkill(undefined)} aria-label="Clear selected technology"><X aria-hidden="true" /></Button></div>
              {activeSkill.description && <p className="mt-4 text-sm leading-6 text-muted-foreground">{activeSkill.description}</p>}
              <dl className="mt-5 grid grid-cols-2 gap-3 border-t border-border pt-5"><div><dt className="text-xs text-muted-foreground">Evidence</dt><dd className="mt-1 font-semibold">{activeSkill.project_count} related {activeSkill.project_count === 1 ? "project" : "projects"}</dd></div>{activeSkill.proficiency_label && <div><dt className="text-xs text-muted-foreground">Practice</dt><dd className="mt-1 font-semibold">{activeSkill.proficiency_label}</dd></div>}</dl>
            </div>
          ) : (
            <div><p className="font-display text-3xl leading-none tracking-[-0.04em]">A connected toolkit, not a keyword cloud.</p><p className="mt-3 text-sm leading-6 text-muted-foreground">Choose a technology node to see its context and published project evidence.</p></div>
          )}
        </div>
      </div>

      <div className="relative isolate min-h-[34rem] overflow-hidden rounded-[var(--radius-card)] border border-border-strong bg-ink text-white shadow-[0_40px_120px_-70px_var(--shadow-ink)]">
        <div className="absolute inset-0 opacity-75" aria-hidden="true"><AmbientField className="size-full" density={Math.min(Math.max(skills.length, 18), 48)} /></div>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0_28%,rgb(0_0_0/0.35)_72%,rgb(0_0_0/0.72)_100%)]" aria-hidden="true" />
        <div className="absolute left-5 top-5 z-20 flex items-center gap-2 rounded-full border border-white/15 bg-black/25 px-3 py-2 font-mono text-[0.6rem] uppercase tracking-[0.14em] text-white/65 backdrop-blur-md"><Orbit className="size-3.5 text-primary" aria-hidden="true" />Semantic nodes + WebGL field</div>
        <div className="relative z-10 flex min-h-[34rem] flex-wrap content-center justify-center gap-2 p-8 sm:gap-3 sm:p-12" role="group" aria-label={`${effectiveCategory} technologies`}>
          {visibleSkills.map((skill, index) => (
            <button
              key={skill.id}
              type="button"
              onClick={() => setActiveSkill(skill)}
              aria-pressed={activeSkill?.id === skill.id}
              className={cn(
                "relative inline-flex min-h-11 items-center gap-2 rounded-full border border-white/20 bg-black/35 px-4 py-2 text-sm font-semibold text-white/85 shadow-lg backdrop-blur-md transition-[transform,border-color,background-color,color] hover:-translate-y-1 hover:border-primary/75 hover:bg-primary/15 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transition-none",
                activeSkill?.id === skill.id && "border-primary bg-primary text-primary-foreground",
                index % 5 === 0 && "sm:-translate-y-8",
                index % 7 === 0 && "sm:translate-y-7",
              )}
            >
              <Box className="size-3.5" aria-hidden="true" />{skill.name}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
