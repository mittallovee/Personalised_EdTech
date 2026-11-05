import { expect, test } from "@playwright/test";

import { csrfOf, expectNoSeriousA11yViolations, signedInOwner, unique } from "./helpers";

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
  await page
    .getByRole("group", { name: "Question", exact: true })
    .getByRole("button", { name: "Add equation" })
    .click();
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
  // The list keeps the filter you left it with (the app keeps a page's state while you are away),
  // so go back to the normal list before looking for the restored question.
  await page.getByLabel("Archived").uncheck();
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

// Review of the first version of this screen: typing must never be lost.

test("leaving the editor right after typing still saves what was typed", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("button", { name: "Start question" }).click();
  await expect(page).toHaveURL(/\/questions\/[0-9a-f-]{36}$/);
  const url = page.url();
  // Typed, and gone before the pause that normally triggers the save.
  await page.getByLabel("Question, block 1: paragraph").fill("Typed and left at once");
  await page.getByRole("link", { name: "Back to questions" }).click();
  await expect(page.getByRole("heading", { name: "Questions", level: 1 })).toBeVisible();
  await page.goto(url);
  await expect(page.getByLabel("Question, block 1: paragraph")).toHaveValue(
    "Typed and left at once",
  );
});

test("while a checkpoint is being saved the question cannot be edited, so nothing typed is lost", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("button", { name: "Start question" }).click();
  await page.getByLabel("Question, block 1: paragraph").fill("Before the checkpoint");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  // Slow the checkpoint down so the moment in between can be seen.
  await page.route("**/checkpoints", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    await route.continue();
  });
  await page.getByRole("button", { name: "Save checkpoint" }).click();
  await expect(page.getByLabel("Question, block 1: paragraph")).toBeDisabled();
  await expect(page.getByText("Checkpoint saved. You can keep editing.")).toBeVisible();
  await expect(page.getByLabel("Question, block 1: paragraph")).toBeEnabled();
  await expect(page.getByLabel("Question, block 1: paragraph")).toHaveValue(
    "Before the checkpoint",
  );
});

test("a question archived elsewhere while you type can still be restored, and your typing is kept", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("button", { name: "Start question" }).click();
  await expect(page).toHaveURL(/\/questions\/[0-9a-f-]{36}$/);
  const id = page.url().split("/").pop()!;
  // Another tab (here: the API) archives it.
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  const archived = await context.request.post(`/api/v1/questions/${id}/archive`, { headers });
  expect(archived.status()).toBe(200);
  // The next autosave finds out; the typing stays on screen.
  await page.getByLabel("Question, block 1: paragraph").fill("Typed while archived elsewhere");
  await expect(page.getByText("This question is archived. Restore it to change it.")).toBeVisible({
    timeout: 15_000,
  });
  await page.getByRole("button", { name: "Restore" }).click();
  await expect(page.getByLabel("Question, block 1: paragraph")).toBeEnabled();
  await expect(page.getByLabel("Question, block 1: paragraph")).toHaveValue(
    "Typed while archived elsewhere",
  );
  // And it is saved afterwards.
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await page.reload();
  await expect(page.getByLabel("Question, block 1: paragraph")).toHaveValue(
    "Typed while archived elsewhere",
  );
});

// M3 PR 3d-2: options, the answer and the solution of single and multiple correct questions.

test("an author writes the options, marks the correct one and adds a solution", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /Single correct/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const findings = page.getByRole("region", { name: "Findings" });
  await expect(findings).toContainText("Choose the correct answer");

  await page.getByLabel("Question, block 1: paragraph").fill("Which number is even?");
  const choices = ["1", "2", "3", "5"];
  for (const [index, letter] of ["A", "B", "C", "D"].entries()) {
    await page.getByLabel(`Option ${letter}, block 1: paragraph`).fill(choices[index]!);
  }
  await page.getByRole("radio", { name: "Option B is correct" }).check();
  await page
    .getByRole("group", { name: "Solution (optional)" })
    .getByRole("button", { name: "Add paragraph" })
    .click();
  await page.getByLabel("Solution (optional), block 1: paragraph").fill("Two is divisible by two.");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await expect(findings).not.toContainText("Choose the correct answer");
  await expectNoSeriousA11yViolations(page);

  // It is really stored.
  await page.reload();
  await expect(page.getByLabel("Option B, block 1: paragraph")).toHaveValue("2");
  await expect(page.getByRole("radio", { name: "Option B is correct" })).toBeChecked();
  await expect(page.getByLabel("Solution (optional), block 1: paragraph")).toHaveValue(
    "Two is divisible by two.",
  );

  // Marking another option moves the answer (one correct option in this format).
  await page.getByRole("radio", { name: "Option C is correct" }).check();
  await expect(page.getByRole("radio", { name: "Option B is correct" })).not.toBeChecked();
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });

  // The preview: options A to D, nothing about the answer until asked, then the right one and the solution.
  await page.getByRole("tab", { name: "Preview" }).click();
  const preview = page.locator(".qb-question");
  await expect(preview).toContainText("Which number is even?");
  await expect(preview.getByText("Correct answer")).toHaveCount(0);
  await expect(preview).not.toContainText("Two is divisible");
  await page.getByLabel("Show the answer and solution").check();
  await expect(preview.getByText("Correct answer")).toHaveCount(1);
  await expect(preview.locator('[data-correct="true"]')).toContainText("3");
  await expect(preview).toContainText("Two is divisible by two.");
  await expectNoSeriousA11yViolations(page);
});

