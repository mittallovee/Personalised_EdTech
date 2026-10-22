import { expect, test } from "@playwright/test";

import {
  activate,
  actingPlatformAdmin,
  csrfOf,
  invite,
  person,
  signedInOwner,
  unique,
} from "./helpers";

// M2 (B-08, B-09, B-10, T14, T15, T17): change roles, remove people and hand over the coaching on
// the Users & grants screen. The buttons come from the API's `actions`; every change asks first.

test("the Owner makes faculty an admin, back to faculty, then removes them", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Roles Classes ${unique()}`);
  const owner = await context.newPage();
  await owner.goto("/admin/users");
  const email = `anita-${unique()}@example.com`;
  const link = await invite(owner, "Anita Rao", email);
  const faculty = await activate(browser, link, "Anita Rao");
  await owner.reload();
  const anita = person(owner, email);
  const role = async () =>
    (await (await faculty.request.get("/api/v1/me")).json()).organization.role;

  // Promote: asked first, then the open session of the other person sees it at once.
  await anita.getByRole("button", { name: "Make admin" }).click();
  const promote = anita.getByRole("region", { name: "Make Anita Rao an admin?" });
  await expect(promote).toContainText("grants are cleared");
  await promote.getByRole("button", { name: "Make admin" }).click();
  await expect(owner.getByRole("status")).toHaveText("Anita Rao is now an admin.");
  await expect(anita).toContainText("Holds every grant");
  expect(await role()).toBe("ADMIN");

  // Demote.
  await anita.getByRole("button", { name: "Make faculty" }).click();
  await anita
    .getByRole("region", { name: "Make Anita Rao faculty?" })
    .getByRole("button", { name: "Make faculty" })
    .click();
  await expect(owner.getByRole("status")).toHaveText("Anita Rao is now faculty.");
  await expect(anita).toContainText("No grants");
  expect(await role()).toBe("FACULTY");

  // Remove: gone from the list, and their open session stops working.
  await anita.getByRole("button", { name: "Remove" }).click();
  const confirm = anita.getByRole("region", { name: "Remove Anita Rao?" });
  await expect(confirm).toContainText("Their access ends at once");
  await confirm.getByRole("button", { name: "Remove" }).click();
  await expect(owner.getByRole("status")).toHaveText(
    "Anita Rao was removed. Their access has ended.",
  );
  await expect(person(owner, email)).toHaveCount(0);
  expect((await faculty.request.get("/api/v1/me")).status()).toBe(401);
  await faculty.reload();
  await expect(faculty).toHaveURL(/\/login$/);
});

test("cancelling a question changes nothing", async ({ browser, baseURL }) => {
  const { context } = await signedInOwner(browser, baseURL!, `Cancel Classes ${unique()}`);
  const owner = await context.newPage();
  await owner.goto("/admin/users");
  const email = `kiran-${unique()}@example.com`;
  await invite(owner, "Kiran Das", email);
  const kiran = person(owner, email);

  await kiran.getByRole("button", { name: "Remove" }).click();
  await expect(kiran.getByRole("region", { name: "Remove Kiran Das?" })).toBeVisible();
  await kiran.getByRole("button", { name: "Cancel" }).click();

  await expect(kiran.getByRole("region")).toHaveCount(0);
  await owner.reload();
  await expect(person(owner, email)).toHaveCount(1);
});

test("an out-of-date screen cannot remove someone who was promoted meanwhile", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Stale Roles ${unique()}`);
  const first = await context.newPage();
  await first.goto("/admin/users");
  const email = `ravi-${unique()}@example.com`;
  await invite(first, "Ravi Iyer", email);

  // A second tab promotes him while the first tab still shows faculty.
  const second = await context.newPage();
  await second.goto("/admin/users");
  await person(second, email).getByRole("button", { name: "Make admin" }).click();
  await person(second, email)
    .getByRole("region", { name: "Make Ravi Iyer an admin?" })
    .getByRole("button", { name: "Make admin" })
    .click();
  await expect(second.getByRole("status")).toHaveText("Ravi Iyer is now an admin.");

  const ravi = person(first, email);
  await ravi.getByRole("button", { name: "Remove" }).click();
  await ravi
    .getByRole("region", { name: "Remove Ravi Iyer?" })
    .getByRole("button", { name: "Remove" })
    .click();

  await expect(ravi.getByRole("alert")).toContainText("Someone else changed this");
  await expect(ravi.getByRole("region")).toHaveCount(0); // the question is closed
  await expect(ravi).toContainText("Holds every grant"); // and the list shows the truth: an admin
});

