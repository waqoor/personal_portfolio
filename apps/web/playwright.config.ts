import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PORTFOLIO_E2E_BASE_URL ?? "http://localhost:18444";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "../../output/playwright/test-results",
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  timeout: 45_000,
  expect: { timeout: 10_000 },
  reporter: [
    ["html", { outputFolder: "../../output/playwright/report", open: "never" }],
    ["list"],
  ],
  use: {
    baseURL,
    ignoreHTTPSErrors: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium-production", use: { ...devices["Desktop Chrome"] } },
  ],
});
