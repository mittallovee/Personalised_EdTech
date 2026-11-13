import { expect, test } from "@playwright/test";

import { csrfOf, expectNoSeriousA11yViolations, signedInOwner, unique } from "./helpers";

// M3 PR 3i-2 (D-03): an admin changes the answer limits for the coaching and for one exam, and the
// checks on a question follow.

const HIGHEST = "Coaching, Integer answers: Highest key";
const LOWEST = "Coaching, Integer answers: Lowest key";
const SAVED_NOTICE = "Saved. The checks use these limits from now on.";

test("an admin changes the answer limits, for the coaching and for one exam", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Limits ${unique()}`);
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  const exam = await context.request.post("/api/v1/exams", {
    data: { name: "JEE Advanced" },
    headers,
  });
  expect(exam.ok()).toBeTruthy();

  const page = await context.newPage();
  await page.goto("/");
  await page.getByRole("link", { name: "Answer limits" }).click();
  await expect(page.getByRole("heading", { name: "Answer limits", level: 1 })).toBeVisible();

  // The built-in values are shown, with the widest range each may take.
  await expect(page.getByLabel(HIGHEST, { exact: true })).toHaveValue("999");
  await expect(page.getByLabel(LOWEST, { exact: true })).toHaveValue("0");
  await expect(
    page.getByLabel("Coaching, Numerical answers: Highest key", { exact: true }),
  ).toHaveValue("999.00");
  await expect(page.getByText("From -999999 to 999999").first()).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  // A box that is not a number is named, and nothing is sent.
  await page.getByLabel(HIGHEST, { exact: true }).fill("12.5");
  await page.getByRole("button", { name: "Save limits" }).click();
  await expect(page.getByText("Use a whole number")).toBeVisible();
  await expect(page.getByText(SAVED_NOTICE)).toHaveCount(0);

  // A minimum above its maximum is refused by the server and explained.
  await page.getByLabel(HIGHEST, { exact: true }).fill("100");
  await page.getByLabel(LOWEST, { exact: true }).fill("5000");
  await page.getByRole("button", { name: "Save limits" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "integer_min is above integer_max" }),
  ).toBeVisible();

  // A good change is saved, and kept after a reload.
  await page.getByLabel(LOWEST, { exact: true }).fill("0");
  await page.getByLabel(HIGHEST, { exact: true }).fill("9999");
  await page.getByRole("button", { name: "Save limits" }).click();
  await expect(page.getByText(SAVED_NOTICE)).toBeVisible();
  await page.reload();
  await expect(page.getByLabel(HIGHEST, { exact: true })).toHaveValue("9999");

  // The checks on a question follow: a key of 5000 is fine now.
  const question = (answer: number) => ({
    content: {
      schema_version: 1,
      question_type: "INTEGER",
      language: "en",
      stem: [{ kind: "paragraph", text: "How many?" }],
      answer: { value: answer },
    },
  });
  const made = await context.request.post("/api/v1/questions", { data: question(5000), headers });
  const outOfRange = (body: { findings: { code: string }[] }) =>
    body.findings.some((f) => f.code === "ANSWER_OUT_OF_RANGE");
  const created = await made.json();
  expect(outOfRange(created)).toBe(false);

  // One exam may have its own limits.
  await page.getByLabel("Add limits for an exam").selectOption({ label: "JEE Advanced" });
  const examBox = page.getByLabel("JEE Advanced, Integer answers: Highest key", { exact: true });
  await expect(examBox).toHaveValue("");
  await expect(examBox).toHaveAttribute("placeholder", "9999"); // what it would otherwise be
  await examBox.fill("99999");
  await page.getByRole("button", { name: "Save limits" }).click();
  await expect(page.getByText(SAVED_NOTICE)).toBeVisible();
  await page.reload();
  await expect(
    page.getByLabel("JEE Advanced, Integer answers: Highest key", { exact: true }),
  ).toHaveValue("99999");
  await expect(page.getByLabel("Add limits for an exam")).toBeDisabled(); // no other exam to add
  await expectNoSeriousA11yViolations(page);

  // Lowering the limit makes the same saved question show the finding, without changing it.
  await page.getByLabel(HIGHEST, { exact: true }).fill("100");
  await page.getByRole("button", { name: "Save limits" }).click();
  await expect(page.getByText(SAVED_NOTICE)).toBeVisible();
  const again = await (await context.request.get(`/api/v1/questions/${created.id}`)).json();
  expect(outOfRange(again)).toBe(true);
  expect(again.content).toEqual(created.content);

  // Removing the exam's limits takes them away.
  await page.getByRole("button", { name: "Remove the limits for JEE Advanced" }).click();
  await page.getByRole("button", { name: "Save limits" }).click();
  await expect(page.getByText(SAVED_NOTICE)).toBeVisible();
  await page.reload();
  await expect(
    page.getByLabel("JEE Advanced, Integer answers: Highest key", { exact: true }),
  ).toHaveCount(0);
});

test("a stale screen is not allowed to overwrite newer limits", async ({ browser, baseURL }) => {
  const { context } = await signedInOwner(browser, baseURL!, `Limits ${unique()}`);
  const headers = { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) };
  const page = await context.newPage();
  await page.goto("/admin/answer-limits");
  await expect(page.getByLabel(HIGHEST, { exact: true })).toHaveValue("999");

  // Another admin (here, the API) saves first.
  const other = await context.request.put("/api/v1/settings/answer-rules", {
    data: { defaults: { integer_max: 500 }, exams: {} },
    headers: { ...headers, "If-Match": '"rev-0"' },
  });
  expect(other.ok()).toBeTruthy();

  await page.getByLabel(HIGHEST, { exact: true }).fill("2000");
  await page.getByRole("button", { name: "Save limits" }).click();
  await expect(page.getByText("Someone else changed these limits")).toBeVisible();
  await page.getByRole("button", { name: "Reload" }).click();
  await expect(page.getByLabel(HIGHEST, { exact: true })).toHaveValue("500");
});
