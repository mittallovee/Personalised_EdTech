import { expect, test, type Page } from "@playwright/test";

import { activate, invite, signedInOwner, unique } from "./helpers";

// M3 (C-01, C-04): the Owner builds the syllabus on the Syllabus screen, one level at a time.

/** One item in the list of the level being shown, found by its name. */
function item(page: Page, name: string) {
  return page
    .getByRole("list", { name: "Syllabus items" })
    .getByRole("listitem")
    .filter({ hasText: name });
}

/** Fill in the "Add a …" form of the level being shown and send it. */
async function add(page: Page, kind: string, name: string, order = "1") {
  const form = page.getByRole("form", { name: `Add a ${kind}` });
  await form.getByLabel("Name (English)").fill(name);
  await form.getByLabel("Order (smaller comes first)").fill(order);
  await form.getByRole("button", { name: `Add ${kind}` }).click();
  await expect(item(page, name)).toBeVisible();
}

test("the Owner builds a syllabus level by level, renames, translates, retires and restores", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Syllabus Classes ${unique()}`);
  const page = await context.newPage();
  await page.goto("/");
  await page.getByRole("link", { name: "Syllabus" }).click();
  await expect(page.getByRole("heading", { name: "Syllabus", level: 1 })).toBeVisible();
  await expect(page.getByText("No classes yet.")).toBeVisible();

  // Classes, then the subjects inside one, then its chapters.
  await add(page, "class", "Class 11");
  await item(page, "Class 11").getByRole("button", { name: "Open" }).click();
  await expect(page.getByRole("heading", { name: "Class 11", level: 2 })).toBeVisible();
  await expect(page.getByText("No subjects yet.")).toBeVisible();
  await add(page, "subject", "Physics");
  await add(page, "subject", "Chemistry", "2");
  await item(page, "Physics").getByRole("button", { name: "Open" }).click();
  await add(page, "chapter", "Kinematics");

  // The same name twice under one parent is refused, with the API's reason.
  const form = page.getByRole("form", { name: "Add a chapter" });
  await form.getByLabel("Name (English)").fill("kinematics");
  await form.getByRole("button", { name: "Add chapter" }).click();
  await expect(form.getByRole("alert")).toContainText("already");

  // Rename a chapter and give it a Hindi name.
  const kinematics = item(page, "Kinematics");
  await kinematics.getByRole("button", { name: "Edit" }).click();
  const edit = kinematics.getByRole("form", { name: "Edit Kinematics" });
  await edit.getByLabel("Name (English)").fill("Kinematics in one dimension");
  await edit.getByLabel(/^Hindi/).fill("एक विमा में गतिकी");
  await edit.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("status")).toContainText("Kinematics in one dimension was saved.");
  const renamed = item(page, "Kinematics in one dimension");
  await expect(renamed).toContainText("Hindi: एक विमा में गतिकी");

  // Retire: asked first; a retired item stays, marked, and can be restored.
  await renamed.getByRole("button", { name: "Retire" }).click();
  await expect(renamed.getByRole("region", { name: /^Retire / })).toContainText(
    "nothing is deleted",
  );
  await renamed.getByRole("button", { name: "Retire", exact: true }).last().click();
  await expect(renamed).toContainText("Retired");
  await expect(renamed.getByRole("button", { name: "Edit" })).toHaveCount(0);
  await renamed.getByRole("button", { name: "Restore" }).click();
  await expect(renamed).not.toContainText("Retired");

  // The breadcrumb leads back up.
  const where = page.getByRole("navigation", { name: "Where you are" });
  await where.getByRole("button", { name: "Class 11" }).click();
  await expect(item(page, "Physics")).toBeVisible();
  await expect(item(page, "Chemistry")).toBeVisible();
  await where.getByRole("button", { name: "All classes" }).click();
  await expect(item(page, "Class 11")).toBeVisible();
});

test("an out-of-date screen cannot overwrite a newer change to a syllabus item", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Stale Syllabus ${unique()}`);
  const first = await context.newPage();
  await first.goto("/admin/syllabus");
  await add(first, "class", "Class 12");

  // The same list in a second tab, which renames the class first.
  const second = await context.newPage();
  await second.goto("/admin/syllabus");
  await item(second, "Class 12").getByRole("button", { name: "Edit" }).click();
  const secondEdit = item(second, "Class 12").getByRole("form", { name: "Edit Class 12" });
  await secondEdit.getByLabel("Name (English)").fill("Class XII");
  await secondEdit.getByRole("button", { name: "Save" }).click();
  await expect(item(second, "Class XII")).toBeVisible();

  // The first tab still shows the old name; its change is refused and the list reloads.
  await item(first, "Class 12").getByRole("button", { name: "Edit" }).click();
  const firstEdit = item(first, "Class 12").getByRole("form", { name: "Edit Class 12" });
  await firstEdit.getByLabel("Name (English)").fill("Class 12 (old)");
  await firstEdit.getByRole("button", { name: "Save" }).click();
  await expect(first.locator("main").getByRole("alert")).toContainText("Someone else changed this");
  await expect(item(first, "Class XII")).toBeVisible();
});

test("faculty can read the syllabus but have no controls to change it", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Faculty Syllabus ${unique()}`);
  const owner = await context.newPage();
  await owner.goto("/admin/syllabus");
  await add(owner, "class", "Class 11");

  await owner.goto("/admin/users");
  const link = await invite(owner, "Anita Rao", `anita-${unique()}@example.com`);
  const faculty = await activate(browser, link, "Anita Rao");
  await faculty.getByRole("link", { name: "Syllabus" }).click();
  await expect(item(faculty, "Class 11")).toBeVisible();
  await expect(faculty.getByRole("button", { name: "Open" })).toBeVisible();
  await expect(faculty.getByRole("button", { name: "Edit" })).toHaveCount(0);
  await expect(faculty.getByRole("button", { name: "Retire" })).toHaveCount(0);
  await expect(faculty.getByRole("form", { name: "Add a class" })).toHaveCount(0);
});
