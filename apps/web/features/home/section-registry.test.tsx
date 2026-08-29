import { homePageSchema } from "@portfolio/api-client";
import { fixtureHome } from "@/test/portfolio-fixture";
import { resolveHomepageSections } from "./section-registry";

describe("homepage section registry", () => {
  it("sorts enabled sections and removes disabled feature families", () => {
    const data = {
      ...fixtureHome,
      sections: fixtureHome.sections.map((section) => section.kind === "writing" ? { ...section, order: -1 } : section),
      feature_flags: { ...fixtureHome.feature_flags, articles: false },
    };
    const resolved = resolveHomepageSections(data);
    expect(resolved.some((section) => section.kind === "writing")).toBe(false);
    expect(resolved[0]?.kind).toBe("hero");
  });

  it("removes individually hidden sections without deleting their content", () => {
    const data = {
      ...fixtureHome,
      sections: fixtureHome.sections.map((section) => section.kind === "metrics" ? { ...section, enabled: false } : section),
    };
    expect(resolveHomepageSections(data).some((section) => section.kind === "metrics")).toBe(false);
    expect(data.metrics).toHaveLength(2);
  });

  it("fails closed when a registry-gated section has no authoritative feature state", () => {
    const data = {
      ...fixtureHome,
      feature_flags: Object.fromEntries(
        Object.entries(fixtureHome.feature_flags).filter(([key]) => key !== "projects"),
      ),
    };

    expect(resolveHomepageSections(data).some((section) => section.kind === "selected_work")).toBe(false);
  });

  it("omits empty collection modules while preserving their configured sections", () => {
    const data = { ...fixtureHome, categories: [], articles: [] };
    const resolved = resolveHomepageSections(data);

    expect(resolved.some((section) => section.kind === "what_i_build")).toBe(false);
    expect(resolved.some((section) => section.kind === "writing")).toBe(false);
    expect(data.sections.some((section) => section.kind === "what_i_build")).toBe(true);
    expect(data.sections.some((section) => section.kind === "writing")).toBe(true);
  });

  it("omits evidence modules when no approved evidence is publishable", () => {
    const data = {
      ...fixtureHome,
      metrics: fixtureHome.metrics.map((metric) => ({ ...metric, verified: false })),
      testimonials: fixtureHome.testimonials.map((item) => ({ ...item, verified: false })),
    };
    const resolved = resolveHomepageSections(data);

    expect(resolved.some((section) => section.kind === "metrics")).toBe(false);
    expect(resolved.some((section) => section.kind === "testimonials")).toBe(false);
  });

  it("fails the public contract when more than five featured projects are returned", () => {
    const sixth = { ...fixtureHome.featured_projects[0]!, id: "project-6", slug: "project-six", featured_rank: 5 };
    expect(homePageSchema.safeParse({ ...fixtureHome, featured_projects: [...fixtureHome.featured_projects, sixth] }).success).toBe(false);
  });
});
