import { describe, expect, it } from "vitest";

import { isSameOriginMutation, publicRequestOrigin } from "./proxy-origin";

describe("proxy-aware mutation origin validation", () => {
  it("uses the external origin supplied by the trusted production proxy", () => {
    const headers = new Headers({
      host: "web:3000",
      "x-forwarded-host": "portfolio.example.com",
      "x-forwarded-proto": "https",
      origin: "https://portfolio.example.com",
      "sec-fetch-site": "same-origin",
    });

    expect(publicRequestOrigin(headers, "http://web:3000")).toBe(
      "https://portfolio.example.com",
    );
    expect(isSameOriginMutation(headers, "http://web:3000")).toBe(true);
  });

  it("falls back safely when forwarded values are absent or malformed", () => {
    expect(publicRequestOrigin(new Headers(), "http://web:3000/path")).toBe(
      "http://web:3000",
    );
    expect(
      publicRequestOrigin(
        new Headers({
          host: "portfolio.example.com/path",
          "x-forwarded-proto": "javascript",
        }),
        "https://internal:3000",
      ),
    ).toBe("https://internal:3000");
  });

  it("rejects cross-origin and cross-site mutations", () => {
    const base = {
      host: "portfolio.example.com",
      "x-forwarded-proto": "https",
    };
    expect(
      isSameOriginMutation(
        new Headers({ ...base, origin: "https://attacker.example" }),
        "http://web:3000",
      ),
    ).toBe(false);
    expect(
      isSameOriginMutation(
        new Headers({ ...base, "sec-fetch-site": "cross-site" }),
        "http://web:3000",
      ),
    ).toBe(false);
  });
});
