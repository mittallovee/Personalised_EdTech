import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import {
  activate,
  actingPlatformAdmin,
  csrfOf,
  platformAdminContext,
  signedInOwner,
  unique,
} from "./helpers";

/** The events on the audit log page. */
function events(page: Page) {
  // Direct children only: each event also holds a nested list of its changes.
  return page.getByRole("list", { name: "Events" }).locator(":scope > li");
}

/** Invite someone through the API; returns what the tests need to change or activate them. */
async function inviteByApi(
  context: BrowserContext,
  baseURL: string,
  name: string,
  role: "FACULTY" | "ADMIN" = "FACULTY",
) {
  const response = await context.request.post("/api/v1/members/invitations", {
    headers: { Origin: baseURL, "X-CSRF-Token": await csrfOf(context) },
    data: { email: `${role.toLowerCase()}-${unique()}@example.com`, display_name: name, role },
  });
  expect(response.status()).toBe(201);
  const body = await response.json();
  return {
    membershipId: body.member.membership_id as string,
    revision: body.member.revision as number,
    link: `${baseURL}/activate#${body.activation.token as string}`,
  };
}

test("the Owner sees who changed what, and when, with before and after", async ({
  browser,
  baseURL,
}) => {
  const { context, ownerName } = await signedInOwner(browser, baseURL!, `Audit ${unique()}`);
  const faculty = await inviteByApi(context, baseURL!, "Anita Rao");
  const granted = await context.request.put(`/api/v1/members/${faculty.membershipId}/grants`, {
    headers: {
      Origin: baseURL!,
      "X-CSRF-Token": await csrfOf(context),
      "If-Match": `"rev-${faculty.revision}"`,
    },
    data: { grants: ["QC"] },
  });
  expect(granted.ok()).toBe(true);

  const page = await context.newPage();
  await page.goto("/admin/audit");

  await expect(page.getByRole("heading", { name: "Audit log" })).toBeVisible();
  // Newest first: the grants change is above the invitation.
  const change = events(page).filter({ hasText: "Member grants changed" });
  await expect(change).toHaveCount(1);
  await expect(change).toContainText(ownerName);
  await expect(change).toContainText("Grants: none → Quality check");
  await expect(change.locator("time")).toHaveCount(1);
  await expect(events(page).first()).toContainText("Member grants changed");
  await expect(events(page).filter({ hasText: "Member invited" })).toContainText(ownerName);
});

test("filters narrow the list by kind, by person and by date", async ({ browser, baseURL }) => {
  const { context, ownerName } = await signedInOwner(browser, baseURL!, `Filters ${unique()}`);
  const faculty = await inviteByApi(context, baseURL!, "Anita Rao");
  await activate(browser, faculty.link, "Anita Rao");
  const page = await context.newPage();
  await page.goto("/admin/audit");
  const invited = events(page).filter({ hasText: "Member invited" });
  const activated = events(page).filter({ hasText: "Account activated" });
  await expect(invited).toHaveCount(1);
  await expect(activated).toHaveCount(2); // the Owner's and Anita's

  // By kind: invitations are about memberships, not accounts.
  await page.getByLabel("Kind").selectOption("membership");
  await expect(activated).toHaveCount(0);
  await expect(invited).toHaveCount(1);
  await page.getByLabel("Kind").selectOption("");
  await expect(activated).toHaveCount(2);

  // By person: only what Anita did herself (activating, and signing in with it).
  await activated
    .filter({ hasText: "Anita Rao" })
    .getByRole("button", { name: "Only this person" })
    .click();
  await expect(page.getByRole("list", { name: "Active filters" })).toContainText("Anita Rao");
  await expect(invited).toHaveCount(0);
  await expect(events(page).filter({ hasNotText: "By Anita Rao" })).toHaveCount(0);
  await expect(activated).toHaveCount(1);
  await page.getByRole("button", { name: "Show everyone" }).click();
  await expect(invited).toHaveCount(1);
  await expect(page.getByRole("list", { name: "Active filters" })).toHaveCount(0);

  // By record: everything that happened to Anita's membership.
  await invited.getByRole("button", { name: "Only this record" }).click();
  await expect(events(page)).toHaveCount(1);
  await page.getByRole("button", { name: "Show all records" }).click();
  await expect(activated).toHaveCount(2);

  // By date: nothing happened tomorrow, and nothing happened before today.
  const [today, tomorrow, yesterday] = await page.evaluate(() => {
    const day = (offset: number) => {
      const date = new Date();
      date.setDate(date.getDate() + offset);
      const pad = (n: number) => String(n).padStart(2, "0");
      return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
    };
    return [day(0), day(1), day(-1)];
  });
  await page.getByLabel("From").fill(tomorrow!);
  await expect(page.getByText("No events match these filters.")).toBeVisible();
  await page.getByLabel("From").fill(today!);
  await expect(invited).toHaveCount(1);
  await page.getByLabel("From").fill("");
  await page.getByLabel("To").fill(yesterday!);
  await expect(page.getByText("No events match these filters.")).toBeVisible();
  await page.getByLabel("To").fill(today!); // the whole of today is included
  await expect(invited).toHaveCount(1);
  expect(ownerName).toBeTruthy();
});

