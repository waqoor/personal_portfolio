import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeSwitcher } from "./theme-switcher";

const setTheme = vi.fn();

vi.mock("next-themes", () => ({
  useTheme: () => ({ resolvedTheme: "dark", setTheme, theme: "dark" }),
}));

describe("ThemeSwitcher", () => {
  beforeEach(() => setTheme.mockClear());

  it("exposes persistent light, dark, and system choices as icon-only controls", async () => {
    const user = userEvent.setup();
    render(<ThemeSwitcher />);

    const light = screen.getByRole("button", { name: "Use light theme" });
    const dark = screen.getByRole("button", { name: "Use dark theme" });
    const system = screen.getByRole("button", { name: "Use system theme" });

    expect(dark).toHaveAttribute("aria-pressed", "true");
    expect(light).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByText("Light")).not.toBeInTheDocument();
    expect(screen.queryByText("Dark")).not.toBeInTheDocument();
    expect(screen.queryByText("System")).not.toBeInTheDocument();

    await user.click(light);
    await user.click(dark);
    await user.click(system);
    expect(setTheme.mock.calls.map(([value]) => value)).toEqual(["light", "dark", "system"]);
  });
});
