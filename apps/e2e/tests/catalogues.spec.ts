import { expect, test, type Page } from "@playwright/test";

import { csrfOf, expectNoSeriousA11yViolations, signedInOwner, unique } from "./helpers";

// M3 (C-02, C-03, C-11, C-13): the Owner keeps concepts (with aliases) per subject, and the exams
// and sources questions can point to.

/** One entry of a named list on the screen, found by its name. */
function entry(page: Page, list: string, name: string) {
  return page.getByRole("list", { name: list }).getByRole("listitem").filter({ hasText: name });
}

test("the Owner adds, edits, searches, retires and restores concepts with aliases", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Concepts ${unique()}`);
  // A class and a subject to file concepts under, through the API (syllabus.spec.ts covers the screen).
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  const made = async (data: object) => {
    const res = await context.request.post("/api/v1/taxonomy/nodes", { headers, data });
    expect(res.status()).toBe(201);
    return ((await res.json()) as { id: string }).id;
  };
  const classId = await made({ kind: "CLASS", parent_id: null, name: "Class 11", sort_order: 1 });
  await made({ kind: "SUBJECT", parent_id: classId, name: "Physics", sort_order: 1 });

  const page = await context.newPage();
  await page.goto("/");
  await page.getByRole("link", { name: "Concepts" }).click();
  await expect(page.getByRole("heading", { name: "Concepts", level: 1 })).toBeVisible();
  await page.getByLabel("Subject").selectOption({ label: "Class 11 › Physics" });
  await expect(page.getByText("No concepts yet.")).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  // Add a concept with two aliases.
  const add = page.getByRole("form", { name: "Add a concept" });
  await add.getByLabel("Name (English)").fill("Newton's second law");
  await add.getByLabel(/^Aliases/).fill("F = ma\nNewton's 2nd law");
  await add.getByRole("button", { name: "Add concept" }).click();
  const law = entry(page, "Concepts", "Newton's second law");
  await expect(law).toContainText("Also called: F = ma · Newton's 2nd law");

  // The same name twice in a subject is refused, with the API's reason.
  await add.getByLabel("Name (English)").fill("newton's second law");
  await add.getByRole("button", { name: "Add concept" }).click();
  await expect(add.getByRole("alert")).toContainText("already");

  // Edit: rename, change the aliases, add a Hindi name.
  await add.getByLabel("Name (English)").fill("Work-energy theorem");
  await add.getByRole("button", { name: "Add concept" }).click();
  await expect(entry(page, "Concepts", "Work-energy theorem")).toBeVisible();
  await law.getByRole("button", { name: "Edit" }).click();
  const edit = law.getByRole("form", { name: "Edit Newton's second law" });
  await edit.getByLabel("Name (English)").fill("Newton's second law of motion");
  await edit.getByLabel(/^Aliases/).fill("F = ma");
  await edit.getByLabel(/^Hindi/).fill("न्यूटन का द्वितीय नियम");
  await edit.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("status")).toContainText("Newton's second law of motion was saved.");
  const renamed = entry(page, "Concepts", "Newton's second law of motion");
  await expect(renamed).toContainText("Also called: F = ma");
  await expect(renamed).not.toContainText("2nd law");
  await expect(renamed).toContainText("Hindi: न्यूटन का द्वितीय नियम");

  // Search finds a concept by one of its aliases.
  await page.getByLabel("Search names and aliases").fill("F = ma");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(renamed).toBeVisible();
  await expect(entry(page, "Concepts", "Work-energy theorem")).toHaveCount(0);
  await page.getByLabel("Search names and aliases").fill("nothing like this");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page.getByText("No concept matches that search.")).toBeVisible();
  await page.getByLabel("Search names and aliases").fill("");
  await page.getByRole("button", { name: "Search" }).click();

  // Retire (asked first), then restore.
  await renamed.getByRole("button", { name: "Retire" }).click();
  await expect(renamed.getByRole("region", { name: /^Retire / })).toContainText(
    "nothing is deleted",
  );
  await renamed.getByRole("button", { name: "Retire", exact: true }).last().click();
  await expect(renamed).toContainText("Retired");
  await expect(renamed.getByRole("button", { name: "Edit" })).toHaveCount(0);
  await expectNoSeriousA11yViolations(page);
  await renamed.getByRole("button", { name: "Restore" }).click();
  await expect(renamed).not.toContainText("Retired");
});

test("the Owner keeps exams and sources: add, edit, filter, retire and restore", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Exams ${unique()}`);
  const page = await context.newPage();
  await page.goto("/");
  await page.getByRole("link", { name: "Exams & sources" }).click();
  await expect(page.getByRole("heading", { name: "Exams & sources", level: 1 })).toBeVisible();
  await expect(page.getByText("No exams yet.")).toBeVisible();
  await expect(page.getByText("No sources yet.")).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  // Exams: add with a short code, refuse a repeat, edit (and clear the code), retire, restore.
  const addExam = page.getByRole("form", { name: "Add an exam" });
  await addExam.getByLabel("Name").fill("JEE Main");
  await addExam.getByLabel(/^Short code/).fill("JEEM");
  await addExam.getByRole("button", { name: "Add exam" }).click();
  const jee = entry(page, "Exams", "JEE Main");
  await expect(jee).toContainText("Short code JEEM");
  await addExam.getByLabel("Name").fill("jee main");
  await addExam.getByRole("button", { name: "Add exam" }).click();
  await expect(addExam.getByRole("alert")).toContainText("already");

  await jee.getByRole("button", { name: "Edit" }).click();
  const editExam = jee.getByRole("form", { name: "Edit JEE Main" });
  await editExam.getByLabel("Name").fill("JEE Main (NTA)");
  await editExam.getByLabel(/^Short code/).fill("");
  await editExam.getByRole("button", { name: "Save" }).click();
  const nta = entry(page, "Exams", "JEE Main (NTA)");
  await expect(nta).toBeVisible();
  await expect(nta).not.toContainText("Short code");

  await nta.getByRole("button", { name: "Retire" }).click();
  await nta.getByRole("button", { name: "Retire", exact: true }).last().click();
  await expect(nta).toContainText("Retired");
  await nta.getByRole("button", { name: "Restore" }).click();
  await expect(nta).not.toContainText("Retired");

  // Sources: add two kinds, filter by kind, edit the name, retire and restore.
  const addSource = page.getByRole("form", { name: "Add a source" });
  await addSource.getByLabel("Kind").selectOption("BOOK");
  await addSource.getByLabel("Name").fill("HC Verma, Concepts of Physics");
  await addSource.getByRole("button", { name: "Add source" }).click();
  const book = entry(page, "Sources", "HC Verma");
  await expect(book).toContainText("Book");
  await addSource.getByLabel("Kind").selectOption("PYQ_PAPER");
  await addSource.getByLabel("Name").fill("JEE Main 2024 Shift 1");
  await addSource.getByRole("button", { name: "Add source" }).click();
  const paper = entry(page, "Sources", "JEE Main 2024");
  await expect(paper).toContainText("Previous-year paper");

  await page.getByLabel("Show").selectOption("BOOK");
  await expect(book).toBeVisible();
  await expect(paper).toHaveCount(0);
  await page.getByLabel("Show").selectOption("");
  await expect(paper).toBeVisible();

  await book.getByRole("button", { name: "Edit" }).click();
  const editSource = book.getByRole("form", { name: /^Edit HC Verma/ });
  await editSource.getByLabel(/^Name/).fill("HC Verma, Concepts of Physics Vol 1");
  await editSource.getByRole("button", { name: "Save" }).click();
  const vol1 = entry(page, "Sources", "Vol 1");
  await expect(vol1).toBeVisible();
  await vol1.getByRole("button", { name: "Retire" }).click();
  await vol1.getByRole("button", { name: "Retire", exact: true }).last().click();
  await expect(vol1).toContainText("Retired");
  await expectNoSeriousA11yViolations(page);
  await vol1.getByRole("button", { name: "Restore" }).click();
  await expect(vol1).not.toContainText("Retired");
});

