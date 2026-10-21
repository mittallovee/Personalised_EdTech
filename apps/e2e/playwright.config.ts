import { defineConfig, devices } from "@playwright/test";

/**
 * Browser tests: a real Chromium drives the running app (`docker compose up`), the way a person
 * would. They need a platform admin account; see apps/e2e/README.md.
 */
export default defineConfig({
  testDir: "./tests",
  // The tests share one database, so run them one at a time and in a predictable order.
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0, // a failure is a bug to fix, not something to retry away
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