test("a multiple-correct question can have several correct options, and none again", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /Multiple correct/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  await page.getByRole("checkbox", { name: "Option A is correct" }).check();
  await page.getByRole("checkbox", { name: "Option C is correct" }).check();
  const findings = page.getByRole("region", { name: "Findings" });
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await expect(findings).not.toContainText("Choose the correct answer");

  await page.reload();
  await expect(page.getByRole("checkbox", { name: "Option A is correct" })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: "Option B is correct" })).not.toBeChecked();
  await expect(page.getByRole("checkbox", { name: "Option C is correct" })).toBeChecked();

  await page.getByRole("tab", { name: "Preview" }).click();
  await page.getByLabel("Show the answer and solution").check();
  await expect(page.locator(".qb-question").getByText("Correct answer")).toHaveCount(2);

  // Unmarking both leaves no answer, and the findings say so again.
  await page.getByRole("tab", { name: "Edit" }).click();
  await page.getByRole("checkbox", { name: "Option A is correct" }).uncheck();
  await page.getByRole("checkbox", { name: "Option C is correct" }).uncheck();
  await expect(findings).toContainText("Choose the correct answer", { timeout: 15_000 });
});

// M3 PR 3d-3: the answers typed in (integer, single digit, numerical).

test("an integer answer is stored as a number, and a wrong one is flagged by the server", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /^Integer/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const findings = page.getByRole("region", { name: "Findings" });
  await expect(findings).toContainText("Choose the correct answer");
  const answer = page.getByRole("textbox", { name: "Correct answer" });

  await answer.fill("1000"); // above the default limit of 999
  await expect(findings).toContainText("Mistakes", { timeout: 15_000 });
  await answer.fill("999");
  await expect(findings).not.toContainText("Mistakes", { timeout: 15_000 });
  await expect(findings).not.toContainText("Choose the correct answer");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await expectNoSeriousA11yViolations(page);

  await page.reload();
  await expect(page.getByRole("textbox", { name: "Correct answer" })).toHaveValue("999");
  await page.getByRole("tab", { name: "Preview" }).click();
  await expect(page.locator(".qb-question")).not.toContainText("Answer: 999");
  await page.getByLabel("Show the answer and solution").check();
  await expect(page.locator(".qb-question")).toContainText("Answer: 999");
});

test("a single-digit answer takes 0 to 9 only", async ({ browser, baseURL }) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /^Single digit/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const findings = page.getByRole("region", { name: "Findings" });
  const answer = page.getByRole("textbox", { name: "Correct answer" });
  await answer.fill("12");
  await expect(findings).toContainText("Mistakes", { timeout: 15_000 });
  await answer.fill("5");
  await expect(findings).not.toContainText("Mistakes", { timeout: 15_000 });
  await expect(findings).not.toContainText("Choose the correct answer");
});

test("a numerical answer is an exact value or a range, kept exactly as typed", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /^Numerical/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const findings = page.getByRole("region", { name: "Findings" });
  await expect(findings).toContainText("Choose the correct answer");

  // More than two decimal places is kept and flagged, never rounded.
  await page.getByRole("textbox", { name: "Value" }).fill("9.805");
  await expect(findings).toContainText("Mistakes", { timeout: 15_000 });
  await page.reload();
  await expect(page.getByRole("textbox", { name: "Value" })).toHaveValue("9.805");
  await page.getByRole("textbox", { name: "Value" }).fill("9.81");
  await expect(findings).not.toContainText("Mistakes", { timeout: 15_000 });

  // Switch to a range.
  await page.getByRole("radio", { name: "A range" }).check();
  await page.getByRole("textbox", { name: "From" }).fill("9.79");
  await page.getByRole("textbox", { name: "To" }).fill("9.81");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await expect(findings).not.toContainText("Mistakes");
  await expect(findings).not.toContainText("Choose the correct answer");
  await expectNoSeriousA11yViolations(page);

  await page.reload();
  await expect(page.getByRole("radio", { name: "A range" })).toBeChecked();
  await expect(page.getByRole("textbox", { name: "From" })).toHaveValue("9.79");
  await expect(page.getByRole("textbox", { name: "To" })).toHaveValue("9.81");
  await page.getByRole("tab", { name: "Preview" }).click();
  await page.getByLabel("Show the answer and solution").check();
  await expect(page.locator(".qb-question")).toContainText("Answer: 9.79 to 9.81");
});

test("after a conflict, Reload shows the other tab's kind of numerical answer, not the old one", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /^Numerical/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  await page.getByRole("textbox", { name: "Value" }).fill("9.81");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });

  // Another tab (here: the API) turns the answer into a range.
  const id = page.url().split("/").pop()!;
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  const current = (await (await context.request.get(`/api/v1/questions/${id}`)).json()) as {
    revision: number;
    content: Record<string, unknown>;
  };
  const changed = await context.request.put(`/api/v1/questions/${id}/working-revision`, {
    headers: { ...headers, "If-Match": `"rev-${current.revision}"` },
    data: {
      content: { ...current.content, answer: { mode: "range", lower: "1.00", upper: "2.00" } },
    },
  });
  expect(changed.status()).toBe(200);

  // This tab saves next, finds out, and offers to reload.
  await page.getByLabel("Question, block 1: paragraph").fill("Typed after the change elsewhere");
  await expect(page.getByText("Someone else changed this question.")).toBeVisible({
    timeout: 15_000,
  });
  await page.getByRole("button", { name: "Reload" }).click();
  await expect(page.getByRole("radio", { name: "A range" })).toBeChecked();
  await expect(page.getByRole("textbox", { name: "From" })).toHaveValue("1.00");
  await expect(page.getByRole("textbox", { name: "To" })).toHaveValue("2.00");
});
