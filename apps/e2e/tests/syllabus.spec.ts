import { expect, test, type Page } from "@playwright/test";

import {
  activate,
  actingPlatformAdmin,
  csrfOf,
  invite,
  platformAdminContext,
  signedInOwner,
  unique,
} from "./helpers";

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
  // At the top there is nowhere higher to go: "All classes" is a label, not a button.
  const where = page.getByRole("navigation", { name: "Where you are" });
  await expect(where.getByRole("button")).toHaveCount(0);

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

test("a new item shows where its order puts it", async ({ browser, baseURL }) => {
  const { context } = await signedInOwner(browser, baseURL!, `Order Syllabus ${unique()}`);
  const page = await context.newPage();
  await page.goto("/admin/syllabus");
  await add(page, "class", "Class 11", "5");
  await add(page, "class", "Class 10", "1");
  await add(page, "class", "Class 12", "9");
  await expect(
    page
      .getByRole("list", { name: "Syllabus items" })
      .getByRole("listitem")
      .getByText(/^Class 1/),
  ).toHaveText(["Class 10", "Class 11", "Class 12"]);
});

test("pressing Show more twice on a long list loads the next page once", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Long Syllabus ${unique()}`);
  const csrf = await csrfOf(context);
  for (let n = 1; n <= 102; n++) {
    const created = await context.request.post("/api/v1/taxonomy/nodes", {
      headers: { Origin: baseURL!, "X-CSRF-Token": csrf },
      data: { kind: "CLASS", name: `Class ${String(n).padStart(3, "0")}`, sort_order: n },
    });
    expect(created.status()).toBe(201);
  }
  const page = await context.newPage();
  // Slow the second page down, so both presses happen before it arrives.
  await page.route("**/api/v1/taxonomy/nodes?*cursor=*", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 800));
    await route.continue();
  });
  await page.goto("/admin/syllabus");
  const items = page.getByRole("list", { name: "Syllabus items" }).getByRole("listitem");
  await expect(items).toHaveCount(100);
  const more = page.getByRole("button", { name: "Show more" });
  await more.click();
  await more.click({ noWaitAfter: true, timeout: 2000 }).catch(() => undefined);
  await expect(items).toHaveCount(102);
  await expect(page.getByRole("button", { name: "Show more" })).toHaveCount(0);
});

test("the Syllabus link is for people in a coaching, not a platform admin outside one", async ({
  browser,
  baseURL,
}) => {
  const { context: ownerContext } = await signedInOwner(
    browser,
    baseURL!,
    `Link Syllabus ${unique()}`,
  );
  const me = await (await ownerContext.request.get("/api/v1/me")).json();

  const platform = await (await platformAdminContext(browser, baseURL!)).newPage();
  await platform.goto("/");
  await expect(platform.getByRole("heading", { name: /Welcome/ })).toBeVisible();
  await expect(platform.getByRole("link", { name: "Syllabus" })).toHaveCount(0);

  const acting = await (await actingPlatformAdmin(browser, baseURL!, me.organization.id)).newPage();
  await acting.goto("/");
  await expect(acting.getByRole("link", { name: "Syllabus" })).toBeVisible();
});

test("changing an item's order moves it to where the order puts it", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Reorder Syllabus ${unique()}`);
  const page = await context.newPage();
  await page.goto("/admin/syllabus");
  await add(page, "class", "Class 9", "1");
  await add(page, "class", "Class 10", "2");
  const names = page.getByRole("list", { name: "Syllabus items" }).getByRole("listitem");
  await expect(names.getByText(/^Class \d+$/)).toHaveText(["Class 9", "Class 10"]);

  await item(page, "Class 9").getByRole("button", { name: "Edit" }).click();
  await item(page, "Class 9").getByLabel("Order (smaller comes first)").fill("5");
  await item(page, "Class 9").getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("status")).toContainText("Class 9 was saved.");
  await expect(names.getByText(/^Class \d+$/)).toHaveText(["Class 10", "Class 9"]);
});

