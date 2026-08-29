import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AdminFieldDefinition } from "./resource-definitions";
import { RESOURCE_DEFINITIONS } from "./resource-definitions";
import {
  parseRecordForm,
  RelationField,
  ResourceWorkspace,
} from "./resource-workspace";

const { adminList } = vi.hoisted(() => ({ adminList: vi.fn() }));

vi.mock("@/lib/browser-api", () => ({
  getBrowserApi: () => ({ admin: { list: adminList } }),
}));

const relationField: AdminFieldDefinition = {
  key: "skill_ids",
  label: "Skills",
  type: "relation-many",
  relation: { resource: "skills", selectedDataKey: "skills", ordered: true },
};

function relationPage(page: number, search?: string) {
  const suffix = search ? ` for ${search}` : "";
  return {
    items: [
      {
        id: page === 1 ? "skill-python" : "skill-go",
        label: page === 1 ? `Python${suffix}` : `Go${suffix}`,
        updated_at: "2026-08-28T00:00:00Z",
        status: "published",
        data: {},
      },
      ...(page === 1
        ? [{
            id: "skill-rust",
            label: `Rust${suffix}`,
            updated_at: "2026-08-28T00:00:00Z",
            status: "published",
            data: {},
          }, {
            id: "skill-archived",
            label: "Archived skill",
            updated_at: "2026-08-28T00:00:00Z",
            status: "archived",
            data: {},
          }]
        : []),
    ],
    page_info: { page, page_size: 25, total: 26, total_pages: 2 },
  };
}

describe("ResourceWorkspace relationships and permissions", () => {
  beforeEach(() => {
    adminList.mockReset();
    adminList.mockImplementation(
      async (_resource: string, query: { page?: number; search?: string }) =>
        relationPage(query.page ?? 1, query.search),
    );
  });

  it("loads labels, preserves unavailable selections, searches, pages, and serializes order", async () => {
    const user = userEvent.setup();
    const record = {
      id: "project-1",
      label: "Project",
      updated_at: "2026-08-28T00:00:00Z",
      status: "draft" as const,
      data: {
        skill_ids: ["skill-python", "skill-removed"],
        skills: [{ id: "skill-python", name: "Python" }],
      },
    };
    render(
      <form data-testid="relation-form">
        <RelationField field={relationField} record={record} />
      </form>,
    );

    const rust = await screen.findByRole("checkbox", { name: "Rust" });
    expect(screen.getAllByRole("checkbox", { name: "Python" })).toHaveLength(1);
    expect(screen.getByText("skill-removed (unavailable)")).toBeInTheDocument();
    expect(screen.queryByText("Archived skill")).not.toBeInTheDocument();

    rust.focus();
    await user.keyboard(" ");
    expect(rust).toBeChecked();
    const selected = new FormData(screen.getByTestId("relation-form") as HTMLFormElement)
      .getAll("skill_ids");
    expect(selected).toEqual(["skill-python", "skill-removed", "skill-rust"]);

    await user.clear(screen.getByRole("searchbox", { name: "Search skills" }));
    await user.type(screen.getByRole("searchbox", { name: "Search skills" }), "systems");
    await user.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() =>
      expect(adminList).toHaveBeenCalledWith(
        "skills",
        expect.objectContaining({ page: 1, search: "systems" }),
      ),
    );
    await user.click(await screen.findByRole("button", { name: "Load more" }));
    await waitFor(() =>
      expect(adminList).toHaveBeenCalledWith(
        "skills",
        expect.objectContaining({ page: 2, search: "systems" }),
      ),
    );
  });

  it("serializes relation-one and relation-many fields without duplicate JSON handling", () => {
    const form = document.createElement("form");
    form.innerHTML = [
      '<input name="category_id" value="category-1">',
      '<input name="skill_ids" value="skill-1">',
      '<input name="skill_ids" value="skill-2">',
    ].join("");
    const parsed = parseRecordForm(form, [
      {
        key: "category_id",
        label: "Category",
        type: "relation-one",
        relation: { resource: "categories" },
      },
      relationField,
    ]);

    expect(parsed.data).toEqual({
      category_id: "category-1",
      skill_ids: ["skill-1", "skill-2"],
    });
  });

  it("keeps owner-only publication and featured controls out of the editor UI", () => {
    render(
      <ResourceWorkspace
        role="editor"
        resource="projects"
        definition={RESOURCE_DEFINITIONS.projects!}
        initial={{
          items: [{
            id: "project-draft",
            label: "Editor draft",
            slug: "editor-draft",
            status: "draft",
            updated_at: "2026-08-28T00:00:00Z",
            data: {},
          }],
          page_info: { page: 1, page_size: 25, total: 1, total_pages: 1 },
        }}
      />,
    );

    expect(screen.queryByText("Featured project slots")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Publish Editor draft" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Archive Editor draft" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit Editor draft" })).toBeInTheDocument();
  });

  it("allows the profile editor to preserve validated site-relative CTA paths", async () => {
    const user = userEvent.setup();
    render(
      <ResourceWorkspace
        role="owner"
        resource="profile"
        definition={RESOURCE_DEFINITIONS.profile!}
        initial={{
          items: [{
            id: "profile-yazeed",
            label: "Yazeed Hasan",
            status: "published",
            updated_at: "2026-08-28T00:00:00Z",
            data: {
              full_name: "Yazeed Hasan",
              headline: "AI and data engineering",
              short_bio: "Production systems from problem framing through operations.",
              primary_cta_label: "Explore projects",
              primary_cta_url: "/projects",
              secondary_cta_label: "Discuss sponsorship",
              secondary_cta_url: "/sponsor",
            },
          }],
          page_info: { page: 1, page_size: 25, total: 1, total_pages: 1 },
        }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Edit Yazeed Hasan" }));

    expect(screen.getByRole("textbox", { name: "Primary CTA URL" })).toHaveAttribute("type", "text");
    expect(screen.getByRole("textbox", { name: "Primary CTA URL" })).toHaveValue("/projects");
    expect(screen.getByRole("textbox", { name: "Secondary CTA URL" })).toHaveValue("/sponsor");
  });
});