test("faculty cannot open the audit log", async ({ browser, baseURL }) => {
  const { context } = await signedInOwner(browser, baseURL!, `No Access ${unique()}`);
  const faculty = await inviteByApi(context, baseURL!, "Anita Rao");
  const page = await activate(browser, faculty.link, "Anita Rao");
  await expect(page.getByRole("link", { name: "Audit log" })).toHaveCount(0);

  await page.goto("/admin/audit");

  await expect(page.getByText("You don't have access to this page.")).toBeVisible();
  await expect(events(page)).toHaveCount(0);
});

test("a platform admin reads a coaching's audit log while acting in it, and the platform's own otherwise", async ({
  browser,
  baseURL,
}) => {
  const name = `Platform View ${unique()}`;
  const { context, ownerName } = await signedInOwner(browser, baseURL!, name);
  const organizationId = (await (await context.request.get("/api/v1/me")).json()).organization.id;

  const acting = await (await actingPlatformAdmin(browser, baseURL!, organizationId)).newPage();
  await acting.goto("/admin/audit");
  await expect(acting.getByRole("region", { name: "Acting in a coaching" })).toBeVisible();
  await expect(events(acting).filter({ hasText: "Account activated" })).toContainText(ownerName);

  const own = await (await platformAdminContext(browser, baseURL!)).newPage();
  await own.goto("/admin/audit");
  await expect(own.getByRole("heading", { name: "Audit log" })).toBeVisible();
  await expect(own.getByText("You don't have access to this page.")).toHaveCount(0);
  // Only platform-level events, never a coaching's.
  await expect(events(own).filter({ hasText: ownerName })).toHaveCount(0);
});

test("pressing Show more twice on a slow connection loads the next page once", async ({
  browser,
  baseURL,
}) => {
  test.setTimeout(90_000);
  const { context } = await signedInOwner(browser, baseURL!, `Many Events ${unique()}`);
  for (let n = 0; n < 52; n++) await inviteByApi(context, baseURL!, `Person ${n}`);
  // The true number of events, counted through the API a page at a time.
  let total = 0;
  for (let cursor = ""; ;) {
    const response = await context.request.get(
      `/api/v1/audit-events?limit=100${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""}`,
    );
    const body = await response.json();
    total += body.data.length;
    if (!body.page.next_cursor) break;
    cursor = body.page.next_cursor;
  }
  expect(total).toBeGreaterThan(50); // more than one page
  const page = await context.newPage();
  let nextPageRequests = 0;
  await page.route("**/api/v1/audit-events?*cursor=*", async (route) => {
    nextPageRequests += 1;
    await new Promise((resolve) => setTimeout(resolve, 800)); // a slow connection
    await route.continue();
  });
  await page.goto("/admin/audit");
  await expect(events(page)).toHaveCount(50);

  await page.getByRole("button", { name: "Show more" }).dblclick();

  // Every event once, however many there are: no repeats from the second click.
  await expect(events(page)).toHaveCount(total);
  expect(nextPageRequests).toBe(1);
});

test("a slow answer to an old filter does not replace the list for the new one", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Stale ${unique()}`);
  await inviteByApi(context, baseURL!, "Anita Rao");
  const page = await context.newPage();
  await page.route("**/api/v1/audit-events?*entity_type=membership*", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500)); // answers after the next filter
    await route.continue();
  });
  await page.goto("/admin/audit");
  const activated = events(page).filter({ hasText: "Account activated" });
  await expect(activated).toHaveCount(1);

  await page.getByLabel("Kind").selectOption("membership"); // slow
  await page.getByLabel("Kind").selectOption(""); // back to everything, fast
  await expect(activated).toHaveCount(1);
  await page.waitForTimeout(2500); // the slow answer has arrived by now

  // It was for filters no longer chosen, so it must not have replaced the list.
  await expect(activated).toHaveCount(1);
  await expect(page.getByLabel("Kind")).toHaveValue("");
});
