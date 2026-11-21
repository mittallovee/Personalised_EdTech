import { readFile } from "node:fs/promises";

import { expect, test, type Page } from "@playwright/test";

import { expectNoSeriousA11yViolations, signedInOwner, unique } from "./helpers";

// M3 (C-03): the Owner imports a syllabus from a file: template, upload, preview, apply.

const HEADER = "kind,path,sort,aliases,label_hi,label_gu,label_bn,label_mr,label_te,label_ta";

/** A CSV file in the browser's file box, as if the person had picked it. */
async function pick(page: Page, name: string, text: string | Buffer) {
  await page.getByLabel(/^File/).setInputFiles({
    name,
    mimeType: "text/csv",
    buffer: Buffer.isBuffer(text) ? text : Buffer.from(text, "utf8"),
  });
}

async function openImport(page: Page) {
  await page.goto("/");
  await page.getByRole("link", { name: "Bulk import" }).click();
  await expect(page.getByRole("heading", { name: "Import syllabus", level: 1 })).toBeVisible();
}

test("the Owner downloads the template, previews it, applies it and finds nothing left to do", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Import ${unique()}`);
  const page = await context.newPage();
  await openImport(page);
  await expectNoSeriousA11yViolations(page);

  // The template downloads, and is itself a file the import accepts.
  const downloading = page.waitForEvent("download");
  await page.getByRole("link", { name: "Download the template" }).click();
  const download = await downloading;
  expect(download.suggestedFilename()).toBe("syllabus-template.csv");
  const template = await readFile((await download.path())!);
  expect(template.toString("utf8")).toContain(HEADER);

  await pick(page, "syllabus-template.csv", template);
  await page.getByRole("button", { name: "Check the file" }).click();
  await expect(
    page.getByRole("heading", { name: /Check the preview: syllabus-template.csv/ }),
  ).toBeVisible();
  await expect(page.getByLabel("Totals")).toContainText("5");
  const rows = page.getByRole("table");
  await expect(rows.getByRole("row")).toHaveCount(6); // header + 5 rows
  await expect(rows).toContainText("Class 11 > Physics > Newton's second law");
  await expectNoSeriousA11yViolations(page);

  // Applying is asked first, then done.
  await page.getByRole("button", { name: "Apply the import" }).click();
  await expect(page.getByRole("region", { name: "Apply this import?" })).toContainText(
    "Nothing is removed",
  );
  await page.getByRole("button", { name: "Apply", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("5 added");
  await expect(page.getByRole("button", { name: "Apply the import" })).toHaveCount(0);

  // The syllabus now has it.
  await page.getByRole("link", { name: "Syllabus" }).click();
  await expect(page.getByRole("list", { name: "Syllabus items" })).toContainText("Class 11");

  // The same file again: everything is already there, so there is nothing to apply.
  await openImport(page);
  await pick(page, "syllabus-template.csv", template);
  await page.getByRole("button", { name: "Check the file" }).click();
  await expect(page.getByText("Everything in this file is already in the syllabus.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Apply the import" })).toHaveCount(0);
});

test("a file with a wrong row shows the reason and cannot be applied", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Import errors ${unique()}`);
  const page = await context.newPage();
  await openImport(page);

  await pick(
    page,
    "wrong.csv",
    [HEADER, "CLASS,Class 12,1,,,,,,,", "PLANET,Class 12 > Mars,1,,,,,,,", ""].join("\r\n"),
  );
  await page.getByRole("button", { name: "Check the file" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("1 row has an error");
  await expect(page.getByRole("button", { name: "Apply the import" })).toHaveCount(0);

  // Only the errors, with the row number and the reason.
  await page.getByLabel("Show").selectOption("ERROR");
  const rows = page.getByRole("table").getByRole("row");
  await expect(rows).toHaveCount(2); // header + the one error
  await expect(rows.nth(1)).toContainText("3"); // the header is row 1
  await expect(rows.nth(1)).toContainText("Error");
  await expectNoSeriousA11yViolations(page);

  // A file that is not a spreadsheet at all is refused with a reason.
  await page.getByRole("button", { name: "Upload a different file" }).click();
  await pick(page, "notes.csv", Buffer.from([0xff, 0xfe, 0x00, 0x01, 0x02]));
  await page.getByRole("button", { name: "Check the file" }).click();
  await expect(page.getByRole("form", { name: "Upload a file" }).getByRole("alert")).toBeVisible();
});

