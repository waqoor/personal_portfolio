import { expect, test, type APIRequestContext, type BrowserContext, type Page } from "@playwright/test";

const CANONICAL_ORIGIN = "https://portfolio.example.com";

function requiredEnvironment(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for canonical admin E2E coverage.`);
  return value;
}

const adminEmail = requiredEnvironment("PORTFOLIO_E2E_ADMIN_EMAIL");
const adminPassword = requiredEnvironment("PORTFOLIO_E2E_ADMIN_PASSWORD");

async function signIn(page: Page) {
  await page.goto("/admin/login");
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Sign in securely" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: "Portfolio control room." })).toBeVisible();
}

async function csrfHeaders(context: BrowserContext): Promise<Record<string, string>> {
  const cookie = (await context.cookies()).find((item) => item.name === "portfolio_csrf");
  if (!cookie) throw new Error("The authenticated browser has no CSRF cookie.");
  return { "X-CSRF-Token": cookie.value };
}

async function sponsorshipId(request: APIRequestContext, title: string): Promise<string | undefined> {
  const response = await request.get("/api/v1/admin/engagement/sponsorship?limit=100&offset=0");
  expect(response.ok()).toBe(true);
  const payload = await response.json() as { items: Array<{ id: string; title: string }> };
  return payload.items.find((item) => item.title === title)?.id;
}

test.describe.configure({ mode: "serial" });

test("admin routes deny anonymous access and crawler indexing", async ({ page }) => {
  await page.goto("/admin");

  await expect(page).toHaveURL(/\/admin\/login$/);
  await expect(page.getByRole("navigation", { name: "Primary navigation" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Welcome back." })).toBeVisible();
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", /noindex/);
});

test("authenticated CMS changes flow through canonical services and public discovery", async ({ page }) => {
  await signIn(page);
  const request = page.context().request;

  await page.goto("/admin/homepage-sections");
  await expect(page.getByRole("heading", { name: "Homepage composition" })).toBeVisible();
  await page.getByRole("button", { name: "Save composition" }).click();
  await expect(page.getByText("Homepage composition saved.")).toBeVisible();

  await page.goto("/admin/site-settings");
  const siteName = page.getByLabel("Site name");
  const projectsTitle = page.getByLabel("Projects page title");
  const projectsIntro = page.getByLabel("Projects page introduction");
  const originalSiteName = await siteName.inputValue();
  const originalProjectsTitle = await projectsTitle.inputValue();
  const originalProjectsIntro = await projectsIntro.inputValue();
  try {
    await siteName.fill("E2E Metadata Verification");
    await projectsTitle.fill("E2E configured project archive");
    await projectsIntro.fill("A configured introduction shared by the visible page and discovery.");
    await page.getByRole("button", { name: "Save settings" }).click();
    await expect(page.getByText("Site and discovery defaults saved.")).toBeVisible();

    const discovery = await request.get("/api/v1/discovery/page?path=%2Fprojects");
    expect(discovery.ok()).toBe(true);
    const discoveryPayload = await discovery.json();
    expect(discoveryPayload.metadata.open_graph.site_name).toBe("E2E Metadata Verification");
    expect(discoveryPayload.metadata.title).toContain("E2E configured project archive");
    expect(discoveryPayload.metadata.description).toBe(
      "A configured introduction shared by the visible page and discovery.",
    );

    await page.goto("/projects");
    await expect(
      page.getByRole("heading", { level: 1, name: "E2E configured project archive" }),
    ).toBeVisible();
    await expect(page.locator('meta[property="og:site_name"]')).toHaveAttribute(
      "content",
      "E2E Metadata Verification",
    );
  } finally {
    await page.goto("/admin/site-settings");
    await page.getByLabel("Site name").fill(originalSiteName);
    await page.getByLabel("Projects page title").fill(originalProjectsTitle);
    await page.getByLabel("Projects page introduction").fill(originalProjectsIntro);
    await page.getByRole("button", { name: "Save settings" }).click();
    await expect(page.getByText("Site and discovery defaults saved.")).toBeVisible();
  }

  await page.goto("/admin/assistant-settings");
  const assistantSwitch = page.getByRole("switch").first();
  const assistantWasEnabled = await assistantSwitch.isChecked();
  try {
    if (!assistantWasEnabled) await assistantSwitch.click();
    await page.getByRole("button", { name: "Save assistant settings" }).click();
    await expect(page.getByText(/Assistant settings saved/)).toBeVisible();

    const homepageResponse = await request.get("/api/v1/public/homepage");
    expect(homepageResponse.ok()).toBe(true);
    expect((await homepageResponse.json()).features.assistant).toBe(false);
    await page.goto("/");
    await expect(page.getByRole("button", { name: "Ask my portfolio AI" })).toHaveCount(0);
  } finally {
    await page.goto("/admin/assistant-settings");
    const currentSwitch = page.getByRole("switch").first();
    if (await currentSwitch.isChecked()) await currentSwitch.click();
    await page.getByRole("button", { name: "Save assistant settings" }).click();
    await expect(page.getByText(/Assistant settings saved/)).toBeVisible();
  }

  const inboxSubmission = await request.post("/api/v1/contact", {
    headers: { "Idempotency-Key": "canonical-e2e-inbox-20260827" },
    data: {
      name: "Inbox Verification",
      email: "inbox-e2e@example.com",
      category: "project",
      organization: "Synthetic Verification Lab",
      subject: "Canonical inbox verification",
      message: "This persisted synthetic inquiry verifies the authenticated contact inbox workflow.",
      consent: true,
      website: "",
    },
  });
  expect(inboxSubmission.status()).toBe(202);

  await page.goto("/admin/contact-submissions");
  await expect(page.getByRole("heading", { name: "Contact submissions" })).toBeVisible();
  const editContact = page.getByRole("button", { name: /Edit Canonical inbox verification/i }).first();
  await expect(editContact).toBeVisible();
  await editContact.click();
  const contactDialog = page.getByRole("dialog");
  await contactDialog.getByLabel("Inbox status").click();
  await page.getByRole("option", { name: "Read" }).click();
  await contactDialog.getByRole("button", { name: "Save contact submission" }).click();
  await expect(contactDialog).toHaveCount(0);

  const inbox = await request.get("/api/v1/admin/engagement/contact-submissions?limit=100&offset=0");
  expect(inbox.ok()).toBe(true);
  const inboxPayload = await inbox.json() as { items: Array<{ subject: string; status: string }> };
  expect(inboxPayload.items.find((item) => item.subject === "Canonical inbox verification")?.status).toBe("read");

  const unique = Date.now().toString(36);
  const sponsorTitle = `E2E Sponsor ${unique}`;
  let createdSponsorId: string | undefined;
  try {
    await page.goto("/admin/sponsorship");
    await expect(page.getByRole("heading", { name: "Sponsorship" })).toBeVisible();
    await page.getByRole("button", { name: "New sponsorship option" }).click();
    const sponsorDialog = page.getByRole("dialog");
    await sponsorDialog.getByLabel("Title").fill(sponsorTitle);
    await sponsorDialog.getByLabel("Slug").fill(`e2e-sponsor-${unique}`);
    await sponsorDialog.getByLabel("Description").fill("Synthetic published sponsorship used only for the canonical E2E journey.");
    await sponsorDialog.getByLabel("Kind").fill("external");
    await sponsorDialog.getByLabel("CTA label").fill("Open verification sponsor");
    await sponsorDialog.getByLabel("HTTPS destination").fill("https://example.com/e2e-sponsor");
    await sponsorDialog.getByLabel("Display order").fill("1");
    await sponsorDialog.getByLabel("Published").check();
    await sponsorDialog.getByLabel("Mark link sponsored/nofollow").check();
    await sponsorDialog.getByRole("button", { name: "Save sponsorship option" }).click();
    await expect(sponsorDialog).toHaveCount(0);
    await expect(page.getByText(sponsorTitle).first()).toBeVisible();

    createdSponsorId = await sponsorshipId(request, sponsorTitle);
    expect(createdSponsorId).toBeTruthy();
    const publicOptions = await request.get("/api/v1/sponsorship");
    expect((await publicOptions.json()).items).toEqual(
      expect.arrayContaining([expect.objectContaining({ title: sponsorTitle, rel: "sponsored nofollow noopener" })]),
    );
    expect(await (await request.get("/sitemap.xml")).text()).toContain(`${CANONICAL_ORIGIN}/sponsor`);

    await page.goto("/sponsorship");
    await expect(page.getByRole("link", { name: "Open verification sponsor" })).toBeVisible();

    await page.goto("/admin/sponsorship");
    await page.getByRole("button", { name: `Archive ${sponsorTitle}` }).click();
    const archiveDialog = page.getByRole("dialog");
    await archiveDialog.getByRole("button", { name: "Archive", exact: true }).click();
    await expect(archiveDialog).toHaveCount(0);
    createdSponsorId = undefined;

    expect((await (await request.get("/api/v1/sponsorship")).json()).items).toEqual([]);
    expect(await (await request.get("/sitemap.xml")).text()).toContain(`${CANONICAL_ORIGIN}/sponsor`);
    await page.goto("/sponsorship");
    await expect(page.getByRole("heading", { name: "The gateway is intentionally not guessed." })).toBeVisible();
  } finally {
    createdSponsorId ??= await sponsorshipId(request, sponsorTitle);
    if (createdSponsorId) {
      await request.delete(`/api/v1/admin/engagement/sponsorship/${createdSponsorId}`, {
        headers: await csrfHeaders(page.context()),
      });
    }
  }
});
