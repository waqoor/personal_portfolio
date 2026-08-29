import { act, fireEvent, render, screen } from "@testing-library/react";
import { fixtureHome } from "@/test/portfolio-fixture";
import { HomepageComposer } from "./homepage-composer";

const { saveHomepageSections } = vi.hoisted(() => ({ saveHomepageSections: vi.fn() }));

vi.mock("@/lib/browser-api", () => ({
  getBrowserApi: () => ({ admin: { saveHomepageSections } }),
}));

describe("HomepageComposer", () => {
  beforeEach(() => saveHomepageSections.mockReset());

  it("offers keyboard-operable ordering and visibility controls", () => {
    render(<HomepageComposer initial={fixtureHome.sections.slice(0, 3)} />);
    expect(screen.getByRole("button", { name: /Move Hero \/ personal identity up/ })).toBeDisabled();
    const moveResumeUp = screen.getByRole("button", { name: /Move Résumé up/ });
    fireEvent.click(moveResumeUp);
    const orderBadges = screen.getAllByText(/^0[1-3]$/);
    expect(orderBadges).toHaveLength(3);
    expect(screen.getByRole("switch", { name: /Show Hero \/ personal identity/ })).toBeChecked();
  });

  it("edits bounded registry entries and persists normalized composition", async () => {
    saveHomepageSections.mockImplementation(async (sections) => sections);
    render(<HomepageComposer csrfToken="csrf-token" initial={fixtureHome.sections.slice(0, 4)} />);

    fireEvent.click(screen.getByRole("switch", { name: /Show Hero \/ personal identity/ }));
    fireEvent.change(screen.getAllByLabelText("Item limit")[0]!, { target: { value: "4" } });
    fireEvent.click(screen.getAllByRole("button", { name: /Remove .* from homepage/ })[1]!);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /Save composition/ }));
    });

    expect(await screen.findByText("Homepage composition saved.")).toBeInTheDocument();
    expect(saveHomepageSections).toHaveBeenCalledWith(
      expect.arrayContaining([expect.objectContaining({ kind: "hero", enabled: false })]),
    );
    expect(saveHomepageSections.mock.calls[0]?.[0]).not.toEqual(
      expect.arrayContaining([expect.objectContaining({ kind: "resume" })]),
    );
  });

});
