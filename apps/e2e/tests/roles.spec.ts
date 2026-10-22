import { expect, test } from "@playwright/test";

import { activate, invite, person, signedInOwner, unique } from "./helpers";

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