test("the Owner hands the coaching to an admin and becomes an admin", async ({
  browser,
  baseURL,
}) => {
  const { context, ownerName } = await signedInOwner(
    browser,
    baseURL!,
    `Transfer Classes ${unique()}`,
  );
  const owner = await context.newPage();
  await owner.goto("/admin/users");
  const email = `meera-${unique()}@example.com`;
  const link = await invite(owner, "Meera Nair", email, "ADMIN");
  const admin = await activate(browser, link, "Meera Nair");
  await owner.reload();
  const priya = person(owner, ownerName);
  await expect(priya.getByRole("button")).toHaveCount(0); // the Owner has no buttons of their own

  await person(owner, email).getByRole("button", { name: "Make owner" }).click();
  const confirm = person(owner, email).getByRole("region", {
    name: "Hand the coaching to Meera Nair?",
  });
  await expect(confirm).toContainText("you become an admin");
  await confirm.getByRole("button", { name: "Make owner" }).click();

  await expect(owner.getByRole("status")).toHaveText(
    "Meera Nair is now the Owner. You are an admin.",
  );
  await expect(person(owner, email)).toContainText("Owner");
  await expect(priya).toContainText("Admin");
  const mine = await (await owner.request.get("/api/v1/me")).json();
  expect(mine.organization.role).toBe("ADMIN");
  // The new Owner can now act on the former one.
  await admin.goto("/admin/users");
  await expect(person(admin, ownerName).getByRole("button", { name: "Make owner" })).toBeVisible();
  await expect(person(admin, ownerName).getByRole("button", { name: "Remove" })).toBeVisible();
});

test("a platform admin acting in the coaching is told who really steps down", async ({
  browser,
  baseURL,
}) => {
  const { context, ownerName } = await signedInOwner(
    browser,
    baseURL!,
    `Acting Classes ${unique()}`,
  );
  const owner = await context.newPage();
  await owner.goto("/admin/users");
  const email = `meera-${unique()}@example.com`;
  await activate(browser, await invite(owner, "Meera Nair", email, "ADMIN"), "Meera Nair");
  const organizationId = (await (await context.request.get("/api/v1/me")).json()).organization.id;
  const staff = await (await actingPlatformAdmin(browser, baseURL!, organizationId)).newPage();
  await staff.goto("/admin/users");

  await person(staff, email).getByRole("button", { name: "Make owner" }).click();
  const confirm = person(staff, email).getByRole("region", {
    name: "Hand the coaching to Meera Nair?",
  });
  await expect(confirm).toContainText(`${ownerName} becomes an admin`);
  await expect(confirm).not.toContainText("you become");
  await confirm.getByRole("button", { name: "Make owner" }).click();

  await expect(staff.getByRole("status")).toHaveText(
    `Meera Nair is now the Owner. ${ownerName} is now an admin.`,
  );
});

