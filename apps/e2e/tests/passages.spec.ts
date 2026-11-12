import { expect, test } from "@playwright/test";

import { csrfOf, expectNoSeriousA11yViolations, signedInOwner, unique } from "./helpers";

// M3 PR 3h-3 (D-14): an author writes a passage, saves a checkpoint, adds a question under it, and
// sees which questions are on an older checkpoint after the passage changes.

const SAVED = /^(Saved \d|All changes saved)/;

test("an author writes a passage, saves a checkpoint and adds a question under it", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Passages ${unique()}`);
  const page = await context.newPage();
  await page.goto("/");
  await page.getByRole("link", { name: "Passages" }).click();
  await expect(page.getByRole("heading", { name: "Passages", level: 1 })).toBeVisible();
  await expect(page.getByText("No passages yet.")).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  // A new passage says what is still to do.
  await page.getByRole("button", { name: "Start a passage" }).click();
  await expect(page).toHaveURL(/\/passages\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "Untitled passage", level: 1 })).toBeVisible();
  const findings = page.getByRole("region", { name: "Findings" });
  await expect(findings).toContainText("Give the passage a short title");
  await expect(findings).toContainText("Write the passage");
  await expect(page.getByText("no checkpoint saved yet")).toBeVisible();

  // Typing is saved by itself, and the findings follow what was written.
  await page.getByLabel("Title").fill("Free fall");
  await page
    .getByRole("group", { name: "Passage text" })
    .getByRole("button", { name: "Add paragraph" })
    .click();
  await page
    .getByLabel("Passage text, block 1: paragraph")
    .fill("A stone is dropped from a tower of height \\(h\\).");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole("heading", { name: "Free fall", level: 1 })).toBeVisible();
  await expect(findings).not.toContainText("Write the passage");
  await expect(page.getByText("No questions under it yet.")).toBeVisible();

  // A question is written under a saved checkpoint, so there is nothing to add until one exists.
  await expect(page.getByText("Save a checkpoint first")).toBeVisible();
  await expect(page.getByRole("button", { name: /^Add question/ })).toHaveCount(0);
  await page.getByRole("button", { name: "Save checkpoint" }).click();
  await expect(
    page.getByText("Checkpoint saved. Questions can now be added under it."),
  ).toBeVisible();
  await expect(page.getByText("newest checkpoint: 1")).toBeVisible();
  await expectNoSeriousA11yViolations(page);

  // The preview shows the passage as a student will read it.
  await page.getByRole("tab", { name: "Preview" }).click();
  const preview = page.locator(".qb-question");
  await expect(preview.getByRole("heading", { name: "Free fall" })).toBeVisible();
  await expect(preview).toContainText("A stone is dropped from a tower of height");
  await expect(preview.locator(".katex")).toHaveCount(1);
  await page.getByRole("tab", { name: "Edit" }).click();

  // Add a question under the checkpoint: it opens in the question editor.
  await page.getByRole("button", { name: "Add question 1" }).click();
  await expect(page).toHaveURL(/\/questions\/[0-9a-f-]{36}$/);
  const heading = page.getByRole("heading", { level: 1 });
  await expect(heading).toContainText("Single correct");
  const code = (await heading.locator("span.font-mono").innerText()).trim();

  // Back on the passage, the question is listed with the checkpoint it was written with.
  await page.goto("/passages");
  await page.getByRole("link", { name: /Free fall/ }).click();
  const under = page.getByRole("region", { name: "Questions under this passage" });
  await expect(under.getByRole("link", { name: new RegExp(code) })).toContainText(
    "Written with checkpoint 1",
  );

  // Editing the passage and saving a new checkpoint leaves the question on the old one.
  await page.getByLabel("Title").fill("Free fall, revised");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await page.getByRole("button", { name: "Save checkpoint" }).click();
  await expect(page.getByText("newest checkpoint: 2")).toBeVisible();
  await expect(under.getByRole("link", { name: new RegExp(code) })).toContainText(
    "On checkpoint 1; newest is 2",
  );

  // The next question is numbered 2 and is written under the newest checkpoint.
  await page.getByRole("button", { name: "Add question 2" }).click();
  await expect(page).toHaveURL(/\/questions\/[0-9a-f-]{36}$/);
  await page.goto("/passages");
  await page.getByRole("link", { name: /Free fall, revised/ }).click();
  await expect(under.getByRole("link")).toHaveCount(2);
  await expect(under.getByRole("link").nth(1)).toContainText("Written with checkpoint 2");
});

test("a passage that someone else changed is not overwritten by a stale screen", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Passages ${unique()}`);
  const page = await context.newPage();
  await page.goto("/passages");
  await page.getByRole("button", { name: "Start a passage" }).click();
  await expect(page).toHaveURL(/\/passages\/[0-9a-f-]{36}$/);
  const id = page.url().split("/").pop()!;
  await expect(page.getByLabel("Title")).toBeEnabled();

  // Another tab (here, the API) saves a newer version of the passage.
  const read = await context.request.get(`/api/v1/passages/${id}`);
  const current = await read.json();
  const other = await context.request.put(`/api/v1/passages/${id}/working-revision`, {
    data: { content: { ...current.content, title: "Written elsewhere" } },
    headers: {
      "If-Match": read.headers()["etag"]!,
      Origin: baseURL!,
      "X-CSRF-Token": await csrfOf(context),
    },
  });
  expect(other.ok()).toBeTruthy();

  // This screen still holds the old version: its save is refused, and Reload shows the new one.
  await page.getByLabel("Title").fill("Typed here");
  await expect(page.getByText("Someone else changed this")).toBeVisible();
  await page.getByRole("button", { name: "Reload" }).click();
  await expect(page.getByLabel("Title")).toHaveValue("Written elsewhere");
});

