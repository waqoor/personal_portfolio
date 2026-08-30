import { fireEvent, render, screen, within } from "@testing-library/react";
import type { MediaAsset } from "@portfolio/api-client";
import { SiteHeader } from "./site-header";

vi.mock("next/navigation", () => ({
  usePathname: () => "/projects",
}));

vi.mock("./theme-switcher", () => ({
  ThemeSwitcher: () => <div data-testid="theme-switcher" />,
}));

const portrait: MediaAsset = {
  id: "portrait-1",
  kind: "image",
  url: "/api/v1/public/portraits/portrait-1",
  alt: "Portrait of Yazeed Hasan",
  is_decorative: false,
  width: 800,
  height: 800,
};

describe("SiteHeader", () => {
  it("renders the final navigation contract without chapters or duplicate pages", () => {
    render(<SiteHeader brandName="Yazeed Hasan" brandLogo={portrait} />);

    const navigation = screen.getByRole("navigation", { name: "Primary navigation" });
    expect(within(navigation).getAllByRole("link").map((link) => link.textContent)).toEqual([
      "Work",
      "Projects",
      "Achievements",
      "Sponsor",
    ]);
    expect(within(navigation).getByRole("link", { name: "Work" })).toHaveAttribute(
      "href",
      "/work",
    );
    expect(screen.queryByText("About")).not.toBeInTheDocument();
    expect(screen.queryByText(/^0[1-9]$/)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Contact Me" })).toBeInTheDocument();
    expect(within(navigation).queryByRole("link", { name: /Contact/ })).not.toBeInTheDocument();
  });

  it("uses the managed portrait and falls back to derived desktop and compact initials", () => {
    render(<SiteHeader brandName="Yazeed Ahmad Hasan" brandLogo={portrait} />);

    fireEvent.error(screen.getByRole("img", { name: "Portrait of Yazeed Hasan" }));

    expect(screen.getByTestId("brand-initial-main")).toHaveTextContent("YH");
    expect(screen.getByTestId("brand-initial-mini")).toHaveTextContent("Y");
  });
});
