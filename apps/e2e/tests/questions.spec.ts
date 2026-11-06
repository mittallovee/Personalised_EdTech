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
  // The editor must be open and editable first: if the archive landed before the question was
  // read, the editor would open already archived and this would not test "archived while open".
  await expect(page.getByLabel("Question, block 1: paragraph")).toBeEnabled();
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

// M3 PR 3d-4 (D-15): the labels: syllabus, concepts, difficulty, Bloom, past-year details.

test("an author labels a question: syllabus, concepts, difficulty, Bloom and past-year details", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Labels ${unique()}`);
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  const post = async (path: string, data: object) => {
    const res = await context.request.post(path, { headers, data });
    expect(res.status()).toBe(201);
    return ((await res.json()) as { id: string }).id;
  };
  const node = (kind: string, parent_id: string | null, name: string) =>
    post("/api/v1/taxonomy/nodes", { kind, parent_id, name, sort_order: 1 });
  const class11 = await node("CLASS", null, "Class 11");
  const class12 = await node("CLASS", null, "Class 12");
  const physics = await node("SUBJECT", class11, "Physics");
  const chemistry = await node("SUBJECT", class11, "Chemistry");
  const mechanics = await node("CHAPTER", physics, "Mechanics");
  await node("TOPIC", mechanics, "Newton's laws");
  await node("CHAPTER", chemistry, "Atoms");
  void class12;
  const concept = (name: string) =>
    post("/api/v1/taxonomy/concepts", { subject_id: physics, name, aliases: [] });
  await concept("Newton's second law");
  await concept("Friction");
  await post("/api/v1/exams", { name: "JEE Main", short_code: "JM" });

  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /Single correct/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const findings = page.getByRole("region", { name: "Findings" });
  await expect(findings).toContainText("Add the labels");

  // The syllabus goes down one level at a time; a level waits for the one above it.
  const labels = page.getByRole("group", { name: "Labels" });
  await expect(labels.getByLabel("Subject")).toBeDisabled();
  await labels.getByLabel("Class").selectOption({ label: "Class 11" });
  await labels.getByLabel("Subject").selectOption({ label: "Physics" });
  await labels.getByLabel("Chapter").selectOption({ label: "Mechanics" });
  await labels.getByLabel(/^Topic/).selectOption({ label: "Newton's laws" });
  await expect(labels.getByLabel("Chapter").locator("option")).toHaveText(["Choose…", "Mechanics"]);

  // Concepts are searched among the subject's, and the main one is chosen.
  await labels.getByLabel("Search concepts").fill("fric");
  await expect(labels.getByLabel("Main concept").locator("option")).toHaveText([
    "Choose…",
    "Friction",
  ]);
  await labels.getByLabel("Main concept").selectOption({ label: "Friction" });
  await labels.getByLabel("Search concepts").fill("");
  await labels.getByLabel("Add another concept").selectOption({ label: "Newton's second law" });
  await expect(
    labels.getByRole("list", { name: "Other concepts" }).getByRole("listitem"),
  ).toContainText("Newton's second law");

  // Difficulty shows what its level means; Bloom is chosen from the list.
  await labels.getByLabel(/^Difficulty/).selectOption("4");
  await expect(labels.getByText(/^Difficulty 4:/)).toBeVisible();
  await labels.getByLabel("Bloom level").selectOption({ label: "Apply" });

  // Past-year details appear when it is a past-year question.
  await expect(labels.getByLabel(/^Exam/)).toHaveCount(0);
  await labels.getByLabel("This question was asked in a past-year exam").check();
  await labels.getByLabel(/^Exam/).selectOption({ label: "JEE Main (JM)" });
  await labels.getByLabel("Year", { exact: true }).fill("2024");
  await labels.getByLabel("Shift (optional)").fill("Shift 1");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  for (const gone of ["Choose the class", "Choose the topic", "Choose the main concept"]) {
    await expect(findings).not.toContainText(gone);
  }
  await expect(findings).not.toContainText("Choose the difficulty");
  await expect(findings).not.toContainText("Choose the Bloom level");
  await expect(findings).not.toContainText("Choose the exam");
  await expectNoSeriousA11yViolations(page);

  // It is really stored: a reload shows every choice, names and all.
  await page.reload();
  const again = page.getByRole("group", { name: "Labels" });
  await expect(again.getByLabel(/^Topic/)).toHaveValue(/.+/);
  await expect(again.getByLabel(/^Topic/).locator("option:checked")).toHaveText("Newton's laws");
  await expect(again.getByLabel("Main concept").locator("option:checked")).toHaveText("Friction");
  await expect(
    again.getByRole("list", { name: "Other concepts" }).getByRole("listitem"),
  ).toContainText("Newton's second law");
  await expect(again.getByLabel(/^Exam/).locator("option:checked")).toHaveText("JEE Main (JM)");
  await expect(again.getByLabel("Year", { exact: true })).toHaveValue("2024");

  // Another subject clears the chapter, topic and concepts, which belonged to the old one.
  await again.getByLabel("Subject").selectOption({ label: "Chemistry" });
  await expect(again.getByLabel("Chapter")).toHaveValue("");
  await expect(again.getByLabel(/^Topic/)).toHaveValue("");
  await expect(again.getByLabel("Main concept")).toHaveValue("");
  await expect(findings).toContainText("Choose the chapter");
  await expect(findings).toContainText("Choose the main concept");

  // Turning "past-year" off removes the exam details.
  await again.getByLabel("This question was asked in a past-year exam").uncheck();
  await expect(again.getByLabel(/^Exam/)).toHaveCount(0);
});

test("a year that is not a year is kept as typed and flagged by the server", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Labels ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /Integer/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const labels = page.getByRole("group", { name: "Labels" });
  await labels.getByLabel("This question was asked in a past-year exam").check();
  await labels.getByLabel("Year", { exact: true }).fill("20x4");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole("region", { name: "Findings" })).toContainText("year");
  await page.reload();
  await expect(
    page.getByRole("group", { name: "Labels" }).getByLabel("Year", { exact: true }),
  ).toHaveValue("20x4");
});

// M3 PR 3e: matching, assertion-reason and multiple-statement.

const settled = (page: import("@playwright/test").Page) =>
  expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({ timeout: 15_000 });

test("an assertion-reason question: assertion, reason, four options and the answer", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /Assertion/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const findings = page.getByRole("region", { name: "Findings" });
  await expect(findings).toContainText("Write the assertion");
  await expect(findings).toContainText("Write the reason");

  await page.getByLabel("Question, block 1: paragraph").fill("Read both statements.");
  await page.getByLabel("Assertion (A), block 1: paragraph").fill("Ice floats on water.");
  await page.getByLabel("Reason (R), block 1: paragraph").fill("Ice is less dense than water.");
  const wording = [
    "Both true, R explains A",
    "Both true, R does not explain A",
    "A only",
    "R only",
  ];
  for (const [index, letter] of ["A", "B", "C", "D"].entries()) {
    await page.getByLabel(`Option ${letter}, block 1: paragraph`).fill(wording[index]!);
  }
  await page.getByRole("radio", { name: "Option A is correct" }).check();
  await settled(page);
  await expect(findings).not.toContainText("Write the assertion");
  await expect(findings).not.toContainText("Write the reason");
  await expect(findings).not.toContainText("Choose the correct answer");
  await expectNoSeriousA11yViolations(page);

  await page.reload();
  await expect(page.getByLabel("Assertion (A), block 1: paragraph")).toHaveValue(
    "Ice floats on water.",
  );
  await expect(page.getByLabel("Reason (R), block 1: paragraph")).toHaveValue(
    "Ice is less dense than water.",
  );
  await expect(page.getByRole("radio", { name: "Option A is correct" })).toBeChecked();

  await page.getByRole("tab", { name: "Preview" }).click();
  const preview = page.locator(".qb-question");
  await expect(preview).toContainText("Ice floats on water.");
  await expect(preview).toContainText("Ice is less dense than water.");
});

test("a multiple-statement question: statements are added and removed, between 2 and 10", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /Multiple statement/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const statements = page.getByRole("group", { name: "Statements", exact: true });

  // It starts with two, and cannot go below two.
  await expect(statements.getByRole("button", { name: /^Remove Statement/ })).toHaveCount(2);
  await expect(statements.getByRole("button", { name: "Remove Statement 1" })).toBeDisabled();

  await page.getByLabel("Statement 1, block 1: paragraph").fill("Water boils at 100 C.");
  await page.getByLabel("Statement 2, block 1: paragraph").fill("Ice melts at 0 C.");
  await page.getByRole("button", { name: "Add statement" }).click();
  await page.getByLabel("Statement 3, block 1: paragraph").fill("Steam is a liquid.");
  await expect(statements.getByRole("button", { name: "Remove Statement 2" })).toBeEnabled();

  // Removing the middle one renumbers by position; the others keep their text.
  await page.getByRole("button", { name: "Remove Statement 2" }).click();
  await expect(page.getByLabel("Statement 2, block 1: paragraph")).toHaveValue(
    "Steam is a liquid.",
  );
  await expect(page.getByLabel("Statement 3, block 1: paragraph")).toHaveCount(0);

  // The most is ten.
  for (let count = 2; count < 10; count += 1) {
    await page.getByRole("button", { name: "Add statement" }).click();
  }
  await expect(page.getByRole("button", { name: "Add statement" })).toBeDisabled();
  await expect(statements).toContainText("10 of 10");

  await page.getByLabel("Option A, block 1: paragraph").fill("1 only");
  await page.getByRole("radio", { name: "Option A is correct" }).check();
  await settled(page);
  await page.reload();
  await expect(page.getByLabel("Statement 1, block 1: paragraph")).toHaveValue(
    "Water boils at 100 C.",
  );
  await expect(page.getByLabel("Statement 10, block 1: paragraph")).toBeVisible();
  await expect(page.getByRole("radio", { name: "Option A is correct" })).toBeChecked();
  await expectNoSeriousA11yViolations(page);
});

test("a matching question: two lists, what each option matches, and the correct option", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /Matching/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const findings = page.getByRole("region", { name: "Findings" });

  await page.getByLabel("List I item P, block 1: paragraph").fill("Speed");
  await page.getByLabel("List I item Q, block 1: paragraph").fill("Force");
  await page.getByLabel("List II item 1, block 1: paragraph").fill("newton");
  await page.getByLabel("List II item 2, block 1: paragraph").fill("metre per second");

  const tick = (option: string, from: string, to: string) =>
    page.getByRole("checkbox", { name: `Option ${option}: ${from} matches ${to}`, exact: true });
  await tick("A", "P", "2").check();
  await tick("A", "Q", "1").check();
  await tick("B", "P", "1").check();
  await tick("B", "Q", "2").check();
  await page.getByRole("radio", { name: "Option A is correct" }).check();
  await settled(page);
  await expect(findings).not.toContainText("Choose the correct answer");

  // A third item in List II appears in every option, and removing it takes it out again.
  await page.getByRole("button", { name: "Add List II item" }).click();
  await tick("A", "Q", "3").check();
  await expect(tick("C", "P", "3")).toBeVisible();
  await page.getByRole("button", { name: "Remove List II item 3" }).click();
  await expect(tick("A", "Q", "3")).toHaveCount(0);
  await expect(tick("A", "Q", "1")).toBeChecked();

  // In the correct option one List II item may not answer two List I items.
  await tick("A", "P", "1").check();
  await expect(findings).toContainText("can match only one", { timeout: 15_000 });
  await tick("A", "P", "1").uncheck();
  await settled(page);
  await expect(findings).not.toContainText("can match only one", { timeout: 15_000 });
  await expectNoSeriousA11yViolations(page);

  await page.reload();
  await expect(tick("A", "P", "2")).toBeChecked();
  await expect(tick("A", "Q", "1")).toBeChecked();
  await expect(tick("B", "P", "1")).toBeChecked();
  await expect(page.getByRole("radio", { name: "Option A is correct" })).toBeChecked();

  await page.getByRole("tab", { name: "Preview" }).click();
  await page.getByLabel("Show the answer and solution").check();
  const preview = page.locator(".qb-question");
  await expect(preview).toContainText("Speed");
  await expect(preview).toContainText("P → 2");
  await expect(preview.locator('[data-correct="true"]')).toContainText("Q → 1");
});

// M3 PR 3f: a live typeset preview under each block, and the visual equation editor (MathLive).

test("an equation shows as it will look, and can be written in the visual editor", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /Single correct/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const stem = page.getByRole("group", { name: "Question", exact: true });

  // Plain text has no preview; an inline equation in a paragraph does.
  await page.getByLabel("Question, block 1: paragraph").fill("A body of mass m moves.");
  await expect(stem.locator(".katex")).toHaveCount(0);
  await page
    .getByLabel("Question, block 1: paragraph")
    .fill(String.raw`A body of mass \(m\) moves.`);
  await expect(stem.locator(".katex")).toHaveCount(1);

  // A displayed equation shows beneath its source box as it is typed.
  await stem.getByRole("button", { name: "Add equation" }).click();
  await page.getByLabel("Question, block 2: equation").fill("x^2");
  await expect(stem.locator(".qb-live-preview .katex-display")).toHaveCount(1);

  // The visual editor starts from what is written and writes LaTeX back.
  await page.getByRole("button", { name: "Visual editor for Question, block 2" }).click();
  const editor = page.getByRole("group", { name: "Visual equation editor" });
  await expect(editor).toBeVisible();
  const field = editor.locator("math-field");
  await expect(field).toBeVisible({ timeout: 15_000 });
  // The left edge: the middle of the small box is its keyboard button.
  await field.click({ position: { x: 5, y: 10 } });
  await page.keyboard.press("Control+a");
  await page.keyboard.type("a/b");
  await expectNoSeriousA11yViolations(page);
  await editor.getByRole("button", { name: "Use this equation" }).click();
  await expect(editor).toHaveCount(0);
  await expect(page.getByLabel("Question, block 2: equation")).toHaveValue(/\\frac\{a\}\{b\}/);
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });

  // Cancel leaves the source as it was.
  await page.getByRole("button", { name: "Visual editor for Question, block 2" }).click();
  await editor.locator("math-field").click({ position: { x: 5, y: 10 } });
  await page.keyboard.press("Control+a");
  await page.keyboard.type("z");
  await editor.getByRole("button", { name: "Cancel" }).click();
  await expect(editor).toHaveCount(0);
  await expect(page.getByLabel("Question, block 2: equation")).toHaveValue(/\\frac\{a\}\{b\}/);

  // It is stored, and the preview shows it again after a reload.
  await page.reload();
  await expect(page.getByLabel("Question, block 2: equation")).toHaveValue(/\\frac\{a\}\{b\}/);
  await expect(
    page
      .getByRole("group", { name: "Question", exact: true })
      .locator(".qb-live-preview .katex-display"),
  ).toHaveCount(1);
});

test("an equation can be inserted into a paragraph at the cursor with the visual editor", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /Single correct/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const stem = page.getByRole("group", { name: "Question", exact: true });
  const paragraph = page.getByLabel("Question, block 1: paragraph");
  await expect(paragraph).toBeEnabled();

  // The cursor is after "Find ": the equation goes there, not at the end.
  await paragraph.fill("Find  now");
  await paragraph.press("Home");
  for (let i = 0; i < 5; i++) await paragraph.press("ArrowRight");
  await stem.getByRole("button", { name: "Insert equation in Question, block 1" }).click();
  const editor = page.getByRole("group", { name: "Visual equation editor" });
  const field = editor.locator("math-field");
  await expect(field).toBeVisible({ timeout: 15_000 });
  await field.click({ position: { x: 5, y: 10 } });
  await page.keyboard.type("a/b");
  await editor.getByRole("button", { name: "Use this equation" }).click();
  await expect(editor).toHaveCount(0);
  await expect(paragraph).toHaveValue(String.raw`Find \(\frac{a}{b}\) now`);
  await expect(stem.locator(".katex")).toHaveCount(1);
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });

  // Cancel changes nothing; typing in the paragraph while the editor is open closes it.
  await stem.getByRole("button", { name: "Insert equation in Question, block 1" }).click();
  await expect(editor).toBeVisible();
  await editor.getByRole("button", { name: "Cancel" }).click();
  await expect(paragraph).toHaveValue(String.raw`Find \(\frac{a}{b}\) now`);
  await stem.getByRole("button", { name: "Insert equation in Question, block 1" }).click();
  await expect(editor).toBeVisible();
  await paragraph.press("End");
  await paragraph.pressSequentially("!");
  await expect(editor).toHaveCount(0);
  await expect(paragraph).toHaveValue(String.raw`Find \(\frac{a}{b}\) now!`);
});

test("a broken equation is flagged beside its source, and the editor is not open for it", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /Integer/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const stem = page.getByRole("group", { name: "Question", exact: true });
  await stem.getByRole("button", { name: "Add equation" }).click();
  await page.getByLabel("Question, block 2: equation").fill(String.raw`\frac{1`);
  await expect(stem.locator(".qb-live-preview")).toContainText("could not be shown");
  await expect(page.getByRole("group", { name: "Visual equation editor" })).toHaveCount(0);
});

test("after a conflict, Reload closes an open visual editor so the other author's equation is not overwritten", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Questions ${unique()}`);
  const page = await context.newPage();
  await page.goto("/questions");
  await page.getByRole("radio", { name: /Integer/ }).check();
  await page.getByRole("button", { name: "Start question" }).click();
  const stem = page.getByRole("group", { name: "Question", exact: true });
  await stem.getByRole("button", { name: "Add equation" }).click();
  await page.getByLabel("Question, block 2: equation").fill("x^2");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await page.getByRole("button", { name: "Visual editor for Question, block 2" }).click();
  const editor = page.getByRole("group", { name: "Visual equation editor" });
  await expect(editor.locator("math-field")).toBeVisible({ timeout: 15_000 });

  // Another tab (here: the API) changes the equation.
  const id = page.url().split("/").pop()!;
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  const current = (await (await context.request.get(`/api/v1/questions/${id}`)).json()) as {
    revision: number;
    content: { stem: Record<string, unknown>[] } & Record<string, unknown>;
  };
  const stemNow = current.content.stem.map((block, index) =>
    index === 1 ? { ...block, source: "y^3" } : block,
  );
  const changed = await context.request.put(`/api/v1/questions/${id}/working-revision`, {
    headers: { ...headers, "If-Match": `"rev-${current.revision}"` },
    data: { content: { ...current.content, stem: stemNow } },
  });
  expect(changed.status()).toBe(200);

  // This tab saves next, finds out, and reloads: the other author's equation is shown, and the
  // visual editor, which still held the old one, is gone.
  await page.getByLabel("Question, block 1: paragraph").fill("Typed after the change elsewhere");
  await expect(page.getByText("Someone else changed this question.")).toBeVisible({
    timeout: 15_000,
  });
  await page.getByRole("button", { name: "Reload" }).click();
  await expect(page.getByLabel("Question, block 2: equation")).toHaveValue("y^3");
  await expect(page.getByRole("group", { name: "Visual equation editor" })).toHaveCount(0);
});