test("after a refused change the editor starts again from the newer data", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Draft Syllabus ${unique()}`);
  const first = await context.newPage();
  await first.goto("/admin/syllabus");
  await add(first, "class", "Class 7");

  const second = await context.newPage();
  await second.goto("/admin/syllabus");
  await item(second, "Class 7").getByRole("button", { name: "Edit" }).click();
  await item(second, "Class 7").getByLabel("Name (English)").fill("Class VII");
  await item(second, "Class 7").getByRole("button", { name: "Save" }).click();
  await expect(item(second, "Class VII")).toBeVisible();

  // The first tab's change is refused; opening Edit again shows the newer name, not the old draft.
  await item(first, "Class 7").getByRole("button", { name: "Edit" }).click();
  await item(first, "Class 7").getByLabel("Name (English)").fill("Class 7 (my draft)");
  await item(first, "Class 7").getByRole("button", { name: "Save" }).click();
  await expect(first.locator("main").getByRole("alert")).toContainText("Someone else changed this");
  await item(first, "Class VII").getByRole("button", { name: "Edit" }).click();
  await expect(item(first, "Class VII").getByLabel("Name (English)")).toHaveValue("Class VII");
});

test("an addition answered after you moved on does not replace the level you moved to", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Moved Syllabus ${unique()}`);
  const csrf = await csrfOf(context);
  const make = async (data: object) => {
    const response = await context.request.post("/api/v1/taxonomy/nodes", {
      headers: { Origin: baseURL!, "X-CSRF-Token": csrf },
      data,
    });
    expect(response.status()).toBe(201);
    return (await response.json()) as { id: string };
  };
  const c11 = await make({ kind: "CLASS", name: "Class 11", sort_order: 1 });
  const c12 = await make({ kind: "CLASS", name: "Class 12", sort_order: 2 });
  await make({ kind: "SUBJECT", parent_id: c11.id, name: "Physics" });
  await make({ kind: "SUBJECT", parent_id: c12.id, name: "Biology" });

  const page = await context.newPage();
  await page.route("**/api/v1/taxonomy/nodes", async (route) => {
    if (route.request().method() === "POST") {
      await new Promise((resolve) => setTimeout(resolve, 1500)); // a slow answer
    }
    await route.continue();
  });
  await page.goto("/admin/syllabus");
  await item(page, "Class 11").getByRole("button", { name: "Open" }).click();
  await expect(item(page, "Physics")).toBeVisible();

  // Send an addition, and move to the other class before the answer comes.
  const form = page.getByRole("form", { name: "Add a subject" });
  await form.getByLabel("Name (English)").fill("Chemistry");
  await form.getByRole("button", { name: "Add subject" }).click();
  const where = page.getByRole("navigation", { name: "Where you are" });
  await where.getByRole("button", { name: "All classes" }).click();
  await item(page, "Class 12").getByRole("button", { name: "Open" }).click();
  await expect(item(page, "Biology")).toBeVisible();

  await page.waitForTimeout(2500); // the slow answer has come by now
  const subjects = page.getByRole("list", { name: "Syllabus items" }).getByRole("listitem");
  await expect(subjects).toHaveCount(1);
  await expect(item(page, "Biology")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Class 12", level: 2 })).toBeVisible();
  // The new subject was added to Class 11 all the same.
  await where.getByRole("button", { name: "All classes" }).click();
  await item(page, "Class 11").getByRole("button", { name: "Open" }).click();
  await expect(item(page, "Chemistry")).toBeVisible();
});

