import { expect, test } from "@playwright/test";

import { activate, coaching, platformAdminContext, signedInOwner, unique } from "./helpers";

// M2 (A-04, A-05, A-06, A-07): the platform admin's Coachings screen and the acting banner.

test("the platform admin creates a coaching and its Owner activates", async ({
  browser,
  baseURL,
}) => {
  const staff = await (await platformAdminContext(browser, baseURL!)).newPage();
  await staff.goto("/platform/coachings");
  await expect(staff.getByRole("heading", { name: "Coachings", exact: true })).toBeVisible();
  const name = `Platform Classes ${unique()}`;

  await staff.fill('input[name="display_name"]', name);
  await staff.fill('input[name="owner_name"]', "Priya Sharma");
  await staff.fill('input[name="owner_email"]', `priya-${unique()}@example.com`);
  await staff.getByRole("button", { name: "Create coaching and make the Owner's link" }).click();

  const notice = staff.getByRole("status", { name: "Activation link for Priya Sharma" });
  await expect(notice).toBeVisible();
  const link = await notice.getByLabel("Link").inputValue();
  expect(link).toContain("/activate#");
  await expect(coaching(staff, name)).toContainText("Active");
  await expect(coaching(staff, name)).toContainText("Asia/Kolkata");

  const owner = await activate(browser, link, "Priya Sharma");
  await expect(owner.locator("header")).toContainText(name); // A-05: the coaching's name
});

test("renaming a coaching shows the new name to its people", async ({ browser, baseURL }) => {
  const name = `Rename Classes ${unique()}`;
  const { context } = await signedInOwner(browser, baseURL!, name);
  const staff = await (await platformAdminContext(browser, baseURL!)).newPage();
  await staff.goto("/platform/coachings");

  await coaching(staff, name).getByRole("button", { name: "Rename or change time zone" }).click();
  const newName = `${name} Renamed`;
  const form = coaching(staff, name).getByRole("form");
  await form.getByLabel("Name").fill(newName);
  await form.getByLabel("Time zone").fill("Asia/Dubai");
  await form.getByRole("button", { name: "Save" }).click();

  await expect(staff.getByRole("status")).toHaveText(`${newName} was saved.`);
  await expect(coaching(staff, newName)).toContainText("Asia/Dubai");
  const owner = await context.newPage();
  await owner.goto("/");
  await expect(owner.locator("header")).toContainText(newName);
});

test("suspending a coaching signs its people out; reactivating lets them back", async ({
  browser,
  baseURL,
}) => {
  const name = `Suspend Classes ${unique()}`;
  const { context } = await signedInOwner(browser, baseURL!, name);
  const staff = await (await platformAdminContext(browser, baseURL!)).newPage();
  await staff.goto("/platform/coachings");
  const card = coaching(staff, name);

  await card.getByRole("button", { name: "Suspend" }).click();
  const confirm = card.getByRole("region", { name: `Suspend ${name}?` });
  await expect(confirm).toContainText("signed out");
  await confirm.getByRole("button", { name: "Suspend" }).click();

  await expect(staff.getByRole("status")).toHaveText(
    `${name} is suspended. Its people are signed out.`,
  );
  await expect(card).toContainText("Suspended");
  expect((await context.request.get("/api/v1/me")).status()).toBe(401);

  await card.getByRole("button", { name: "Reactivate" }).click();
  await expect(staff.getByRole("status")).toHaveText(
    `${name} is active again. Its people can sign in.`,
  );
  await expect(card).toContainText("Active");
});

test("acting in a coaching shows a banner until the platform admin stops", async ({
  browser,
  baseURL,
}) => {
  const name = `Acting Classes ${unique()}`;
  const { ownerName } = await signedInOwner(browser, baseURL!, name);
  const staff = await (await platformAdminContext(browser, baseURL!)).newPage();
  await staff.goto("/platform/coachings");
  await expect(staff.getByRole("region", { name: "Acting in a coaching" })).toHaveCount(0);

  await coaching(staff, name).getByRole("button", { name: "Act in" }).click();

  await expect(staff).toHaveURL(/\/admin\/users$/);
  const banner = staff.getByRole("region", { name: "Acting in a coaching" });
  await expect(banner).toContainText(`Acting in ${name}`);
  await expect(staff.getByRole("list", { name: "Members" })).toContainText(ownerName);

  await banner.getByRole("button", { name: "Stop acting" }).click();

  await expect(staff).toHaveURL(/\/platform\/coachings$/);
  await expect(banner).toHaveCount(0);
  await expect(staff.getByRole("link", { name: "Users & grants" })).toHaveCount(0);
});

test("an out-of-date tab cannot overwrite a newer rename", async ({ browser, baseURL }) => {
  const name = `Stale Platform ${unique()}`;
  await signedInOwner(browser, baseURL!, name);
  const context = await platformAdminContext(browser, baseURL!);
  const first = await context.newPage();
  await first.goto("/platform/coachings");
  const second = await context.newPage();
  await second.goto("/platform/coachings");

  // The second tab renames it first.
  await coaching(second, name).getByRole("button", { name: "Rename or change time zone" }).click();
  const renamed = `${name} Two`;
  await coaching(second, name).getByLabel("Name").fill(renamed);
  await coaching(second, name).getByRole("button", { name: "Save" }).click();
  await expect(second.getByRole("status")).toHaveText(`${renamed} was saved.`);

  // The first tab still shows the old name and tries to rename it too.
  await coaching(first, name).getByRole("button", { name: "Rename or change time zone" }).click();
  await coaching(first, name).getByLabel("Name").fill(`${name} One`);
  await coaching(first, name).getByRole("button", { name: "Save" }).click();

  await expect(
    first.getByRole("alert").filter({ hasText: "Someone else changed this" }),
  ).toBeVisible();
  await expect(coaching(first, renamed)).toBeVisible(); // reloaded: it shows the newer name
});
