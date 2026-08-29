import { cleanup, render, screen } from "@testing-library/react";
import type { HomepageSection, HomepageSectionKind } from "@portfolio/api-client";
import { fixtureHome } from "@/test/portfolio-fixture";
import { HeroSection } from "./hero-section";
import {
  AssistantCtaSection,
  AvailabilitySection,
  ContactCtaSection,
  ResumeSection,
} from "./utility-sections";

vi.mock("@/components/ambient-field", () => ({
  AmbientField: () => <div aria-hidden="true" />,
}));

function section(kind: HomepageSectionKind): HomepageSection {
  const configured =
    fixtureHome.sections.find((item) => item.kind === kind) ??
    {
      ...fixtureHome.sections[0]!,
      id: `section-${kind}`,
      kind,
      variant: "default",
    };
  return { ...configured, cta_visible: false };
}

describe("homepage CTA visibility contract", () => {
  afterEach(cleanup);

  it("hides the complete hero action group", () => {
    render(<HeroSection data={fixtureHome} section={section("hero")} />);

    expect(screen.queryByRole("link", { name: /Explore selected work/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /R.sum./ })).not.toBeInTheDocument();
  });

  it("hides actions consistently in utility CTA sections", () => {
    const { rerender } = render(
      <ResumeSection data={fixtureHome} section={section("resume")} />,
    );
    expect(screen.queryByRole("link", { name: /Download/ })).not.toBeInTheDocument();

    rerender(
      <AvailabilitySection data={fixtureHome} section={section("availability")} />,
    );
    expect(screen.queryByRole("link", { name: /Discuss a fit/ })).not.toBeInTheDocument();

    rerender(
      <AssistantCtaSection data={fixtureHome} section={section("assistant")} />,
    );
    expect(screen.queryByRole("button", { name: /Ask my AI/ })).not.toBeInTheDocument();

    rerender(<ContactCtaSection data={fixtureHome} section={section("contact")} />);
    expect(screen.queryByRole("link", { name: /Start a conversation/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Browse the case studies/ })).not.toBeInTheDocument();
  });
});
