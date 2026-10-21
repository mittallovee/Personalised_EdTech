import { expect, test } from "@playwright/test";

import { createCoaching, setPassword, unique } from "./helpers";

// M2 (B-05, A-05, T16): a new coaching's Owner opens the activation link and sets a password.

test("the Owner activates the account and lands on Home", async ({ browser, baseURL }) => {
  const coaching = `Sharma Classes ${unique()}`;
  const adminContext = await browser.newContext();
  const { token, ownerName } = await createCoaching(adminContext.request, baseURL!, coaching);
  await adminContext.close();

  // A browser that has never signed in, as the Owner's would be.
  const page = await (await browser.newContext()).newPage();
  await page.goto(`/activate#${token}`);
  await expect(page.getByRole("heading", { name: "Set your password" })).toBeVisible();
  await expect(page).not.toHaveURL(/#/); // the token is removed from the address bar

  await setPassword(page, "a brand new passphrase", "a different passphrase");
  await expect(page.locator('form [role="alert"]')).toContainText(/different/i);

  await setPassword(page, "a brand new passphrase");
  await expect(page.getByRole("heading", { name: `Welcome, ${ownerName}` })).toBeVisible();
  await expect(page.getByText("Signed in as owner in your coaching.")).toBeVisible();
  await expect(page.locator("header", { hasText: coaching })).toBeVisible();

  // The same link a second time, in another browser, is refused.
  const again = await (await browser.newContext()).newPage();
  await again.goto(`/activate#${token}`);
  await setPassword(again, "yet another passphrase");
  await expect(again.locator('form [role="alert"]')).toContainText(/not valid/i);
});

test("the page without a link explains what to do", async ({ page }) => {
  await page.goto("/activate");
  await expect(page.locator('main [role="alert"]')).toContainText(/full link/i);
});
