import { expect, test, type BrowserContext, type Page } from "@playwright/test";

import {
  activate,
  csrfOf,
  expectNoSeriousA11yViolations,
  inviteByApi,
  readyContent,
  signedInOwner,
  unique,
} from "./helpers";

// M5 journey (design note T55), against a stack whose AI calls are answered by the built-in demo
// provider (AI_DEMO_PROVIDER=true; the master key is set too, so a key can be stored). The Owner
// enters a (fake) key, refreshes the model list, turns a model on and sets what each operation
// uses. Faculty then tags, solves, verifies and translates a question and applies what they are
// shown; a person with no budget is refused; and an Economy verification finishes in the background
// and tells the person. Nothing here calls a real provider.

const FAKE_KEY = "demo-key-" + "a".repeat(16) + "wXyZ"; // plainly fake, and too plain for a scanner
const OPERATIONS = [
  "Tag a question",
  "Solve a question",
  "Verify a question",
  "Translate a question",
];

async function openAiTab(page: Page, id: string) {
  await page.goto(`/questions/${id}`);
  await page.getByRole("tab", { name: "AI" }).click();
  await expect(page.getByRole("group", { name: "AI actions" })).toBeVisible();
}

async function runOperation(page: Page, action: string, run: string) {
  await page
    .getByRole("group", { name: "AI actions" })
    .getByRole("button", { name: action })
    .click();
  await page.getByRole("button", { name: run }).click();
}

async function startQuestion(
  context: BrowserContext,
  baseURL: string,
  content: object,
): Promise<{ id: string; code: string }> {
  const started = await context.request.post("/api/v1/questions", {
    headers: { Origin: baseURL, "X-CSRF-Token": await csrfOf(context) },
    data: { content },
  });
  expect(started.status()).toBe(201);
  return (await started.json()) as { id: string; code: string };
}