test("an edit answered after you moved on does not replace the level you moved to", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Slow Edit Syllabus ${unique()}`);
  const csrf = await csrfOf(context);
  const make = async (data: object) => {
    const response = await context.request.post("/api/v1/taxonomy/nodes", {
      headers: { Origin: baseURL!, "X-CSRF-Token": csrf },
      data,
    });
    expect(response.status()).toBe(201);
    return (await response.json()) as { id: string };
  };
  const c11 = await make({ kind: "CLASS", name: "Class 11", sort_order: 1 });
  const c12 = await make({ kind: "CLASS", name: "Class 12", sort_order: 2 });
  await make({ kind: "SUBJECT", parent_id: c11.id, name: "Physics" });
  await make({ kind: "SUBJECT", parent_id: c12.id, name: "Biology" });

  const page = await context.newPage();
  await page.route("**/api/v1/taxonomy/nodes/*", async (route) => {
    if (route.request().method() === "PATCH") {
      await new Promise((resolve) => setTimeout(resolve, 1500)); // a slow answer
    }
    await route.continue();
  });
  await page.goto("/admin/syllabus");
  await item(page, "Class 11").getByRole("button", { name: "Open" }).click();
  await item(page, "Physics").getByRole("button", { name: "Edit" }).click();
  await item(page, "Physics").getByLabel("Order (smaller comes first)").fill("3");
  await item(page, "Physics").getByRole("button", { name: "Save" }).click();

  // Move to the other class before the answer comes.
  const where = page.getByRole("navigation", { name: "Where you are" });
  await where.getByRole("button", { name: "All classes" }).click();
  await item(page, "Class 12").getByRole("button", { name: "Open" }).click();
  await expect(item(page, "Biology")).toBeVisible();

  await page.waitForTimeout(2500); // the slow answer has come by now
  await expect(
    page.getByRole("list", { name: "Syllabus items" }).getByRole("listitem"),
  ).toHaveCount(1);
  await expect(item(page, "Biology")).toBeVisible();
});

test("Show more of the level you left is not offered while the next level loads", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Cursor Syllabus ${unique()}`);
  const csrf = await csrfOf(context);
  for (let n = 1; n <= 101; n++) {
    const created = await context.request.post("/api/v1/taxonomy/nodes", {
      headers: { Origin: baseURL!, "X-CSRF-Token": csrf },
      data: { kind: "CLASS", name: `Class ${String(n).padStart(3, "0")}`, sort_order: n },
    });
    expect(created.status()).toBe(201);
    if (n === 1) {
      const { id } = (await created.json()) as { id: string };
      await context.request.post("/api/v1/taxonomy/nodes", {
        headers: { Origin: baseURL!, "X-CSRF-Token": csrf },
        data: { kind: "SUBJECT", parent_id: id, name: "Physics" },
      });
    }
  }
  const page = await context.newPage();
  await page.route("**/api/v1/taxonomy/nodes?*parent_id=*", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500)); // the next level is slow
    await route.continue();
  });
  await page.goto("/admin/syllabus");
  await expect(page.getByRole("button", { name: "Show more" })).toBeVisible();
  await item(page, "Class 001").getByRole("button", { name: "Open" }).click();
  await expect(page.getByText("Loading…")).toBeVisible();
  // Checked once, right now (not retried until the slow level has arrived).
  expect(await page.getByRole("button", { name: "Show more" }).count()).toBe(0);
  await expect(item(page, "Physics")).toBeVisible();
});

test("a failed load can be tried again without refreshing the page", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Retry Syllabus ${unique()}`);
  const setup = await context.newPage();
  await setup.goto("/admin/syllabus");
  await add(setup, "class", "Class 11");

  const page = await context.newPage();
  let failures = 1;
  await page.route("**/api/v1/taxonomy/nodes?*", async (route) => {
    if (failures-- > 0)
      await route.abort("connectionrefused"); // the first load fails
    else await route.continue();
  });
  await page.goto("/admin/syllabus");
  await expect(page.locator("main").getByRole("alert")).toContainText("Cannot reach the server");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(item(page, "Class 11")).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toHaveCount(0);
});

test("a late failure to add belongs to the level it was sent from", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Late Error Syllabus ${unique()}`);
  const csrf = await csrfOf(context);
  const make = async (data: object) => {
    const response = await context.request.post("/api/v1/taxonomy/nodes", {
      headers: { Origin: baseURL!, "X-CSRF-Token": csrf },
      data,
    });
    expect(response.status()).toBe(201);
    return (await response.json()) as { id: string };
  };
  const c11 = await make({ kind: "CLASS", name: "Class 11", sort_order: 1 });
  await make({ kind: "CLASS", name: "Class 12", sort_order: 2 });
  await make({ kind: "SUBJECT", parent_id: c11.id, name: "Physics" });

  const page = await context.newPage();
  await page.route("**/api/v1/taxonomy/nodes", async (route) => {
    if (route.request().method() === "POST") {
      await new Promise((resolve) => setTimeout(resolve, 1500)); // a slow answer
    }
    await route.continue();
  });
  await page.goto("/admin/syllabus");
  await item(page, "Class 11").getByRole("button", { name: "Open" }).click();
  await expect(item(page, "Physics")).toBeVisible();
  // The same name again: refused, but only after the person has moved on.
  const form = page.getByRole("form", { name: "Add a subject" });
  await form.getByLabel("Name (English)").fill("physics");
  await form.getByRole("button", { name: "Add subject" }).click();
  const where = page.getByRole("navigation", { name: "Where you are" });
  await where.getByRole("button", { name: "All classes" }).click();
  await item(page, "Class 12").getByRole("button", { name: "Open" }).click();
  await expect(page.getByText("No subjects yet.")).toBeVisible();

  await page.waitForTimeout(2500); // the slow refusal has come by now
  await expect(page.getByRole("form", { name: "Add a subject" }).getByRole("alert")).toHaveCount(0);
});

