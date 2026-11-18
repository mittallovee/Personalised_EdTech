import { expect, test } from "@playwright/test";

import {
  csrfOf,
  expectNoSeriousA11yViolations,
  finishedQuestion,
  signedInOwner,
  unique,
} from "./helpers";

// M4 PR 4k (E-08, E-09, D-16): a question's duplicates, history and comparison, in a real browser.
// What may be seen, what changed and what matches all come from the API.

const SAVED = /^(Saved \d|All changes saved)/;

test("the question page shows possible duplicates, the history and a comparison of two texts", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Compare ${unique()}`);
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  const firstId = await finishedQuestion(context, baseURL!);
  const first = (await (await context.request.get(`/api/v1/questions/${firstId}`)).json()) as {
    content: object;
  };
  // A second question with exactly the same content.
  const copied = await context.request.post("/api/v1/questions", {
    headers,
    data: { content: first.content },
  });
  expect(copied.status()).toBe(201);
  const copyCode = ((await copied.json()) as { code: string }).code;

  const page = await context.newPage();
  await page.goto(`/questions/${firstId}`);
  const heading = page.getByRole("heading", { level: 1 });
  await expect(heading).toContainText("Draft");

  // The copy is found, and the decision about it is recorded with a reason.
  const duplicates = page.getByRole("region", { name: "Possible duplicates" });
  await expect(duplicates.getByRole("link", { name: copyCode })).toBeVisible();
  await expect(duplicates).toContainText("Same content");
  await expectNoSeriousA11yViolations(page);
  const decide = duplicates.getByRole("group", { name: `Decide about ${copyCode}` });
  await decide.getByRole("button", { name: "Not a duplicate" }).click();
  const save = duplicates.getByRole("button", { name: "Save decision" });
  await expect(save).toBeDisabled();
  await duplicates.getByLabel("Why is it not a duplicate?").fill("A different pair of numbers.");
  await save.click();
  await expect(duplicates).toContainText(
    "You decided: not a duplicate. A different pair of numbers.",
  );

  // Two saved texts: submit, withdraw, change the stem, submit again.
  const bar = page.getByRole("group", { name: "Review steps" });
  await bar.getByRole("button", { name: "Submit for review" }).click();
  await expect(heading).toContainText("In review");
  await bar.getByRole("button", { name: "Withdraw to edit" }).click();
  await expect(heading).toContainText("Draft");
  await page.getByLabel("Question, block 1: paragraph").fill("What is 2 + 3 in total?");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await bar.getByRole("button", { name: "Submit for review" }).click();
  await expect(heading).toContainText("In review");

  // The history lists each step, oldest first.
  await page.getByRole("tab", { name: "History" }).click();
  const history = page.getByRole("region", { name: "History" });
  await expect(history.getByRole("listitem").first()).toContainText("Started by you");
  await expect(history).toContainText("Withdrawn from review by you");
  await expect(history.getByText("Submitted for review by you · version 1")).toHaveCount(2);
  await expectNoSeriousA11yViolations(page);

  // The comparison starts with the two newest texts and marks the words that changed.
  await page.getByRole("tab", { name: "Compare" }).click();
  const compare = page.getByRole("region", { name: "Compare" });
  await expect(compare.getByLabel("Older text")).toBeVisible();
  await expect(compare.locator("ins").filter({ hasText: "total" })).toBeVisible();
  await expect(compare.getByRole("list", { name: "Changes" })).toContainText("Question");
  await expectNoSeriousA11yViolations(page);

  // The same text against itself has no changes.
  const newer = await compare.getByLabel("Newer text").inputValue();
  await compare.getByLabel("Older text").selectOption(newer);
  await expect(compare.getByRole("status")).toHaveText("These two texts are the same.");
});