test("a 5 MB file goes through the web app to the API, and a slow upload shows progress", async ({
  browser,
  baseURL,
}) => {
  test.setTimeout(120_000);
  const { context } = await signedInOwner(browser, baseURL!, `Import big ${unique()}`);
  const page = await context.newPage();
  await openImport(page);

  // About 4.9 MB, just under the limit: a class, a subject, a chapter, and many long topics.
  const lines = [
    HEADER,
    "CLASS,Big,1,,,,,,,",
    "SUBJECT,Big > S,1,,,,,,,",
    "CHAPTER,Big > S > C,1,,,,,,,",
  ];
  const filler = "x".repeat(140);
  const hindi = "अ".repeat(60);
  let size = lines.join("\r\n").length;
  for (let i = 0; size < 4.9 * 1024 * 1024; i++) {
    const line = `TOPIC,Big > S > C > Topic ${i} ${filler},${i % 1000},,${hindi},,,,,`;
    lines.push(line);
    size += Buffer.byteLength(line) + 2;
  }
  const file = Buffer.from(lines.join("\r\n") + "\r\n", "utf8");
  expect(file.length).toBeLessThan(5 * 1024 * 1024);
  expect(file.length).toBeGreaterThan(4.5 * 1024 * 1024);

  // The upload takes a few seconds on purpose, so the waiting message can be seen.
  await page.route("**/api/v1/taxonomy/imports?*", async (route) => {
    await new Promise((r) => setTimeout(r, 2500));
    await route.continue();
  });
  await pick(page, "big.csv", file);
  await page.getByRole("button", { name: "Check the file" }).click();
  await expect(page.getByRole("button", { name: "Checking the file…" })).toBeDisabled();
  await expect(page.getByRole("status")).toContainText("Reading big.csv");

  await expect(page.getByRole("heading", { name: /Check the preview: big.csv/ })).toBeVisible({
    timeout: 90_000,
  });
  await expect(page.getByLabel("Totals")).toContainText(String(lines.length - 1));
  await expect(page.getByRole("button", { name: "Show more rows" })).toBeVisible();
});

test("a file over 5 MB is refused before it is sent", async ({ browser, baseURL }) => {
  const { context } = await signedInOwner(browser, baseURL!, `Import huge ${unique()}`);
  const page = await context.newPage();
  await openImport(page);
  await pick(page, "huge.csv", Buffer.alloc(5 * 1024 * 1024 + 1, "a"));
  await expect(page.locator("main").getByRole("alert")).toContainText("bigger than 5 MB");
  await expect(page.getByRole("button", { name: "Check the file" })).toBeDisabled();
});

test("a valid file with more than 5,000 changes says why it cannot be applied", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Import limit ${unique()}`);
  const page = await context.newPage();
  await openImport(page);

  const lines = [
    HEADER,
    "CLASS,Lim,1,,,,,,,",
    "SUBJECT,Lim > S,1,,,,,,,",
    "CHAPTER,Lim > S > C,1,,,,,,,",
  ];
  for (let i = 0; i < 5000; i++) lines.push(`TOPIC,Lim > S > C > Topic ${i},${i},,,,,,,`);
  await pick(page, "many.csv", lines.join("\r\n") + "\r\n");
  await page.getByRole("button", { name: "Check the file" }).click();

  await expect(page.getByLabel("Totals")).toContainText("5003"); // no row is wrong
  await expect(page.getByRole("button", { name: "Apply the import" })).toHaveCount(0);
  await expect(page.locator("main").getByRole("alert")).toContainText("5,000");
  await expect(page.locator("main").getByRole("alert")).toContainText("Split");
});

test("while an import is being applied, another file cannot be started", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Import busy ${unique()}`);
  const page = await context.newPage();
  await openImport(page);
  await pick(page, "one.csv", [HEADER, "CLASS,Busy,1,,,,,,,", ""].join("\r\n"));
  await page.getByRole("button", { name: "Check the file" }).click();
  await expect(page.getByRole("button", { name: "Apply the import" })).toBeVisible();

  // The answer to "Apply" is slow; meanwhile the person tries to start over.
  await page.route("**/api/v1/taxonomy/imports/*/apply", async (route) => {
    await new Promise((r) => setTimeout(r, 2000));
    await route.continue();
  });
  await page.getByRole("button", { name: "Apply the import" }).click();
  await page.getByRole("button", { name: "Apply", exact: true }).click();
  await expect(page.getByRole("button", { name: "Upload a different file" })).toBeDisabled();

  // When the answer comes, the result of this import is what is shown.
  await expect(page.getByRole("status")).toContainText("1 added");
  await expect(page.getByRole("button", { name: "Import another file" })).toBeEnabled();
});

