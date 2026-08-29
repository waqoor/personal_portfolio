import { expect, test } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { deflateSync } from "node:zlib";

const CANONICAL_ORIGIN = "https://portfolio.example.com";
const PROFILE_NAME = "Clean Bootstrap Portfolio";
const RUN_CLEAN_BOOTSTRAP = process.env.PORTFOLIO_E2E_CLEAN_BOOTSTRAP === "1";
const RESUME_PATH = fileURLToPath(
  new URL("../../../tests/fixtures/e2e/resume.pdf", import.meta.url),
);

function crc32(input: Buffer): number {
  let crc = 0xffffffff;
  for (const byte of input) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function pngChunk(type: string, data: Buffer): Buffer {
  const kind = Buffer.from(type, "ascii");
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length);
  const checksum = Buffer.alloc(4);
  checksum.writeUInt32BE(crc32(Buffer.concat([kind, data])));
  return Buffer.concat([length, kind, data, checksum]);
}

function syntheticPortraitPng(width = 640, height = 800): Buffer {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr.set([8, 2, 0, 0, 0], 8);

  const scanlineLength = 1 + width * 3;
  const pixels = Buffer.alloc(scanlineLength * height);
  for (let y = 0; y < height; y += 1) {
    const row = y * scanlineLength;
    pixels[row] = 0;
    for (let x = 0; x < width; x += 1) {
      const pixel = row + 1 + x * 3;
      pixels[pixel] = 37 + Math.floor((x / width) * 90);
      pixels[pixel + 1] = 75 + Math.floor((y / height) * 100);
      pixels[pixel + 2] = 95 + Math.floor(((x + y) / (width + height)) * 90);
    }
  }
  return Buffer.concat([
    Buffer.from("89504e470d0a1a0a", "hex"),
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", deflateSync(pixels, { level: 9 })),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

const PORTRAIT_PNG = syntheticPortraitPng();

function requiredEnvironment(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required for clean bootstrap E2E coverage.`);
  return value;
}

test.describe.configure({ mode: "serial" });

test("clean owner bootstraps a reviewed identity and publishes every public boundary", async ({
  page,
}) => {
  test.skip(
    !RUN_CLEAN_BOOTSTRAP,
    "This destructive first-run journey requires a dedicated empty database.",
  );

  const adminEmail = requiredEnvironment("PORTFOLIO_E2E_ADMIN_EMAIL");
  const adminPassword = requiredEnvironment("PORTFOLIO_E2E_ADMIN_PASSWORD");
  const request = page.context().request;

  const unavailableHomepage = await request.get("/api/v1/public/homepage");
  expect(unavailableHomepage.status()).toBe(200);
  expect(await unavailableHomepage.json()).toMatchObject({
    profile: null,
    current_resume: null,
    sections: [],
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "The studio is here. Its live archive is reconnecting.",
    }),
  ).toBeVisible();

  await page.goto("/admin/login");
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Password").fill(adminPassword);
  await page.getByRole("button", { name: "Sign in securely" }).click();
  await expect(page).toHaveURL(/\/admin$/);

  await page.goto("/admin/profile");
  await expect(page.getByRole("button", { name: "New profile" })).toBeEnabled();
  await page.getByRole("button", { name: "New profile" }).click();
  const profileDialog = page.getByRole("dialog");
  await profileDialog.getByLabel("Public name *").fill(PROFILE_NAME);
  await profileDialog
    .getByLabel("Headline *")
    .fill("Production-ready identity verified end to end");
  await profileDialog
    .getByLabel("Short biography *")
    .fill("Synthetic identity used only to verify the clean production bootstrap journey.");
  await profileDialog
    .getByLabel("Long biography")
    .fill("The owner reviews this draft, attaches validated assets, and publishes it explicitly.");
  await profileDialog.getByLabel("Public location").fill("Test environment");
  await profileDialog
    .getByLabel("Availability detail")
    .fill("Available for automated production-path verification.");
  await profileDialog.getByLabel("Primary CTA label").fill("Review test work");
  await profileDialog
    .getByLabel("Primary CTA URL")
    .fill("https://example.com/clean-bootstrap-work");
  await profileDialog.getByRole("button", { name: "Save profile" }).click();
  await expect(profileDialog).toHaveCount(0);

  let profileRow = page.getByRole("row").filter({ hasText: PROFILE_NAME });
  await expect(profileRow).toContainText("draft");
  await expect(page.getByRole("button", { name: "New profile" })).toHaveCount(0);

  await page.goto("/admin/resumes");
  await expect(
    page.getByRole("heading", { name: /Portraits, résumé & socials/i }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Upload portrait" }).click();
  let assetDialog = page.getByRole("dialog");
  await assetDialog.getByLabel("Image").setInputFiles({
    name: "clean-bootstrap-portrait.png",
    mimeType: "image/png",
    buffer: PORTRAIT_PNG,
  });
  await assetDialog
    .getByLabel("Alternative text")
    .fill("Synthetic portrait used for clean bootstrap verification");
  await assetDialog.getByLabel("Make primary now").check();
  await assetDialog.getByRole("button", { name: "Upload portrait" }).click();
  await expect(page.getByText("Portrait uploaded and validated.")).toBeVisible();
  await expect(page.getByText("Primary", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Upload PDF version" }).click();
  assetDialog = page.getByRole("dialog");
  await assetDialog.getByLabel("PDF file").setInputFiles(RESUME_PATH);
  await assetDialog.getByLabel("Version label").fill("Clean bootstrap v1");
  await assetDialog.getByLabel("Effective date").fill("2026-08-28");
  await assetDialog
    .getByLabel("Public download filename")
    .fill("clean-bootstrap-resume.pdf");
  await assetDialog.getByRole("button", { name: "Upload version" }).click();
  await expect(page.getByText(/Résumé version uploaded/)).toBeVisible();
  await expect(page.getByText("Clean bootstrap v1", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Publish profile first" })).toBeDisabled();

  await page.goto("/admin/profile");
  profileRow = page.getByRole("row").filter({ hasText: PROFILE_NAME });
  await profileRow.getByRole("button", { name: `Edit ${PROFILE_NAME}` }).click();
  const reviewDialog = page.getByRole("dialog");
  await expect(reviewDialog.getByLabel("Public name *")).toHaveValue(PROFILE_NAME);
  await expect(reviewDialog.getByLabel("Primary CTA URL")).toHaveValue(
    "https://example.com/clean-bootstrap-work",
  );
  await reviewDialog.getByRole("button", { name: "Cancel" }).click();
  await profileRow.getByRole("button", { name: `Publish ${PROFILE_NAME}` }).click();
  await expect(profileRow).toContainText("published");

  await page.goto("/admin/resumes");
  await page.getByRole("button", { name: "Publish current" }).click();
  await expect(page.getByText("Current", { exact: true })).toBeVisible();

  await page.goto("/admin/homepage-sections");
  await page.getByLabel("Add a supported module").click();
  await page.getByRole("option", { name: "Hero / personal identity" }).click();
  await page.getByRole("button", { name: "Add module" }).click();
  await page.getByRole("button", { name: "Save composition" }).click();
  await expect(page.getByText("Homepage composition saved.")).toBeVisible();

  const homepage = await request.get("/api/v1/public/homepage");
  expect(homepage.status()).toBe(200);
  const homepagePayload = (await homepage.json()) as {
    profile: { full_name: string; portraits: Array<{ is_primary: boolean }> };
    current_resume: { download_name: string; is_current: boolean };
    sections: Array<{ section: { section_type: string } }>;
  };
  expect(homepagePayload.profile.full_name).toBe(PROFILE_NAME);
  expect(homepagePayload.profile.portraits).toEqual(
    expect.arrayContaining([expect.objectContaining({ is_primary: true })]),
  );
  expect(homepagePayload.current_resume).toMatchObject({
    download_name: "clean-bootstrap-resume.pdf",
    is_current: true,
  });
  expect(homepagePayload.sections).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ section: expect.objectContaining({ section_type: "hero" }) }),
    ]),
  );

  await page.goto("/");
  await expect(page.getByRole("heading", { name: PROFILE_NAME })).toBeVisible();
  const portrait = page.getByAltText(
    "Synthetic portrait used for clean bootstrap verification",
  );
  await expect(portrait).toBeVisible();
  await expect.poll(() => portrait.evaluate((image) => (image as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);

  const resume = await request.get("/resume");
  expect(resume.status()).toBe(200);
  expect(resume.headers()["content-type"]).toContain("application/pdf");
  expect(resume.headers()["content-disposition"]).toContain("clean-bootstrap-resume.pdf");

  const discovery = await request.get("/api/v1/discovery/page?path=%2F");
  expect(discovery.status()).toBe(200);
  const discoveryPayload = (await discovery.json()) as {
    metadata: { canonical_url: string };
    json_ld: { "@graph": Array<{ "@type": string }> };
  };
  expect(discoveryPayload.metadata.canonical_url).toBe(`${CANONICAL_ORIGIN}/`);
  expect(discoveryPayload.json_ld["@graph"]).toEqual(
    expect.arrayContaining([expect.objectContaining({ "@type": "Person" })]),
  );
  expect(await (await request.get("/sitemap.xml")).text()).toContain(
    `<loc>${CANONICAL_ORIGIN}/</loc>`,
  );
  expect(await (await request.get("/llms.txt")).text()).toContain(PROFILE_NAME);
});
