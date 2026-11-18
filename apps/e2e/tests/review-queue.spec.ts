import { expect, test } from "@playwright/test";

import {
  csrfOf,
  expectNoSeriousA11yViolations,
  finishedQuestion,
  signedInOwner,
  unique,
} from "./helpers";

// M4 PR 4i (E-05, I-01): the review queue and the notifications, in a real browser. The Owner holds
// every review grant, so the Owner's own submitted question waits in their queue, and a return of
// it tells the Owner (as its author) in the notifications.

test("the queue lists what waits, by tab and filter, and a return reaches the author's notifications", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Queue ${unique()}`);
  const questionId = await finishedQuestion(context, baseURL!);
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  const opened = await (await context.request.get(`/api/v1/questions/${questionId}`)).json();
  const submitted = await context.request.post(`/api/v1/questions/${questionId}/submit`, {
    headers: { ...headers, "If-Match": `"rev-${opened.revision}"` },
  });
  expect(submitted.status()).toBe(200);
  const question = (await submitted.json()) as { code: string; flow_etag: string };

  // The queue: the question waits for QC, and the count says so.
  const page = await context.newPage();
  await page.goto("/");
  await page
    .getByRole("navigation", { name: "Modules" })
    .getByRole("link", { name: "Review" })
    .click();
  await expect(page.getByRole("heading", { level: 1, name: "Review" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Waiting for QC (1)" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByRole("link", { name: question.code })).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  // Filters narrow it: nothing in Hindi, and nothing waiting for approval yet.
  await page.getByLabel("Language").selectOption("hi");
  await expect(page.getByText("Nothing is waiting here.")).toBeVisible();
  await page.getByRole("button", { name: "Clear filters" }).click();
  await expect(page.getByRole("link", { name: question.code })).toBeVisible();
  await page.getByRole("tab", { name: /Waiting for approval/ }).click();
  await expect(page.getByText("Nothing is waiting here.")).toBeVisible();
  await page.getByRole("tab", { name: /Waiting for QC/ }).click();

  // A row opens the question.
  await page.getByRole("link", { name: question.code }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("In review");

  // Returning it tells the author (the Owner): the bell shows one unread.
  const returned = await context.request.post(`/api/v1/questions/${questionId}/return`, {
    headers: { ...headers, "If-Match": question.flow_etag },
    data: { reasons: ["ANSWER_WRONG"], note: "Check the answer key against B." },
  });
  expect(returned.status()).toBe(200);
  await page.goto("/");
  const bell = page.getByRole("link", { name: "Notifications 1 unread" });
  await expect(bell).toBeVisible();

  // The notification says why, and opening it marks it read.
  await bell.click();
  const list = page.getByRole("list", { name: "Your notifications" });
  await expect(list).toContainText(`Question ${question.code} was returned to you`);
  await expect(list).toContainText("The answer is wrong or does not match the question");
  await expect(list).toContainText("Note: Check the answer key against B.");
  await expectNoSeriousA11yViolations(page);
  await list.getByRole("link", { name: `Question ${question.code} was returned to you` }).click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Returned to the author");
  await expect(page.getByRole("link", { name: "Notifications", exact: true })).toBeVisible();

  // Back in the queue, it is under "Returned to me", and no longer waits for QC.
  await page.goto("/review");
  await expect(page.getByRole("tab", { name: "Waiting for QC (0)" })).toBeVisible();
  await page.getByRole("tab", { name: "Returned to me (1)" }).click();
  await expect(page.getByRole("link", { name: question.code })).toBeVisible();
});