test("a checkpoint refused because the passage changed elsewhere offers Reload", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Passages ${unique()}`);
  const page = await context.newPage();
  await page.goto("/passages");
  await page.getByRole("button", { name: "Start a passage" }).click();
  await expect(page).toHaveURL(/\/passages\/[0-9a-f-]{36}$/);
  const id = page.url().split("/").pop()!;
  await expect(page.getByLabel("Title")).toBeEnabled();

  const read = await context.request.get(`/api/v1/passages/${id}`);
  const current = await read.json();
  const other = await context.request.put(`/api/v1/passages/${id}/working-revision`, {
    data: { content: { ...current.content, title: "Written elsewhere" } },
    headers: {
      "If-Match": read.headers()["etag"]!,
      Origin: baseURL!,
      "X-CSRF-Token": await csrfOf(context),
    },
  });
  expect(other.ok()).toBeTruthy();

  // Nothing was typed here, so only the checkpoint finds out that this screen is out of date.
  await page.getByRole("button", { name: "Save checkpoint" }).click();
  await expect(page.getByText("Someone else changed this")).toBeVisible();
  await page.getByRole("button", { name: "Reload" }).click();
  await expect(page.getByLabel("Title")).toHaveValue("Written elsewhere");
  await expect(page.getByText("Someone else changed this")).toHaveCount(0);
});

test("the next question number is not guessed from the questions on screen", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Passages ${unique()}`);
  const page = await context.newPage();
  await page.goto("/passages");
  await page.getByRole("button", { name: "Start a passage" }).click();
  await expect(page).toHaveURL(/\/passages\/[0-9a-f-]{36}$/);
  await page.getByLabel("Title").fill("Numbers");
  await page
    .getByRole("group", { name: "Passage text" })
    .getByRole("button", { name: "Add paragraph" })
    .click();
  await page.getByLabel("Passage text, block 1: paragraph").fill("Some text.");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await page.getByRole("button", { name: "Save checkpoint" }).click();
  await expect(page.getByText("newest checkpoint: 1")).toBeVisible();

  // A question that is not shown in the list but exists (here: made through the API as number 5).
  const id = page.url().split("/").pop()!;
  const passage = await (await context.request.get(`/api/v1/passages/${id}`)).json();
  const started = await context.request.post("/api/v1/questions", {
    data: {
      content: {
        schema_version: 1,
        question_type: "SCQ",
        language: "en",
        stem: [],
        context: { passage_revision_id: passage.latest_checkpoint.id, ordinal: 5 },
      },
    },
    headers: { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) },
  });
  expect(started.ok()).toBeTruthy();
  await page.reload();
  await expect(page.getByRole("button", { name: "Add question 6" })).toBeVisible();
});

test("a question shows its passage, and can be moved to the passage's newest checkpoint", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Passages ${unique()}`);
  const page = await context.newPage();
  await page.goto("/passages");
  await page.getByRole("button", { name: "Start a passage" }).click();
  await expect(page).toHaveURL(/\/passages\/[0-9a-f-]{36}$/);
  const passageUrl = page.url();
  await page.getByLabel("Title").fill("Free fall");
  await page
    .getByRole("group", { name: "Passage text" })
    .getByRole("button", { name: "Add paragraph" })
    .click();
  await page
    .getByLabel("Passage text, block 1: paragraph")
    .fill("A stone is dropped from a tower.");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await page.getByRole("button", { name: "Save checkpoint" }).click();
  await expect(page.getByText("newest checkpoint: 1")).toBeVisible();
  await page.getByRole("button", { name: "Add question 1" }).click();
  await expect(page).toHaveURL(/\/questions\/[0-9a-f-]{36}$/);
  const questionUrl = page.url();

  // The passage is shown above the question, as written at the checkpoint it was written with.
  const panel = page.getByRole("region", { name: "Passage" });
  await expect(panel.getByRole("heading", { name: "Passage: Free fall" })).toBeVisible();
  await expect(panel).toContainText("A stone is dropped from a tower.");
  await expect(panel).toContainText("Written with checkpoint 1");
  await expect(panel.getByRole("link", { name: "Open the passage" })).toHaveAttribute(
    "href",
    new URL(passageUrl).pathname,
  );
  await expect(panel.getByRole("status")).toHaveCount(0);
  await expectNoSeriousA11yViolations(page);

  // The student preview has the passage above the question.
  await page.getByRole("tab", { name: "Preview" }).click();
  const preview = page.locator(".qb-question").last();
  await expect(preview.locator(".qb-passage")).toContainText("A stone is dropped from a tower.");
  await expect(preview.locator(".qb-passage h3")).toHaveText("Free fall");
  await page.getByRole("tab", { name: "Edit" }).click();

  // The passage gets a second checkpoint with a new text; the question keeps the old one...
  await page.goto(passageUrl);
  await page.getByLabel("Passage text, block 1: paragraph").fill("A ball is thrown upward.");
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await page.getByRole("button", { name: "Save checkpoint" }).click();
  await expect(page.getByText("newest checkpoint: 2")).toBeVisible();
  await page.goto(questionUrl);
  await expect(panel).toContainText("A stone is dropped from a tower.");
  await expect(panel.getByRole("status")).toContainText("The passage has a newer checkpoint (2).");

  // ...until its author moves it.
  await panel.getByRole("button", { name: "Move to checkpoint 2" }).click();
  await expect(panel).toContainText("A ball is thrown upward.");
  await expect(panel).toContainText("Written with checkpoint 2");
  await expect(panel.getByRole("status")).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await page.reload();
  await expect(page.getByRole("region", { name: "Passage" })).toContainText(
    "Written with checkpoint 2",
  );
  await expect(page.getByRole("region", { name: "Findings" })).not.toContainText(
    "passage is not available",
  );
});