test("the Owner sets AI up, faculty use it, a budget stops a run, and an Economy run finishes by itself", async ({
  browser,
  baseURL,
}) => {
  test.setTimeout(420_000); // the Economy step waits for the worker's first look, about a minute

  // The coaching: its Owner, faculty Anita, and faculty Ben who will have no AI budget.
  const { context: ownerContext } = await signedInOwner(browser, baseURL!, `M5 AI ${unique()}`);
  const content = await readyContent(ownerContext, baseURL!);
  const anitaLink = (await inviteByApi(ownerContext, baseURL!, "Anita Rao")).link;
  const benLink = (await inviteByApi(ownerContext, baseURL!, "Ben Das")).link;

  // --- The Owner: key, models, what each operation uses, rate and budget -----------------------
  const owner = await ownerContext.newPage();
  await owner.goto("/admin/ai");
  await expect(owner.getByRole("heading", { name: "AI", level: 1 })).toBeVisible();
  const openai = owner.getByRole("form", { name: "OpenAI key" });
  await openai.getByLabel("Key").fill(FAKE_KEY);
  await openai.getByRole("button", { name: "Save key" }).click();
  await expect(owner.getByText("Stored, ending wXyZ")).toBeVisible();
  // The key is write-only: nothing on the page, in any field, ever shows it again.
  await expect(owner.locator("body")).not.toContainText(FAKE_KEY);
  await expect(openai.getByLabel("Replace the key")).toHaveValue("");

  const models = owner.getByRole("region", { name: "Models" });
  const openaiModels = models
    .locator("div")
    .filter({ has: owner.getByRole("heading", { name: "OpenAI", level: 3 }) })
    .first();
  await openaiModels.getByRole("button", { name: "Refresh the list" }).click();
  await expect(models.getByText("Demo small").first()).toBeVisible({ timeout: 30_000 });
  await models.getByLabel("Offer Demo small").click(); // it flips once the server has saved it
  await expect(models.getByLabel("Offer Demo small")).toBeChecked();
  // Economy is the admin's call, per model: this one offers it at half price.
  const small = models.getByRole("listitem").filter({ hasText: "demo-small" });
  await small.getByRole("button", { name: "Prices and Economy" }).click();
  await small.getByLabel("This model offers Economy (batch) runs").check();
  await small.getByLabel("Batch discount (0.5 means half price)").fill("0.5");
  await small.getByRole("button", { name: "Save" }).click();
  await expect(small.getByText(/Economy runs are on/)).toBeVisible();

  const operations = owner.getByRole("region", { name: "Operations" });
  for (const name of OPERATIONS) {
    const form = operations.getByRole("form", { name });
    await form.getByLabel("First model").selectOption({ label: "Demo small (OpenAI)" });
    await form.getByRole("button", { name: "Save" }).click();
    await expect(
      operations.getByRole("listitem").filter({ hasText: name }).getByRole("status"),
    ).toHaveText("Saved.");
  }
  const rate = owner.getByRole("form", { name: "Rate and budget" });
  await rate.getByLabel("Rupees for one US dollar").fill("100");
  await rate.getByLabel("Default monthly budget per person (rupees)").fill("1000");
  await rate.getByRole("button", { name: "Save" }).click();
  await expect(owner.getByText("Saved. New runs use these numbers.")).toBeVisible();
  await expectNoSeriousA11yViolations(owner);

  // --- Anita: tag, solve, verify and translate one question, applying what she is shown --------
  const anita = await activate(browser, anitaLink, "Anita Rao");
  const first = await startQuestion(anita.context(), baseURL!, content);
  await openAiTab(anita, first.id);
  await expectNoSeriousA11yViolations(anita);

  await runOperation(anita, "Tag", "Run tagging");
  const tagged = anita.getByRole("region", { name: "Tag result" });
  await expect(tagged).toContainText("Applied: difficulty 6");
  await expect(tagged).toContainText("Applied to the question");

  await runOperation(anita, "Solve", "Run solve");
  const solved = anita.getByRole("region", { name: "Solve result" });
  await expect(solved.getByRole("heading", { name: "Suggested" })).toBeVisible();
  await solved.getByRole("button", { name: "Apply the answer and solution" }).click();
  await expect(solved).toContainText("Applied to the question");

  await runOperation(anita, "Verify", "Run verification");
  const verified = anita.getByRole("region", { name: "Verify result" });
  await expect(verified).toContainText("Demo provider: this is a made-up finding");
  await verified.getByRole("button", { name: "Apply the correction" }).click();
  await expect(verified).toContainText("Applied to the question");
  // The correction reached the editor itself: the stem now carries the demo's mark.
  await anita.getByRole("tab", { name: "Edit" }).click();
  await expect(anita.getByLabel("Question, block 1: paragraph")).toHaveValue(/\(checked\)$/);

  await anita.getByRole("tab", { name: "AI" }).click();
  await anita
    .getByRole("group", { name: "AI actions" })
    .getByRole("button", { name: "Translate" })
    .click();
  await anita.getByLabel("Translate into").selectOption("hi");
  await anita.getByRole("button", { name: "Run translation" }).click();
  const translated = anita.getByRole("region", { name: "Translate result" });
  await expect(translated).toContainText("[Hindi]");
  await translated
    .getByRole("button", { name: "Create the translation as a new question" })
    .click();
  // A translation never changes its source: it is a new draft of her own, which she can open.
  const link = translated.getByRole("link", { name: /^question / });
  const newCode = (await link.locator("span").innerText()).trim();
  await link.click();
  // Wait for the new question itself (the old screen is still in the page, hidden, a moment).
  await expect(anita.getByRole("heading", { level: 1 })).toContainText(`Question ${newCode}`);
  await expect(anita.getByRole("heading", { level: 1 })).toContainText("Draft");
  await anita.getByRole("tab", { name: "Edit" }).click();
  await expect(anita.getByLabel("Question, block 1: paragraph")).toHaveValue(/\[Hindi\]$/);

  // The history of the first question lists the four runs, each tied to what it did.
  await openAiTab(anita, first.id);
  const history = anita.getByRole("region", { name: "AI history" });
  for (const name of ["Tag", "Solve", "Verify", "Translate"]) {
    await expect(history.getByRole("button", { name: new RegExp(`^${name}`) })).toBeVisible();
  }

  // --- Ben has no AI budget: his run is refused with the reason, and nothing is spent ----------
  const ben = await activate(browser, benLink, "Ben Das");
  const benId = ((await (await ben.context().request.get("/api/v1/me")).json()) as { id: string })
    .id;
  const limit = await ownerContext.request.put(`/api/v1/ai/budgets/${benId}`, {
    headers: {
      Origin: baseURL!,
      "X-CSRF-Token": await csrfOf(ownerContext),
      "If-Match": '"rev-0"',
    },
    data: { monthly_inr: "0" },
  });
  expect(limit.ok()).toBe(true);
  const bens = await startQuestion(ben.context(), baseURL!, content);
  await openAiTab(ben, bens.id);
  await runOperation(ben, "Solve", "Run solve");
  await expect(
    ben.getByRole("alert").filter({ hasText: "This would pass your monthly AI budget." }),
  ).toBeVisible();
  await ben.getByRole("link", { name: "AI usage" }).click();
  await expect(ben.getByRole("region", { name: "Your usage" })).toContainText("used up");

  // --- Economy: Anita starts a verification that finishes later, keeps working, and is told -----
  await openAiTab(anita, first.id);
  await anita
    .getByRole("group", { name: "AI actions" })
    .getByRole("button", { name: "Verify" })
    .click();
  await anita.getByLabel(/^Economy/).check();
  await anita.getByRole("button", { name: "Run verification" }).click();
  await expect(anita.getByText("This is an Economy run")).toBeVisible();
  // The worker looks about a minute later; the demo provider has the answer ready by then.
  const entry = history.getByRole("button", { name: /^Verify/ }).first();
  await expect(entry).toContainText("Done", { timeout: 240_000 });
  await anita.goto("/notifications");
  const notices = anita.getByRole("list", { name: "Your notifications" });
  await expect(notices).toContainText("Your Economy verification has finished");
  await expect(notices.getByRole("link", { name: /Economy verification/ })).toBeVisible();
});
