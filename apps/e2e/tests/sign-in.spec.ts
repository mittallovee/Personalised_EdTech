import { expect, test } from "@playwright/test";

import { admin } from "./helpers";

// M1 web flow (B-01, B-03, B-04): sign in, see Home, sign out.

test("a signed-out visitor is sent to the sign-in page", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
});

test("a wrong password shows one general message", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[name="email"]', admin.email);
  await page.fill('input[name="password"]', "wrong-password-1");
  await page.click('button[type="submit"]');

  // `form [role=alert]`: Next.js has its own hidden alert region for page changes.
  await expect(page.locator('form [role="alert"]')).toContainText(/incorrect/i);
  await expect(page).toHaveURL(/\/login$/);
});

test("sign in, stay signed in after a reload, sign out", async ({ page }) => {
  await page.goto("/login");
  await page.fill('input[name="email"]', admin.email);
  await page.fill('input[name="password"]', admin.password);
  await page.click('button[type="submit"]');

  await expect(page.getByRole("heading", { name: /^Welcome, / })).toBeVisible();
  await expect(page.getByText("Signed in as Platform admin.")).toBeVisible();
  await expect(page.locator("dd", { hasText: /^ok$/ }).first()).toBeVisible(); // system health
  const session = (await page.context().cookies()).find((c) => c.name === "qb_session");
  expect(session?.httpOnly).toBe(true); // page scripts cannot read the session

  await page.reload();
  await expect(page.getByRole("heading", { name: /^Welcome, / })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await page.request.get("/api/v1/me")).status()).toBe(401);
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
});
