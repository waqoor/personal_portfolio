import axe from "axe-core";
import { render } from "@testing-library/react";
import { ContactForm } from "@/features/contact/contact-form";
import { ProjectCard } from "@/features/projects/project-card";
import { fixtureContactOptions, fixtureHome } from "@/test/portfolio-fixture";

describe("critical component accessibility", () => {
  it("has no automated violations in the contact workflow", async () => {
    const { container } = render(<main><h1>Contact</h1><ContactForm options={fixtureContactOptions} /></main>);
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });

  it("has no automated violations in a project archive card", async () => {
    const project = fixtureHome.featured_projects[0]!;
    const { container } = render(<main><h1>Projects</h1><ProjectCard project={project} /></main>);
    const results = await axe.run(container);
    expect(results.violations).toEqual([]);
  });
});