test("a save that finishes after you changed the source filter does not bring back the old list", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Late save ${unique()}`);
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  for (const [kind, name] of [
    ["BOOK", "Late Book"],
    ["PYQ_PAPER", "Late Paper"],
  ]) {
    const res = await context.request.post("/api/v1/sources", { headers, data: { kind, name } });
    expect(res.status()).toBe(201);
  }
  const page = await context.newPage();
  await page.goto("/admin/exams-sources");
  await expect(entry(page, "Sources", "Late Book")).toBeVisible();

  // The save is slow; while it is on its way, the person narrows the list to papers.
  await page.route("**/api/v1/sources/*", async (route) => {
    if (route.request().method() === "PATCH") await new Promise((r) => setTimeout(r, 1500));
    await route.continue();
  });
  const book = entry(page, "Sources", "Late Book");
  await book.getByRole("button", { name: "Edit" }).click();
  await book
    .getByRole("form", { name: "Edit Late Book" })
    .getByLabel(/^Name/)
    .fill("Late Book, 2nd edition");
  await book.getByRole("button", { name: "Save" }).click();
  await page.getByLabel("Show").selectOption("PYQ_PAPER");
  await expect(entry(page, "Sources", "Late Paper")).toBeVisible();

  // When the save answers, the list still shows only what the filter asks for.
  await expect(page.getByRole("status")).toContainText("Late Book, 2nd edition was saved.");
  await expect(entry(page, "Sources", "Late Paper")).toBeVisible();
  await expect(entry(page, "Sources", "Late Book")).toHaveCount(0);
});
