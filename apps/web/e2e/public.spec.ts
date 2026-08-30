import AxeBuilder from "@axe-core/playwright";
import { devices, expect, test, type Page } from "@playwright/test";

const expectedName = process.env.PORTFOLIO_E2E_EXPECTED_NAME ?? "Integration Test Portfolio";
const canonicalOrigin = "https://portfolio.example.com";

function collectRuntimeFailures(page: Page): string[] {
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") failures.push(`console: ${message.text()}`);
  });
  page.on("requestfailed", (request) => {
    const error = request.failure()?.errorText ?? "failed";
    if (error.includes("ERR_ABORTED") && request.url().includes("_rsc=")) return;
    failures.push(`${request.method()} ${request.url()} ${error}`);
  });
  return failures;
}

test.describe.configure({ mode: "serial" });

test("public homepage renders canonical published content without draft leakage", async ({ page }) => {
  const failures = collectRuntimeFailures(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: expectedName })).toBeVisible();
  await expect(page.locator("[data-section-kind='selected_work'] article")).toHaveCount(1);
  await expect(page.getByText("Private Draft Sentinel")).toHaveCount(0);
  await expect(page.getByText("Private Article Sentinel")).toHaveCount(0);
  await expect(page.getByRole("link", { name: /Verification Systems 1 published project/ })).toBeVisible();
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", /https?:\/\//);
  const primaryLinks = page
    .getByRole("navigation", { name: "Primary navigation" })
    .getByRole("link");
  await expect(primaryLinks).toHaveText(["Work", "Projects", "Achievements", "Sponsor"]);
  await expect(page.getByRole("link", { name: "Contact Me" })).toBeVisible();
  await expect(page.getByRole("link", { name: "About" })).toHaveCount(0);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  expect(failures).toEqual([]);
});

test("theme controls remain keyboard-operable and disabled assistant stays absent", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/dark/);

  await expect(page.getByRole("button", { name: "Ask my portfolio AI" })).toHaveCount(0);
});

