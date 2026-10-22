import { expect, test } from "@playwright/test";

import {
  actingPlatformAdmin,
  activate,
  coaching,
  csrfOf,
  platformAdminContext,
  signedInOwner,
  unique,
} from "./helpers";

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

test("renaming the coaching you are acting in updates the banner", async ({ browser, baseURL }) => {
  const name = `Banner Classes ${unique()}`;
  const { context } = await signedInOwner(browser, baseURL!, name);
  const organizationId = (await (await context.request.get("/api/v1/me")).json()).organization.id;
  const staff = await (await actingPlatformAdmin(browser, baseURL!, organizationId)).newPage();
  await staff.goto("/admin/users");
  await staff.getByRole("link", { name: "Coachings" }).click(); // still acting, on the platform list

  await coaching(staff, name).getByRole("button", { name: "Rename or change time zone" }).click();
  const newName = `${name} Renamed`;
  await coaching(staff, name).getByLabel("Name").fill(newName);
  await coaching(staff, name).getByRole("button", { name: "Save" }).click();

  await expect(staff.getByRole("status")).toHaveText(`${newName} was saved.`);
  await expect(staff.getByRole("region", { name: "Acting in a coaching" })).toContainText(
    `Acting in ${newName}`,
  );
});

test("stopping acting after the session has ended sends you to sign in", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Expired Classes ${unique()}`);
  const organizationId = (await (await context.request.get("/api/v1/me")).json()).organization.id;
  const staffContext = await actingPlatformAdmin(browser, baseURL!, organizationId);
  const staff = await staffContext.newPage();
  await staff.goto("/admin/users");
  await expect(staff.getByRole("region", { name: "Acting in a coaching" })).toBeVisible();
  // The same sign-in ends elsewhere (another tab, or it expired).
  const ended = await staffContext.request.post("/api/v1/auth/logout", {
    headers: { Origin: baseURL!, "X-CSRF-Token": await csrfOf(staffContext) },
  });
  expect(ended.ok()).toBe(true);

  await staff.getByRole("button", { name: "Stop acting" }).click();

  await expect(staff).toHaveURL(/\/login$/);
});

test("creating a coaching or acting in one after the session has ended sends you to sign in", async ({
  browser,
  baseURL,
}) => {
  const name = `Ended Classes ${unique()}`;
  await signedInOwner(browser, baseURL!, name);
  for (const action of ["create", "act in"] as const) {
    const staffContext = await platformAdminContext(browser, baseURL!);
    const staff = await staffContext.newPage();
    await staff.goto("/platform/coachings");
    await expect(coaching(staff, name)).toBeVisible();
    // The same sign-in ends elsewhere (another tab, or it expired).
    const ended = await staffContext.request.post("/api/v1/auth/logout", {
      headers: { Origin: baseURL!, "X-CSRF-Token": await csrfOf(staffContext) },
    });
    expect(ended.ok()).toBe(true);

    if (action === "create") {
      await staff.fill('input[name="display_name"]', `Never Created ${unique()}`);
      await staff.fill('input[name="owner_name"]', "Nobody");
      await staff.fill('input[name="owner_email"]', `nobody-${unique()}@example.com`);
      await staff
        .getByRole("button", { name: "Create coaching and make the Owner's link" })
        .click();
    } else {
      await coaching(staff, name).getByRole("button", { name: "Act in" }).click();
    }

    await expect(staff).toHaveURL(/\/login$/);
  }
});

test("sending you to sign in replaces the console in the browser history", async ({
  browser,
  baseURL,
}) => {
  const name = `Back Classes ${unique()}`;
  await signedInOwner(browser, baseURL!, name);
  const staffContext = await platformAdminContext(browser, baseURL!);
  const staff = await staffContext.newPage();
  await staff.goto("/platform/coachings");
  await expect(coaching(staff, name)).toBeVisible();
  const entriesBefore = await staff.evaluate(() => window.history.length);
  const ended = await staffContext.request.post("/api/v1/auth/logout", {
    headers: { Origin: baseURL!, "X-CSRF-Token": await csrfOf(staffContext) },
  });
  expect(ended.ok()).toBe(true);

  await coaching(staff, name).getByRole("button", { name: "Act in" }).click();
  await expect(staff).toHaveURL(/\/login$/);

  // Back must not be able to restore the console of the ended session (browsers may keep a
  // page in memory for Back), so the sign-in page takes the console's place in the history.
  expect(await staff.evaluate(() => window.history.length)).toBe(entriesBefore);
});

test("pressing Show more twice on the coachings list loads the next page once", async ({
  browser,
  baseURL,
}) => {
  test.setTimeout(120_000);
  const context = await platformAdminContext(browser, baseURL!);
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  // Enough coachings that the list has a second page, however many earlier runs left behind.
  for (let n = 0; n < 51; n++) {
    const response = await context.request.post("/api/v1/platform/organizations", {
      headers,
      data: {
        display_name: `Many ${n} ${unique()}`,
        timezone: "Asia/Kolkata",
        owner: { email: `many${n}-${unique()}@example.com`, display_name: "Owner" },
      },
    });
    expect(response.status()).toBe(201);
  }
  const page = await context.newPage();
  let nextPageRequests = 0;
  await page.route("**/api/v1/platform/organizations?*cursor=*", async (route) => {
    nextPageRequests += 1;
    await new Promise((resolve) => setTimeout(resolve, 800)); // a slow connection
    await route.continue();
  });
  await page.goto("/platform/coachings");
  const cards = page.getByRole("list", { name: "Coachings" }).getByRole("listitem");
  await expect(cards).toHaveCount(50);

  await page.getByRole("button", { name: "Show more" }).dblclick();

  await expect(cards).not.toHaveCount(50); // the next page arrived
  const names = await cards.locator("span.font-medium").allTextContents();
  expect(new Set(names).size).toBe(names.length); // nobody twice
  expect(nextPageRequests).toBe(1);
});