test("a refusal about someone who is no longer listed is still explained", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Gone Classes ${unique()}`);
  const first = await context.newPage();
  await first.goto("/admin/users");
  const email = `kiran-${unique()}@example.com`;
  await invite(first, "Kiran Das", email);

  // Another tab removes him; this tab still shows him and asks to remove him too.
  const second = await context.newPage();
  await second.goto("/admin/users");
  await person(second, email).getByRole("button", { name: "Remove" }).click();
  await person(second, email)
    .getByRole("region", { name: "Remove Kiran Das?" })
    .getByRole("button", { name: "Remove" })
    .click();
  await expect(person(second, email)).toHaveCount(0);

  await person(first, email).getByRole("button", { name: "Remove" }).click();
  await person(first, email)
    .getByRole("region", { name: "Remove Kiran Das?" })
    .getByRole("button", { name: "Remove" })
    .click();

  await expect(person(first, email)).toHaveCount(0); // the list shows the truth: he is gone
  await expect(first.locator("main").getByRole("alert")).toContainText("Kiran Das");
  await expect(first.locator("main").getByRole("alert")).toContainText("Someone else changed this");
});

test("after Show more, a refusal keeps the people already loaded", async ({ browser, baseURL }) => {
  test.setTimeout(90_000);
  const { context } = await signedInOwner(browser, baseURL!, `Long Classes ${unique()}`);
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  const firstEmail = `first-${unique()}@example.com`;
  for (let n = 0; n < 52; n++) {
    const email = n === 0 ? firstEmail : `person${n}-${unique()}@example.com`;
    const response = await context.request.post("/api/v1/members/invitations", {
      headers,
      data: { email, display_name: `Person ${n}`, role: "FACULTY" },
    });
    expect(response.status()).toBe(201);
  }
  const page = await context.newPage();
  await page.goto("/admin/users");
  const members = page.getByRole("list", { name: "Members" }).getByRole("listitem");
  await expect(members).toHaveCount(50); // the first page
  await page.getByRole("button", { name: "Show more" }).click();
  await expect(members).toHaveCount(53); // 52 invited and the Owner
  const oldest = person(page, firstEmail); // invited first, so on the second page

  // Meanwhile someone else makes her an admin, so this screen is out of date.
  const found = await context.request.get(`/api/v1/members?limit=100`);
  const target = (await found.json()).data.find((m: { email: string }) => m.email === firstEmail);
  const promoted = await context.request.post(
    `/api/v1/members/${target.membership_id}/change-role`,
    {
      headers: { ...headers, "If-Match": `"rev-${target.revision}"` },
      data: { expected_role: "FACULTY", new_role: "ADMIN" },
    },
  );
  expect(promoted.status()).toBe(200);

  await oldest.getByRole("button", { name: "Remove" }).click();
  await oldest
    .getByRole("region", { name: "Remove Person 0?" })
    .getByRole("button", { name: "Remove" })
    .click();

  await expect(oldest.getByRole("alert")).toContainText("Someone else changed this");
  await expect(members).toHaveCount(53); // nobody dropped off the list
  await expect(oldest).toContainText("Holds every grant"); // and she shows as the admin she is now
});

test("pressing Show more twice on a slow connection loads the next page once", async ({
  browser,
  baseURL,
}) => {
  test.setTimeout(90_000);
  const { context } = await signedInOwner(browser, baseURL!, `Double Classes ${unique()}`);
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  for (let n = 0; n < 52; n++) {
    const response = await context.request.post("/api/v1/members/invitations", {
      headers,
      data: {
        email: `p${n}-${unique()}@example.com`,
        display_name: `Person ${n}`,
        role: "FACULTY",
      },
    });
    expect(response.status()).toBe(201);
  }
  const page = await context.newPage();
  let nextPageRequests = 0;
  await page.route("**/api/v1/members?*cursor=*", async (route) => {
    nextPageRequests += 1;
    await new Promise((resolve) => setTimeout(resolve, 800)); // a slow connection
    await route.continue();
  });
  await page.goto("/admin/users");
  const members = page.getByRole("list", { name: "Members" }).getByRole("listitem");
  await expect(members).toHaveCount(50);

  await page.getByRole("button", { name: "Show more" }).dblclick();

  await expect(members).toHaveCount(53); // 52 invited and the Owner, each once
  expect(nextPageRequests).toBe(1);
});