test("project archive, deep case study, writing, and 404 stay semantic", async ({ page }) => {
  await page.goto("/projects");
  await expect(page.getByRole("heading", { level: 1, name: "Projects" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Canonical Service Verification" })).toBeVisible();
  await page.getByRole("link", { name: /Canonical Service Verification/i }).first().click();
  await expect(page).toHaveURL(/\/projects\/canonical-service-verification$/);
  await expect(page.getByRole("heading", { level: 1, name: "Canonical Service Verification" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Architecture" })).toBeVisible();

  await page.goto("/writing/testing-the-canonical-path");
  await expect(page.getByRole("heading", { level: 1, name: "Testing the Canonical Path" })).toBeVisible();
  await expect(page.getByText("Private Article Sentinel")).toHaveCount(0);

  await page.goto("/not-a-published-route");
  await expect(page.getByRole("heading", { level: 1, name: "The trail ends here." })).toBeVisible();
});

test("public profile chapters render their published evidence without runtime failures", async ({ page }) => {
  const failures = collectRuntimeFailures(page);
  const chapters = [
    ["/achievements", "Achievements"],
    ["/work", "Work"],
    ["/open-source", "Open source"],
    ["/sectors", "Sectors"],
    ["/writing", "Writing"],
  ] as const;

  for (const [path, heading] of chapters) {
    const response = await page.goto(path);
    expect(response?.status(), path).toBe(200);
    await expect(page.getByRole("heading", { level: 1, name: heading })).toBeVisible();
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", `${canonicalOrigin}${path}`);
  }

  expect(failures).toEqual([]);
});

test("retired about route permanently consolidates into the homepage", async ({ page }) => {
  const response = await page.goto("/about");
  expect(response?.status()).toBe(200);
  await expect(page).toHaveURL(/\/#leadership-approach$/);
  await expect(page.getByRole("heading", { level: 1, name: expectedName })).toBeVisible();
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", `${canonicalOrigin}/`);
});

test("stable résumé route returns the current managed PDF", async ({ page }) => {
  await page.goto("/");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("link", { name: /résumé/i }).first().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("integration-test-resume.pdf");
  expect(await download.failure()).toBeNull();
});

test("contact workflow preserves a clear success state", async ({ page }) => {
  await page.goto("/contact");
  await page.getByLabel(/Name/).fill("Production Path Check");
  await page.getByLabel(/Email/).fill(`playwright-${Date.now()}@example.com`);
  await page.getByLabel(/Organization/).fill("Synthetic Verification Lab");
  await page.getByLabel(/Conversation type/).click();
  await page.getByRole("option", { name: "Project", exact: true }).click();
  await page.getByLabel(/Subject/).fill("Canonical production path verification");
  await page.getByLabel(/Context/).fill("This synthetic inquiry verifies the real contact persistence path through the deployed edge, frontend, API, and database services.");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Send inquiry" }).click();
  await expect(page.getByText("Message received")).toBeVisible();
});

test("sponsor page keeps checkout on GitHub and submits a sponsorship inquiry", async ({ page }) => {
  await page.goto("/sponsor");
  await expect(
    page.getByRole("heading", { level: 2, name: "Support through GitHub Sponsors" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { level: 2, name: "Contact me about sponsorship" }),
  ).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Primary navigation" }).getByRole("link", {
      name: "Sponsor",
    }),
  ).toBeVisible();

  const checkout = page.getByRole("link", { name: "Open GitHub Sponsors" });
  await expect(checkout).toHaveAttribute(
    "href",
    "https://github.com/sponsors/yazeedhasan97",
  );
  await expect(checkout).toHaveAttribute("target", "_blank");
  await expect(checkout).toHaveAttribute(
    "rel",
    "sponsored nofollow noopener noreferrer",
  );
  await expect(
    page.getByText(/this website never receives, processes, or stores them/i),
  ).toBeVisible();

  const email = page.getByRole("link", { name: "Email about sponsorship" });
  await expect(email).toHaveAttribute(
    "href",
    /^mailto:sponsor@example\.com\?subject=Sponsorship%20inquiry&body=.*%0D%0A/,
  );
  await expect(page.locator('select[name="category_id"]')).toHaveValue("sponsorship");

  await page.getByLabel(/Name/).fill("Sponsor Path Check");
  await page.getByLabel(/Email/).fill(`sponsor-${Date.now()}@example.com`);
  await page.getByLabel(/Organization/).fill("Synthetic Sponsor Lab");
  await page.getByLabel(/Subject/).fill("Open-source maintenance sponsorship");
  await page
    .getByLabel(/Context/)
    .fill("This inquiry verifies the existing sponsorship contact path without sending payment data.");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Send sponsorship inquiry" }).click();
  await expect(page.getByText("Message received")).toBeVisible();
});

test("critical public pages have no serious automated accessibility violations", async ({ page }) => {
  for (const path of [
    "/",
    "/projects",
    "/projects/canonical-service-verification",
    "/writing/testing-the-canonical-path",
    "/contact",
    "/sponsor",
  ]) {
    await page.goto(path);
    const results = await new AxeBuilder({ page }).analyze();
    const violations = results.violations
      .filter((violation) => ["critical", "serious"].includes(violation.impact ?? ""))
      .map((violation) => ({ id: violation.id, targets: violation.nodes.map((node) => node.target) }));
    expect(violations, path).toEqual([]);
  }
});

test("metadata, structured data, and crawler surfaces use published authority", async ({ page, request }) => {
  await page.goto("/projects/canonical-service-verification");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    "href",
    `${canonicalOrigin}/projects/canonical-service-verification`,
  );
  await expect(page.locator('meta[property="og:title"]')).toHaveAttribute(
    "content",
    /Canonical Service Verification/,
  );
  await expect(page.locator('meta[name="twitter:card"]')).toHaveAttribute("content", /summary/);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /index/);
  const projectJsonLd = JSON.stringify(
    (await page.locator('script[type="application/ld+json"]').allTextContents())
      .map((value) => JSON.parse(value)),
  );
  expect(projectJsonLd).toContain("SoftwareSourceCode");
  expect(projectJsonLd).toContain("BreadcrumbList");
  expect(projectJsonLd).toContain(`${canonicalOrigin}/writing`);

  await page.goto("/sectors/verification-systems");
  await expect(page.getByRole("heading", { level: 1, name: "Verification Systems" })).toBeVisible();
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    "href",
    `${canonicalOrigin}/sectors/verification-systems`,
  );
  const sectorJsonLd = JSON.stringify(
    (await page.locator('script[type="application/ld+json"]').allTextContents())
      .map((value) => JSON.parse(value)),
  );
  expect(sectorJsonLd).toContain("WebPage");
  expect(sectorJsonLd).toContain("BreadcrumbList");
  expect(sectorJsonLd).toContain(`${canonicalOrigin}/projects/canonical-service-verification`);

  await page.goto("/");
  const homeJsonLd = JSON.stringify(
    (await page.locator('script[type="application/ld+json"]').allTextContents())
      .map((value) => JSON.parse(value)),
  );
  expect(homeJsonLd).toContain('"@type":"Person"');
  expect(homeJsonLd).toContain('"@type":"WebSite"');
  expect(homeJsonLd).toContain('"@type":"ProfilePage"');
  expect(homeJsonLd).not.toContain("https://example.com/integration-test-portfolio");

  const [sitemap, robots, llms] = await Promise.all([
    request.get("/sitemap.xml"),
    request.get("/robots.txt"),
    request.get("/llms.txt"),
  ]);
  expect(sitemap.ok()).toBe(true);
  expect(robots.ok()).toBe(true);
  expect(llms.ok()).toBe(true);
  const sitemapText = await sitemap.text();
  const robotsText = await robots.text();
  const llmsText = await llms.text();
  expect(sitemapText).toContain(`${canonicalOrigin}/projects/canonical-service-verification`);
  expect(sitemapText).toContain(`${canonicalOrigin}/sectors/verification-systems`);
  expect(sitemapText).toContain(`${canonicalOrigin}/writing/testing-the-canonical-path`);
  expect(sitemapText).not.toContain("private-draft-sentinel");
  expect(robotsText).toContain("Disallow: /admin/");
  expect(robotsText).toContain(`Sitemap: ${canonicalOrigin}/sitemap.xml`);
  expect(llmsText).toContain("Canonical Service Verification");
  expect(llmsText).toContain("Testing the Canonical Path");
  expect(llmsText).not.toContain("Private Draft Sentinel");
  expect(llmsText).not.toContain("Private Article Sentinel");
});

test("production edge enforces security and private API caching headers", async ({ request }) => {
  const [pageResponse, apiResponse] = await Promise.all([
    request.get("/"),
    request.get("/api/v1/public/homepage"),
  ]);
  for (const response of [pageResponse, apiResponse]) {
    const headers = response.headers();
    expect(headers["strict-transport-security"]).toContain("max-age=63072000");
    expect(headers["content-security-policy"]).toContain("default-src 'self'");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  }
  expect(apiResponse.headers()["cache-control"]).toContain("no-store");
  expect(apiResponse.headers()["x-robots-tag"]).toContain("noindex");
});

test("mobile layout preserves content and avoids horizontal overflow", async ({ browser }) => {
  const context = await browser.newContext({ ...devices["Pixel 7"], ignoreHTTPSErrors: true });
  const page = await context.newPage();
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: expectedName })).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);

  await page.goto("/sponsor");
  await expect(
    page.getByRole("heading", { level: 2, name: "Support through GitHub Sponsors" }),
  ).toBeVisible();
  const sponsorOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(sponsorOverflow).toBeLessThanOrEqual(1);
  await context.close();
});

test("cold production navigation stays inside the browser performance budget", async ({ page }) => {
  const failures = collectRuntimeFailures(page);
  const response = await page.goto("/", { waitUntil: "load" });
  expect(response?.status()).toBe(200);
  const timing = await page.evaluate(() => {
    const entry = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming;
    return {
      domContentLoadedMs: entry.domContentLoadedEventEnd,
      loadMs: entry.loadEventEnd,
      transferBytes: entry.transferSize,
    };
  });
  expect(timing.domContentLoadedMs).toBeLessThan(8_000);
  expect(timing.loadMs).toBeLessThan(10_000);
  expect(timing.transferBytes).toBeLessThan(1_500_000);
  expect(failures).toEqual([]);
});

test("reduced motion retains content and replaces the WebGL enhancement", async ({ browser }) => {
  const context = await browser.newContext({ ignoreHTTPSErrors: true, reducedMotion: "reduce" });
  const page = await context.newPage();
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: expectedName })).toBeVisible();
  await expect(page.locator("canvas")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Python" })).toBeVisible();
  await context.close();
});
