import { expect, test } from "@playwright/test";

import { invite, person, setPassword, signedInOwner, unique } from "./helpers";

// M2 (A-01, B-05, B-06, B-09, B-10): the Owner invites people, gives faculty their grants, and
// makes links, on the Users & grants screen.

test("the Owner invites faculty, who activate, then gives them grants and a reset link", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Users Classes ${unique()}`);
  const owner = await context.newPage();
  await owner.goto("/");
  await owner.getByRole("link", { name: "Users & grants" }).click();
  await expect(owner.getByRole("heading", { name: "Users & grants" })).toBeVisible();

  const email = `anita-${unique()}@example.com`;
  const link = await invite(owner, "Anita Rao", email);
  const anita = person(owner, email);
  await expect(anita).toContainText("Invited");
  await expect(anita).toContainText("No grants");

  // The faculty member opens the link in a browser of their own.
  const faculty = await (await browser.newContext()).newPage();
  await faculty.goto(link);
  await setPassword(faculty, "a faculty passphrase");
  await expect(faculty.getByRole("heading", { name: "Welcome, Anita Rao" })).toBeVisible();
  await expect(faculty.getByRole("link", { name: "Users & grants" })).toHaveCount(0);
  await faculty.goto("/admin/users");
  // `main`: Next.js keeps its own hidden alert region for page changes.
  await expect(faculty.locator("main").getByRole("alert")).toContainText("don't have access");

  // The Owner gives them grants; they apply to the open session at once.
  await owner.reload();
  await expect(anita).not.toContainText("Invited");
  await anita.getByRole("button", { name: "Edit grants" }).click();
  await anita.getByRole("checkbox", { name: /^Quality check/ }).check();
  await anita.getByRole("checkbox", { name: /^Approve/ }).check();
  await anita.getByRole("button", { name: "Save grants" }).click();
  await expect(anita).toContainText("Grants: Approve, Quality check");
  const me = await (await faculty.request.get("/api/v1/me")).json();
  expect(me.organization.grants).toEqual(["APPROVE", "QC"]);

  // A password-reset link for them, shown once.
  await anita.getByRole("button", { name: "Password-reset link" }).click();
  const notice = owner.getByRole("status", { name: "Password-reset link for Anita Rao" });
  await expect(notice.getByLabel("Link")).toHaveValue(/\/activate#/);
  await notice.getByRole("button", { name: "Done" }).click();
  await expect(notice).toHaveCount(0);
});

test("an out-of-date screen cannot overwrite a newer change to grants", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Stale Classes ${unique()}`);
  const first = await context.newPage();
  await first.goto("/admin/users");
  const email = `ravi-${unique()}@example.com`;
  await invite(first, "Ravi Iyer", email);

  // The same people, opened in a second tab, which changes the grants first.
  const second = await context.newPage();
  await second.goto("/admin/users");
  await person(second, email).getByRole("button", { name: "Edit grants" }).click();
  await person(second, email)
    .getByRole("checkbox", { name: /^Publish/ })
    .check();
  await person(second, email).getByRole("button", { name: "Save grants" }).click();
  await expect(person(second, email)).toContainText("Grants: Publish");

  // The first tab still shows the old state; its change is refused, and it reloads.
  const ravi = person(first, email);
  await ravi.getByRole("button", { name: "Edit grants" }).click();
  await ravi.getByRole("checkbox", { name: /^Quality check/ }).check();
  await ravi.getByRole("button", { name: "Save grants" }).click();
  await expect(ravi.getByRole("alert")).toContainText("Someone else changed this");
  await expect(ravi).toContainText("Grants: Publish");
});

test("an email that already has an account is refused with a clear message", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Email Classes ${unique()}`);
  const owner = await context.newPage();
  await owner.goto("/admin/users");
  const email = `dup-${unique()}@example.com`;
  await invite(owner, "First Person", email);

  await owner.fill('input[name="display_name"]', "Second Person");
  await owner.fill('input[name="email"]', email);
  await owner.getByRole("button", { name: "Invite and make link" }).click();

  await expect(
    owner.getByRole("form", { name: "Invite someone" }).getByRole("alert"),
  ).toContainText("already exists");
});
