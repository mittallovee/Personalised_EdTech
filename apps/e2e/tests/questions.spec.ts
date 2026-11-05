import { expect, test } from "@playwright/test";

import { expectNoSeriousA11yViolations, signedInOwner, unique } from "./helpers";

// M3 PR 3d-1 (D-11, E-04): an author starts a question, writes it, sees it saved by itself, looks
// at it as a student will, saves a checkpoint and archives it.

const SAVED = /^(Saved \d|All changes saved)/;

test("an author starts, writes, previews, checkpoints and archives a question", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/");
  await page.getByRole("link", { name: "Questions" }).click();
  await expect(page.getByRole("heading", { name: "Questions", level: 1 })).toBeVisible();
  await expect(page.getByText("No questions yet.")).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  // Start a single-correct question: it gets its permanent code at once and opens in the editor.
  await page
    .getByRole("form", { name: "Start a question" })
    .getByRole("radio", { name: /Single correct/ })
    .check();
  await page.getByRole("button", { name: "Start question" }).click();
  await expect(page).toHaveURL(/\/questions\/[0-9a-f-]{36}$/);
  const heading = page.getByRole("heading", { level: 1 });
  await expect(heading).toContainText("Question");
  await expect(heading).toContainText("Single correct");
  const code = (await heading.locator("span.font-mono").innerText()).trim();
  expect(code).toMatch(/^[0-9A-Z]{8}$/);

  // A new draft says what is still to do.
  const findings = page.getByRole("region", { name: "Findings" });
  await expect(findings).toContainText("Still to do");
  await expect(findings).toContainText("Write the question");

  // Typing is saved by itself a moment later, and the findings follow what was written.
  const stem = page.getByLabel("Question, block 1: paragraph");
  await stem.fill("A body of mass \\(m\\) moves at \\(v = 2\\) m/s. What is its momentum?");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await expect(findings).not.toContainText("Write the question");
  await expectNoSeriousA11yViolations(page);

  // It is really stored: a reload shows the same text.
  await page.reload();
  await expect(page.getByLabel("Question, block 1: paragraph")).toHaveValue(
    "A body of mass \\(m\\) moves at \\(v = 2\\) m/s. What is its momentum?",
  );

  // The preview shows it as a student will see it, with the equations typeset, and nothing about
  // the answer until asked.
  await page.getByRole("tab", { name: "Preview" }).click();
  await expect(page.getByText("A body of mass")).toBeVisible();
  await expect(page.locator(".katex").first()).toBeVisible();
  await expect(page.locator(".qb-question").getByText("Correct answer")).toHaveCount(0);
  await expectNoSeriousA11yViolations(page);
  await page.getByRole("tab", { name: "Edit" }).click();

  // A displayed equation can be added.
  await page.getByRole("button", { name: "Add equation" }).click();
  await page.getByLabel("Question, block 2: equation").fill("p = m v");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });

  // A checkpoint freezes what is there and the editing goes on.
  await page.getByRole("button", { name: "Save checkpoint" }).click();
  await expect(page.getByText("Checkpoint saved. You can keep editing.")).toBeVisible();
  await expect(page.getByLabel("Question, block 2: equation")).toHaveValue("p = m v");

  // Archive: hidden from the list, read-only, still found with the Archived filter; restore undoes it.
  await page.getByRole("button", { name: "Archive" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Archived" }).first()).toBeVisible();
  await expect(page.getByLabel("Question, block 1: paragraph")).toBeDisabled();
  await page.getByRole("link", { name: "Back to questions" }).click();
  await expect(page.getByText("No questions yet.")).toBeVisible();
  await page.getByLabel("Archived").check();
  await expect(page.getByRole("link", { name: new RegExp(code) })).toBeVisible();
  await page.getByRole("link", { name: new RegExp(code) }).click();
  await page.getByRole("button", { name: "Restore" }).click();
  await expect(page.getByLabel("Question, block 1: paragraph")).toBeEnabled();
  await page.getByRole("link", { name: "Back to questions" }).click();
  await expect(page.getByRole("link", { name: new RegExp(code) })).toBeVisible();
});

test("a typed-answer format starts too, and its preview shows an answer box", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /^Integer/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Integer");
  await page.getByLabel("Question, block 1: paragraph").fill("How many sides has a hexagon?");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await page.getByRole("tab", { name: "Preview" }).click();
  await expect(page.getByLabel("Your answer")).toBeDisabled();
});

test("a question that is not yours or does not exist says so", async ({ browser, baseURL }) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions/00000000-0000-4000-8000-000000000000");
  await expect(page.getByText("This question does not exist")).toBeVisible();
});
