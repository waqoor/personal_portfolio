import { cleanup, render, screen } from "@testing-library/react";
import { MotionModeProvider, Reveal, Stagger, StaggerItem } from "@portfolio/motion";

const { motionPreference } = vi.hoisted(() => ({
  motionPreference: { reduced: false },
}));

vi.mock("motion/react", async (importOriginal) => ({
  ...(await importOriginal<typeof import("motion/react")>()),
  useReducedMotion: () => motionPreference.reduced,
}));

describe("homepage motion contract", () => {
  afterEach(() => {
    cleanup();
    motionPreference.reduced = false;
  });

  it("uses reveal initial state only for an enabled motion mode", () => {
    const { rerender } = render(
      <MotionModeProvider mode="reveal">
        <Reveal data-testid="reveal">Content</Reveal>
      </MotionModeProvider>,
    );
    expect(screen.getByTestId("reveal")).toHaveStyle({ opacity: "0" });

    rerender(
      <MotionModeProvider mode="none">
        <Reveal key="none" data-testid="reveal">Content</Reveal>
      </MotionModeProvider>,
    );
    expect(screen.getByTestId("reveal")).not.toHaveStyle({ opacity: "0" });
  });

  it("lets the stagger mode own child staggering and honors reduced motion", () => {
    const { rerender } = render(
      <MotionModeProvider mode="stagger">
        <Stagger key="normal">
          <StaggerItem>
            <span>Staggered item</span>
          </StaggerItem>
        </Stagger>
      </MotionModeProvider>,
    );
    expect(screen.getByText("Staggered item").parentElement).toHaveStyle({ opacity: "0" });

    motionPreference.reduced = true;
    rerender(
      <MotionModeProvider mode="stagger">
        <Stagger key="reduced">
          <StaggerItem>
            <span>Staggered item</span>
          </StaggerItem>
        </Stagger>
      </MotionModeProvider>,
    );
    expect(screen.getByText("Staggered item").parentElement).not.toHaveStyle({ opacity: "0" });
  });
});