test("a save answered after you moved on leaves the edit you started on the new level alone", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Late Save Syllabus ${unique()}`);
  const csrf = await csrfOf(context);
  const make = async (data: object) => {
    const response = await context.request.post("/api/v1/taxonomy/nodes", {
      headers: { Origin: baseURL!, "X-CSRF-Token": csrf },
      data,
    });
    expect(response.status()).toBe(201);
    return (await response.json()) as { id: string };
  };
  const c11 = await make({ kind: "CLASS", name: "Class 11", sort_order: 1 });
  const c12 = await make({ kind: "CLASS", name: "Class 12", sort_order: 2 });
  await make({ kind: "SUBJECT", parent_id: c11.id, name: "Physics" });
  await make({ kind: "SUBJECT", parent_id: c12.id, name: "Biology" });

  const page = await context.newPage();
  await page.route("**/api/v1/taxonomy/nodes/*", async (route) => {
    if (route.request().method() === "PATCH") {
      await new Promise((resolve) => setTimeout(resolve, 1500)); // a slow answer
    }
    await route.continue();
  });
  await page.goto("/admin/syllabus");
  await item(page, "Class 11").getByRole("button", { name: "Open" }).click();
  await item(page, "Physics").getByRole("button", { name: "Edit" }).click();
  await item(page, "Physics").getByLabel("Order (smaller comes first)").fill("3");
  await item(page, "Physics").getByRole("button", { name: "Save" }).click();

  // Move on, and start an edit on the other class's subject before the answer comes.
  const where = page.getByRole("navigation", { name: "Where you are" });
  await where.getByRole("button", { name: "All classes" }).click();
  await item(page, "Class 12").getByRole("button", { name: "Open" }).click();
  await item(page, "Biology").getByRole("button", { name: "Edit" }).click();
  await item(page, "Biology").getByLabel("Name (English)").fill("Biology (draft)");

  await page.waitForTimeout(2500); // the slow answer has come by now
  await expect(item(page, "Biology").getByLabel("Name (English)")).toHaveValue("Biology (draft)");
  await expect(page.getByText("Physics was saved.")).toHaveCount(0);
});

test("a retired item offers no way to add under it", async ({ browser, baseURL }) => {
  const { context } = await signedInOwner(browser, baseURL!, `Retired Parent ${unique()}`);
  const csrf = await csrfOf(context);
  const headers = { Origin: baseURL!, "X-CSRF-Token": csrf };
  const created = await context.request.post("/api/v1/taxonomy/nodes", {
    headers,
    data: { kind: "CLASS", name: "Class 11", sort_order: 1 },
  });
  const cls = (await created.json()) as { id: string; revision: number };
  const retired = await context.request.post(`/api/v1/taxonomy/nodes/${cls.id}/deprecate`, {
    headers: { ...headers, "If-Match": `"rev-${cls.revision}"` },
  });
  expect(retired.status()).toBe(200);

  const page = await context.newPage();
  await page.goto("/admin/syllabus");
  await item(page, "Class 11").getByRole("button", { name: "Open" }).click();
  await expect(
    page.getByText("Class 11 is retired. Restore it to add subjects under it."),
  ).toBeVisible();
  await expect(page.getByRole("form", { name: "Add a subject" })).toHaveCount(0);
});

test("Show more of a level you left does not block Show more on the level you moved to", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Lock Syllabus ${unique()}`);
  const csrf = await csrfOf(context);
  const headers = { Origin: baseURL!, "X-CSRF-Token": csrf };
  let first = "";
  for (let n = 1; n <= 101; n++) {
    const created = await context.request.post("/api/v1/taxonomy/nodes", {
      headers,
      data: { kind: "CLASS", name: `Class ${String(n).padStart(3, "0")}`, sort_order: n },
    });
    expect(created.status()).toBe(201);
    if (n === 1) first = ((await created.json()) as { id: string }).id;
  }
  for (let n = 1; n <= 101; n++) {
    const created = await context.request.post("/api/v1/taxonomy/nodes", {
      headers,
      data: {
        kind: "SUBJECT",
        parent_id: first,
        name: `Subject ${String(n).padStart(3, "0")}`,
        sort_order: n,
      },
    });
    expect(created.status()).toBe(201);
  }
  const page = await context.newPage();
  // The classes' second page hangs for a long time; the subjects' second page is quick.
  await page.route(
    (url) => url.pathname === "/api/v1/taxonomy/nodes" && url.searchParams.has("cursor"),
    async (route) => {
      if (!route.request().url().includes("parent_id")) {
        await new Promise((resolve) => setTimeout(resolve, 6000));
      }
      await route.continue();
    },
  );
  await page.goto("/admin/syllabus");
  await page.getByRole("button", { name: "Show more" }).click(); // slow, left hanging
  await item(page, "Class 001").getByRole("button", { name: "Open" }).click();
  await expect(item(page, "Subject 001")).toBeVisible();
  await page.getByRole("button", { name: "Show more" }).click();
  await expect(item(page, "Subject 101")).toBeVisible({ timeout: 3000 });
});

