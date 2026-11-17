import { expect, test, type Page } from "@playwright/test";

import { expectNoSeriousA11yViolations, finishedQuestion, signedInOwner, unique } from "./helpers";

// M4 PR 4h (E-01, E-04, E-06, E-07): the review steps on the question page, in a real browser. The
// Owner holds every grant, so one person can take each step (E-02). The page shows exactly the steps
// the API allows; the editor is read-only once submitted; a return needs a reason and a note.

async function step(page: Page, name: string) {
  await page.getByRole("group", { name: "Review steps" }).getByRole("button", { name }).click();
}

test("a question goes through review: submit, return, resubmit, QC, approve, publish, correct", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Workflow ${unique()}`);
  const questionId = await finishedQuestion(context, baseURL!);
  const page = await context.newPage();
  await page.goto(`/questions/${questionId}`);
  const heading = page.getByRole("heading", { level: 1 });
  const bar = page.getByRole("group", { name: "Review steps" });

  // A draft: editable, its findings are findings, and it can be submitted.
  await expect(heading).toContainText("Draft");
  await expect(page.getByRole("region", { name: "Findings" })).toContainText(
    "Nothing left to fix.",
  );
  await expect(bar.getByRole("button")).toHaveText(["Submit for review"]);

  // Submitted: read-only, the findings become the publication checklist.
  await step(page, "Submit for review");
  await expect(heading).toContainText("In review");
  await expect(page.getByText("Submitted for review.")).toBeVisible();
  await expect(page.getByRole("region", { name: "Publication checklist" })).toBeVisible();
  await expect(page.getByText("cannot be edited. Withdraw it to make changes.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save checkpoint" })).toHaveCount(0);
  await expect(bar.getByRole("button")).toHaveText([
    "Pass QC",
    "Return to the author",
    "Withdraw to edit",
  ]);
  await expectNoSeriousA11yViolations(page);

  // Return: the form waits for a reason and a note, then sends it back.
  await step(page, "Return to the author");
  const form = page.getByRole("form", { name: "Return to the author" });
  const send = form.getByRole("button", { name: "Return to the author" });
  await expect(send).toBeDisabled();
  await form.getByLabel("The answer is wrong or does not match the question").check();
  await form.getByLabel("What should the author fix?").fill("Check the answer key against B.");
  await expect(send).toBeEnabled();
  await expectNoSeriousA11yViolations(page);
  await send.click();
  await expect(heading).toContainText("Returned to the author");
  await expect(page.getByText("Returned to the author with your reasons.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save checkpoint" })).toBeVisible();

  // Resubmitted, then each later step in turn.
  await step(page, "Submit for review");
  await expect(heading).toContainText("In review");
  await step(page, "Pass QC");
  await expect(heading).toContainText("QC passed");
  await step(page, "Approve");
  await expect(heading).toContainText("Approved");

  // Publishing asks first.
  await step(page, "Publish");
  const confirm = page.getByRole("region", { name: "Publish this question?" });
  await confirm.getByRole("button", { name: "Publish" }).click();
  await expect(heading).toContainText("Published");
  await expect(page.getByText("A published question never changes.")).toBeVisible();
  await expect(bar.getByRole("button")).toHaveText(["Start a correction"]);

  // A correction is version 2, a draft again; the published version stays as it was.
  await step(page, "Start a correction");
  await page
    .getByRole("region", { name: "Start a correction?" })
    .getByRole("button", { name: "Start the correction" })
    .click();
  await expect(heading).toContainText("Draft");
  await expect(page.getByRole("status").filter({ hasText: "version 2" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save checkpoint" })).toBeVisible();
});

test("a step taken on an out-of-date screen is refused and the screen offers to reload", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Workflow race ${unique()}`);
  const questionId = await finishedQuestion(context, baseURL!);
  const first = await context.newPage();
  const second = await context.newPage();
  await first.goto(`/questions/${questionId}`);
  await second.goto(`/questions/${questionId}`);
  await expect(second.getByRole("heading", { level: 1 })).toContainText("Draft");

  await step(first, "Submit for review");
  await expect(first.getByRole("heading", { level: 1 })).toContainText("In review");

  // The second tab still shows the draft; its submit is refused, not repeated.
  await step(second, "Submit for review");
  const alert = second.getByRole("alert");
  await expect(alert).toBeVisible();
  await alert.getByRole("button", { name: "Reload" }).click();
  await expect(second.getByRole("heading", { level: 1 })).toContainText("In review");
});
