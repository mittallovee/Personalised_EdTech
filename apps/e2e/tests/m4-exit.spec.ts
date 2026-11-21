import { expect, test, type Page } from "@playwright/test";

import {
  activate,
  csrfOf,
  expectNoSeriousA11yViolations,
  inviteByApi,
  readyContent,
  signedInOwner,
  unique,
} from "./helpers";

// M4 exit journey (design note T42), with real people in real browsers: faculty writes and
// submits; a QC person returns it with reasons; faculty fixes and resubmits; QC, approval and
// publish; the bank finds it by words (with a typo) and by code; a correction becomes version 2
// and the published text stays; two tabs race on one step. Each person has a browser of their own.

const SAVED = /^(Saved \d|All changes saved)/;
const OLD_STEM = "A heavy pendulum swings slowly in the lab.";
const FIXED_STEM = "A heavy pendulum swings slowly in the lab, twice.";

async function step(page: Page, name: string) {
  await page.getByRole("group", { name: "Review steps" }).getByRole("button", { name }).click();
}

test("a question goes from faculty through QC to the bank, and a correction leaves the published text alone", async ({
  browser,
  baseURL,
}) => {
  // The coaching: an Owner who makes the labels, faculty Anita, and Kiran who holds the review
  // grants but is not an admin.
  const { context: owner } = await signedInOwner(browser, baseURL!, `M4 exit ${unique()}`);
  const content = await readyContent(owner, baseURL!);
  const anitaLink = (await inviteByApi(owner, baseURL!, "Anita Rao")).link;
  const kiranInvite = await inviteByApi(owner, baseURL!, "Kiran Das");
  const granted = await owner.request.put(`/api/v1/members/${kiranInvite.membershipId}/grants`, {
    headers: {
      Origin: baseURL!,
      "X-CSRF-Token": await csrfOf(owner),
      "If-Match": `"rev-${kiranInvite.revision}"`,
    },
    data: { grants: ["QC", "APPROVE", "PUBLISH"] },
  });
  expect(granted.ok()).toBe(true);
  const anita = await activate(browser, anitaLink, "Anita Rao");
  const kiran = await activate(browser, kiranInvite.link, "Kiran Das");

  // Anita starts a question (the editor itself is covered by the M3 journeys) and submits it.
  const started = await anita.context().request.post("/api/v1/questions", {
    headers: { Origin: baseURL!, "X-CSRF-Token": await csrfOf(anita.context()) },
    data: { content: { ...content, stem: [{ kind: "paragraph", text: OLD_STEM }] } },
  });
  expect(started.status()).toBe(201);
  const { id, code } = (await started.json()) as { id: string; code: string };
  await anita.goto(`/questions/${id}`);
  const heading = anita.getByRole("heading", { level: 1 });
  await expect(heading).toContainText("Draft");
  await step(anita, "Submit for review");
  await expect(heading).toContainText("In review");

  // Kiran finds it in the queue and returns it, with a reason and a note.
  await kiran.goto("/review");
  await expect(kiran.getByRole("tab", { name: "Waiting for QC (1)" })).toBeVisible();
  await expectNoSeriousA11yViolations(kiran);
  await kiran.getByRole("link", { name: code }).click();
  const kiranHeading = kiran.getByRole("heading", { level: 1 });
  await expect(kiranHeading).toContainText("In review");
  await step(kiran, "Return to the author");
  const form = kiran.getByRole("form", { name: "Return to the author" });
  await form.getByLabel("The question text is unclear, incomplete or ambiguous").check();
  await form.getByLabel("What should the author fix?").fill("Say how many swings are timed.");
  await form.getByRole("button", { name: "Return to the author" }).click();
  await expect(kiranHeading).toContainText("Returned to the author");

  // Anita is told, reads why, fixes the text and submits again.
  await anita.goto("/");
  const bell = anita.getByRole("link", { name: "Notifications 1 unread" });
  await bell.click();
  const list = anita.getByRole("list", { name: "Your notifications" });
  await expect(list).toContainText("Say how many swings are timed.");
  await list.getByRole("link", { name: `Question ${code} was returned to you` }).click();
  await expect(heading).toContainText("Returned to the author");
  await anita.getByLabel("Question, block 1: paragraph").fill(FIXED_STEM);
  await expect(anita.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });
  await step(anita, "Submit for review");
  await expect(heading).toContainText("In review");

  // Two tabs of Kiran's race on one step: the second is refused and offers to reload.
  const tab = await kiran.context().newPage();
  await kiran.goto(`/questions/${id}`);
  await tab.goto(`/questions/${id}`);
  await expect(tab.getByRole("heading", { level: 1 })).toContainText("In review");
  await step(kiran, "Pass QC");
  await expect(kiranHeading).toContainText("QC passed");
  await step(tab, "Pass QC");
  const alert = tab.getByRole("alert");
  await expect(alert).toBeVisible();
  await alert.getByRole("button", { name: "Reload" }).click();
  await expect(tab.getByRole("heading", { level: 1 })).toContainText("QC passed");
  await tab.close();

  // Approval and publishing (which asks first).
  await step(kiran, "Approve");
  await expect(kiranHeading).toContainText("Approved");
  await step(kiran, "Publish");
  await kiran
    .getByRole("region", { name: "Publish this question?" })
    .getByRole("button", { name: "Publish" })
    .click();
  await expect(kiranHeading).toContainText("Published");

  // The bank finds it by words, also with a typo, and by its code (as Kiran, not its author).
  await kiran.goto("/questions");
  const bank = kiran.getByRole("region", { name: "Question bank" });
  await bank.getByLabel("Search the stem, options and solution").fill("pendulm");
  await expect(bank.getByRole("link", { name: code })).toBeVisible();
  await expect(bank).toContainText(FIXED_STEM);
  const box = kiran.getByRole("form", { name: "Open by code" });
  await box.getByLabel("Code").fill(`${code.slice(0, 4)}-${code.slice(4)}`.toLowerCase());
  await box.getByRole("button", { name: "Open" }).click();
  await expect(kiranHeading).toContainText(code);
  await expect(kiranHeading).toContainText("Published");

  // Anita starts a correction: version 2, a draft; she changes the text in it.
  await anita.goto(`/questions/${id}`);
  await expect(heading).toContainText("Published");
  await step(anita, "Start a correction");
  await anita
    .getByRole("region", { name: "Start a correction?" })
    .getByRole("button", { name: "Start the correction" })
    .click();
  await expect(heading).toContainText("Draft");
  await expect(anita.getByRole("status").filter({ hasText: "version 2" })).toBeVisible();
  await anita.getByLabel("Question, block 1: paragraph").fill(`${FIXED_STEM} Zephyr.`);
  await expect(anita.getByRole("status").filter({ hasText: SAVED })).toBeVisible({
    timeout: 15_000,
  });

  // Kiran still sees the published text and nothing of the correction; Anita's history says so.
  await kiran.goto("/questions");
  const kiranBank = kiran.getByRole("region", { name: "Question bank" });
  await expect(kiranBank.getByRole("link", { name: code })).toBeVisible();
  await expect(kiranBank).toContainText(FIXED_STEM);
  await expect(kiranBank).not.toContainText("Zephyr");
  await kiranBank.getByLabel("Search the stem, options and solution").fill("zephyr");
  await expect(kiranBank.getByRole("status")).toHaveText("0 questions match");

  await anita.getByRole("tab", { name: "History" }).click();
  await expect(anita.getByRole("region", { name: "History" })).toContainText(
    "Started a correction by you · version 2",
  );
  await expectNoSeriousA11yViolations(anita);
});