test("a slow retire does not close the edit you started on another row", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Two Rows ${unique()}`);
  const csrf = await csrfOf(context);
  const make = async (data: object) => {
    const response = await context.request.post("/api/v1/taxonomy/nodes", {
      headers: { Origin: baseURL!, "X-CSRF-Token": csrf },
      data,
    });
    expect(response.status()).toBe(201);
    return (await response.json()) as { id: string };
  };
  await make({ kind: "CLASS", name: "Class 11", sort_order: 1 });
  await make({ kind: "CLASS", name: "Class 12", sort_order: 2 });

  const page = await context.newPage();
  await page.route("**/api/v1/taxonomy/nodes/*/deprecate", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500)); // a slow answer
    await route.continue();
  });
  await page.goto("/admin/syllabus");
  await item(page, "Class 11").getByRole("button", { name: "Retire" }).click();
  await item(page, "Class 11").getByRole("button", { name: "Retire", exact: true }).last().click();

  // While it is slow, start editing the other row.
  await item(page, "Class 12").getByRole("button", { name: "Edit" }).click();
  await item(page, "Class 12").getByLabel("Name (English)").fill("Class 12 (draft)");

  await expect(item(page, "Class 11")).toContainText("Retired");
  await expect(item(page, "Class 12").getByLabel("Name (English)")).toHaveValue("Class 12 (draft)");
});

test("under a retired parent, a retired child cannot be restored first", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Restore Order ${unique()}`);
  const csrf = await csrfOf(context);
  const headers = { Origin: baseURL!, "X-CSRF-Token": csrf };
  const post = async (path: string, data?: object, revision?: number) => {
    const response = await context.request.post(path, {
      headers: revision ? { ...headers, "If-Match": `"rev-${revision}"` } : headers,
      data,
    });
    expect(response.status()).toBeLessThan(300);
    return (await response.json()) as { id: string; revision: number };
  };
  const cls = await post("/api/v1/taxonomy/nodes", {
    kind: "CLASS",
    name: "Class 11",
    sort_order: 1,
  });
  const subject = await post("/api/v1/taxonomy/nodes", {
    kind: "SUBJECT",
    parent_id: cls.id,
    name: "Physics",
  });
  const retiredSubject = await post(
    `/api/v1/taxonomy/nodes/${subject.id}/deprecate`,
    undefined,
    subject.revision,
  );
  expect(retiredSubject.id).toBe(subject.id);
  await post(`/api/v1/taxonomy/nodes/${cls.id}/deprecate`, undefined, cls.revision);

  const page = await context.newPage();
  await page.goto("/admin/syllabus");
  await item(page, "Class 11").getByRole("button", { name: "Open" }).click();
  await expect(item(page, "Physics")).toContainText("Retired");
  await expect(item(page, "Physics").getByRole("button", { name: "Restore" })).toHaveCount(0);
  await expect(item(page, "Physics")).toContainText("Restore its parent first.");
  // The parent itself can be restored from the level above.
  await page
    .getByRole("navigation", { name: "Where you are" })
    .getByRole("button", { name: "All classes" })
    .click();
  await item(page, "Class 11").getByRole("button", { name: "Restore" }).click();
  await expect(item(page, "Class 11")).not.toContainText("Retired");
});

