import { expect, test } from "@playwright/test";

import {
  csrfOf,
  expectNoSeriousA11yViolations,
  finishedQuestion,
  signedInOwner,
  unique,
} from "./helpers";

// M4 PR 4j (F-01, F-02, F-03): the bank on the Questions page, in a real browser. The list, its
// count and filters, a search that forgives a typo, and the code box all come from the API.

test("the bank lists, counts, filters and searches questions, and opens one by its code", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Bank ${unique()}`);
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  const finishedId = await finishedQuestion(context, baseURL!);
  const opened = (await (await context.request.get(`/api/v1/questions/${finishedId}`)).json()) as {
    code: string;
    revision: number;
  };
  const submitted = await context.request.post(`/api/v1/questions/${finishedId}/submit`, {
    headers: { ...headers, "If-Match": `"rev-${opened.revision}"` },
  });
  expect(submitted.status()).toBe(200);
  const draft = await context.request.post("/api/v1/questions", {
    headers,
    data: {
      content: {
        schema_version: 1,
        question_type: "SCQ",
        stem: [{ kind: "paragraph", text: "A pendulum swings slowly in the lab." }],
      },
    },
  });
  expect(draft.status()).toBe(201);
  const pendulum = (await draft.json()) as { code: string };

  const page = await context.newPage();
  await page.goto("/questions");
  const bank = page.getByRole("region", { name: "Question bank" });
  const count = bank.getByRole("status");

  // Everything you may open, with its state and the start of its text.
  await expect(count).toHaveText("2 questions");
  await expect(bank.getByRole("link", { name: opened.code })).toBeVisible();
  await expect(bank.getByRole("link", { name: pendulum.code })).toBeVisible();
  await expect(bank).toContainText("A pendulum swings slowly in the lab.");
  await expect(bank).toContainText("In review");
  await expectNoSeriousA11yViolations(page);

  // A search, also with a typo.
  const search = bank.getByLabel("Search the stem, options and solution");
  await search.fill("pendulum");
  await expect(count).toHaveText("1 question matches");
  await expect(bank.getByRole("link", { name: pendulum.code })).toBeVisible();
  await expect(bank.getByRole("link", { name: opened.code })).toHaveCount(0);
  await search.fill("pendulm");
  await expect(bank.getByRole("link", { name: pendulum.code })).toBeVisible();
  await bank.getByRole("button", { name: "Clear" }).click();
  await expect(count).toHaveText("2 questions");

  // A filter narrows the list and the count.
  await bank.getByLabel("State", { exact: true }).selectOption("IN_REVIEW");
  await expect(count).toHaveText("1 question");
  await expect(bank.getByRole("link", { name: opened.code })).toBeVisible();
  await bank.getByLabel("State", { exact: true }).selectOption("PUBLISHED");
  await expect(count).toHaveText("0 questions");
  await expect(bank.getByText("Nothing matches. Try fewer filters.")).toBeVisible();
  await bank.getByRole("button", { name: "Clear" }).click();

  // The code box forgives case and dashes, and says when a code is unknown.
  const box = page.getByRole("form", { name: "Open by code" });
  await box.getByLabel("Code").fill("ZZZZZZZZ");
  await box.getByRole("button", { name: "Open" }).click();
  await expect(box.getByRole("alert")).toHaveText("No question has that code.");
  const typed = `${pendulum.code.slice(0, 4)}-${pendulum.code.slice(4)}`.toLowerCase();
  await box.getByLabel("Code").fill(typed);
  await box.getByRole("button", { name: "Open" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(pendulum.code);
});