// C-14: a built-in syllabus is previewed and applied like a file, without uploading one.
test("the Owner loads a built-in syllabus, and loading it again adds nothing", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Starter ${unique()}`);
  const page = await context.newPage();
  await openImport(page);
  const starters = page.getByRole("list", { name: "Built-in syllabuses" });
  await expect(starters.getByRole("listitem")).toHaveCount(3);
  await expectNoSeriousA11yViolations(page);

  const physics = page.getByRole("button", { name: "Preview JEE Physics (Class 11 and 12)" });
  await physics.click();
  await expect(
    page.getByRole("heading", { name: /Check the preview: Built-in: JEE Physics/ }),
  ).toBeVisible();
  await expect(page.getByRole("table")).toContainText("Class 11 > Physics");

  await page.getByRole("button", { name: "Apply the import" }).click();
  await page.getByRole("button", { name: "Apply", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("added");
  await page.getByRole("link", { name: "Syllabus" }).click();
  await expect(page.getByRole("list", { name: "Syllabus items" })).toContainText("Class 11");

  await openImport(page);
  await physics.click();
  await expect(page.getByText("Everything in this file is already in the syllabus.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Apply the import" })).toHaveCount(0);
});

// Only one check at a time: a late answer must not replace the preview being read or applied.
test("a file and a built-in syllabus cannot be checked at the same time", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Starter busy ${unique()}`);
  const page = await context.newPage();
  await openImport(page);
  const checkFile = page.getByRole("button", { name: "Check the file" });
  const physics = page.getByRole("button", { name: "Preview JEE Physics (Class 11 and 12)" });
  const chemistry = page.getByRole("button", { name: "Preview JEE Chemistry (Class 11 and 12)" });

  // Hold the answer to the built-in preview: meanwhile the file cannot be sent.
  let release = () => {};
  const held = new Promise<void>((resolve) => (release = resolve));
  await page.route("**/api/v1/taxonomy/starter-syllabuses/*/imports", async (route) => {
    await held;
    await route.continue();
  });
  await pick(
    page,
    "one-class.csv",
    `${HEADER}
CLASS,Class 11,1,,,,,,,
`,
  );
  await expect(checkFile).toBeEnabled();
  await physics.click();
  await expect(checkFile).toBeDisabled();
  await expect(chemistry).toBeDisabled();
  release();
  await expect(
    page.getByRole("heading", { name: /Check the preview: Built-in: JEE Physics/ }),
  ).toBeVisible();

  // And the other way round: while a file is being checked, no built-in preview can start.
  await page.getByRole("button", { name: "Upload a different file" }).click();
  let releaseUpload = () => {};
  const heldUpload = new Promise<void>((resolve) => (releaseUpload = resolve));
  await page.route("**/api/v1/taxonomy/imports?*", async (route) => {
    await heldUpload;
    await route.continue();
  });
  await pick(
    page,
    "one-class.csv",
    `${HEADER}
CLASS,Class 11,1,,,,,,,
`,
  );
  await checkFile.click();
  await expect(physics).toBeDisabled();
  releaseUpload();
  await expect(
    page.getByRole("heading", { name: /Check the preview: one-class.csv/ }),
  ).toBeVisible();
});