test("while one change is on its way, no second change can be sent from another row", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `One At A Time ${unique()}`);
  const csrf = await csrfOf(context);
  const headers = { Origin: baseURL!, "X-CSRF-Token": csrf };
  const post = async (path: string, data?: object, revision?: number) => {
    const response = await context.request.post(path, {
      headers: revision ? { ...headers, "If-Match": `"rev-${revision}"` } : headers,
      data,
    });
    expect(response.status()).toBeLessThan(300);
    return (await response.json()) as { id: string; revision: number };
  };
  await post("/api/v1/taxonomy/nodes", { kind: "CLASS", name: "Class 11", sort_order: 1 });
  const other = await post("/api/v1/taxonomy/nodes", {
    kind: "CLASS",
    name: "Class 12",
    sort_order: 2,
  });
  await post(`/api/v1/taxonomy/nodes/${other.id}/deprecate`, undefined, other.revision);

  const page = await context.newPage();
  await page.route("**/api/v1/taxonomy/nodes/*", async (route) => {
    if (route.request().method() === "PATCH") {
      await new Promise((resolve) => setTimeout(resolve, 1500)); // a slow answer
    }
    await route.continue();
  });
  await page.goto("/admin/syllabus");
  await item(page, "Class 11").getByRole("button", { name: "Edit" }).click();
  await item(page, "Class 11").getByLabel("Order (smaller comes first)").fill("3");
  await item(page, "Class 11").getByRole("button", { name: "Save" }).click();

  // Checked once, right now, while the save is on its way.
  expect(await item(page, "Class 12").getByRole("button", { name: "Restore" }).isDisabled()).toBe(
    true,
  );
  expect(await item(page, "Class 11").getByRole("button", { name: "Open" }).isDisabled()).toBe(
    true,
  );
  await expect(item(page, "Class 11").getByRole("button", { name: "Open" })).toBeEnabled();
  await expect(item(page, "Class 12").getByRole("button", { name: "Restore" })).toBeEnabled();
});

test("a change still on its way does not lock the level you moved to", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Unlock ${unique()}`);
  const csrf = await csrfOf(context);
  const make = async (data: object) => {
    const response = await context.request.post("/api/v1/taxonomy/nodes", {
      headers: { Origin: baseURL!, "X-CSRF-Token": csrf },
      data,
    });
    expect(response.status()).toBe(201);
    return (await response.json()) as { id: string };
  };
  const c11 = await make({ kind: "CLASS", name: "Class 11", sort_order: 1 });
  await make({ kind: "CLASS", name: "Class 12", sort_order: 2 });
  await make({ kind: "SUBJECT", parent_id: c11.id, name: "Physics" });

  const page = await context.newPage();
  await page.route("**/api/v1/taxonomy/nodes/*", async (route) => {
    if (route.request().method() === "PATCH") {
      await new Promise((resolve) => setTimeout(resolve, 6000)); // a very slow answer
    }
    await route.continue();
  });
  await page.goto("/admin/syllabus");
  await item(page, "Class 11").getByRole("button", { name: "Open" }).click();
  await item(page, "Physics").getByRole("button", { name: "Edit" }).click();
  await item(page, "Physics").getByLabel("Order (smaller comes first)").fill("3");
  await item(page, "Physics").getByRole("button", { name: "Save" }).click();
  await page
    .getByRole("navigation", { name: "Where you are" })
    .getByRole("button", { name: "All classes" })
    .click();
  // The slow save is still on its way, but this level is free to use.
  await expect(item(page, "Class 12").getByRole("button", { name: "Open" })).toBeEnabled({
    timeout: 2000,
  });
});
