import { copyrightLabel } from "./site-footer";

describe("copyrightLabel", () => {
  it("keeps the 2026 launch year and advances the current year", () => {
    expect(copyrightLabel("Yazeed Hasan", 2031)).toBe("© 2026 - 2031 Yazeed Hasan");
  });
});
