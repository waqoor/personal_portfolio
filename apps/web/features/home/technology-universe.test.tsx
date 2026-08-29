import type { Skill } from "@portfolio/api-client";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TechnologyUniverse } from "./technology-universe";

const skills: Skill[] = [
  {
    id: "zero",
    slug: "zero",
    name: "Zero evidence",
    category: "Platform",
    project_count: 0,
    order: 0,
  },
  {
    id: "one",
    slug: "one",
    name: "One evidence",
    category: "Platform",
    project_count: 1,
    order: 1,
  },
  {
    id: "many",
    slug: "many",
    name: "Plural evidence",
    category: "Platform",
    project_count: 3,
    order: 2,
  },
];

describe("TechnologyUniverse", () => {
  it("renders authoritative zero, singular, and plural project evidence counts", () => {
    render(<TechnologyUniverse skills={skills} />);

    fireEvent.click(screen.getByRole("button", { name: "Zero evidence" }));
    expect(screen.getByText("0 related projects")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "One evidence" }));
    expect(screen.getByText("1 related project")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Plural evidence" }));
    expect(screen.getByText("3 related projects")).toBeInTheDocument();
  });
});
