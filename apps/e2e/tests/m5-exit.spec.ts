import { expect, test } from "@playwright/test";

import {
  activate,
  csrfOf,
  expectNoSeriousA11yViolations,
  inviteByApi,
  readyContent,
  signedInOwner,
  unique,
} from "./helpers";

// M5 exit journey (design note T55): an admin sets up the AI (a key, the model list, a model turned
// on); faculty tag a question, translate it into a new linked draft, verify it, and are refused when
// they would pass their monthly budget. The stack runs with AI_DEMO_PROVIDER=true, so a built-in
// stand-in answers instead of a real provider: no key, network or bill. Economy (batch) runs need a
// batch service that a separate worker process can reach, so they are proved by the backend tests
// (T50 to T52), which run a real worker against a fake batch service.

const FAKE_KEY = "fake-openai-" + "a".repeat(16) + "wXyZ"; // plain, so no secret scanner takes it for a key

test("an admin sets up the AI and faculty tag, translate and verify, within a budget", async ({
  browser,
  baseURL,
}) => {
  const { context: owner } = await signedInOwner(browser, baseURL!, `M5 exit ${unique()}`);
  const content = await readyContent(owner, baseURL!);
  const ownerHeaders = async () => ({ Origin: baseURL!, "X-CSRF-Token": await csrfOf(owner) });
  const anitaInvite = await inviteByApi(owner, baseURL!, "Anita Rao");

  // The admin stores a key. It is sealed on the server: the box empties and only the end shows.
  const admin = await owner.newPage();
  await admin.goto("/admin/ai");
  await expect(admin.getByRole("heading", { level: 1, name: "AI" })).toBeVisible();
  const keyForm = admin.getByRole("form", { name: "OpenAI key" });
  await keyForm.getByLabel("Key").fill(FAKE_KEY);
  await keyForm.getByRole("button", { name: "Save key" }).click();
  await expect(admin.getByText("The OpenAI key is saved.")).toBeVisible();
  await expect(keyForm.getByLabel("Replace the key")).toHaveValue("");
  await expect(admin.getByText("Stored, ending wXyZ")).toBeVisible();
  await expect(admin.getByText(FAKE_KEY)).toHaveCount(0);

  // The model list comes from the provider through a background job: refresh and wait for it.
  await admin.locator("button:not([disabled])", { hasText: "Refresh the list" }).first().click();
  const offer = admin.getByLabel("Offer Fake small");
  await expect(offer).toBeVisible({ timeout: 45_000 });
  await offer.check();
  await expect(offer).toBeChecked({ timeout: 15_000 });
  await expectNoSeriousA11yViolations(admin);

  // The rate, the budget and the model each operation uses (set through the API; the screens for
  // these are covered by the checks of the page itself).
  const models = (await (await owner.request.get("/api/v1/ai/models")).json()) as {
    data: { id: string; model_id: string }[];
  };
  const model = models.data.find((item) => item.model_id === "fake-small");
  expect(model).toBeTruthy();
  for (const operation of ["TAG", "TRANSLATE", "SOLVE", "VERIFY"]) {
    const saved = await owner.request.put(`/api/v1/ai/operations/${operation}`, {
      headers: { ...(await ownerHeaders()), "If-Match": '"rev-0"' },
      data: { default_model_id: model!.id, mode: "NOW", fallback_model_ids: [] },
    });
    expect(saved.status(), operation).toBe(200);
  }
  const settings = await owner.request.put("/api/v1/ai/settings", {
    headers: { ...(await ownerHeaders()), "If-Match": '"rev-0"' },
    data: { usd_to_inr: "83", default_budget_inr: "1000" },
  });
  expect(settings.status()).toBe(200);

  // Anita starts a question and opens its AI tab.
  const anita = await activate(browser, anitaInvite.link, "Anita Rao");
  const started = await anita.context().request.post("/api/v1/questions", {
    headers: { Origin: baseURL!, "X-CSRF-Token": await csrfOf(anita.context()) },
    data: { content },
  });
  expect(started.status()).toBe(201);
  const question = (await started.json()) as { id: string; code: string };
  const open = async () => {
    await anita.goto(`/questions/${question.id}`);
    await anita.getByRole("tab", { name: "AI" }).click();
    return anita.getByRole("form", { name: "Ask the AI" });
  };
  const ask = async (operation: string) => {
    const form = await open();
    await form.getByLabel("What should the AI do?").selectOption({ label: operation });
    return form;
  };

  // Tag: the labels are filled in from her coaching's own syllabus.
  let form = await ask("Tag a question");
  await form.getByRole("button", { name: "Run" }).click();
  const history = anita.getByRole("region", { name: "AI history" });
  await expect(history.getByText("Applied to the question")).toBeVisible({ timeout: 20_000 });
  await expect(history.getByText("Difficulty:")).toBeVisible();
  await expectNoSeriousA11yViolations(anita);

  // Translate: a suggestion first; applying makes a new draft linked to this question.
  form = await ask("Translate a question");
  await form.getByLabel("Translate into").selectOption({ label: "Hindi" });
  await form.getByRole("button", { name: "Run" }).click();
  await expect(history.getByText("The translation (hi)")).toBeVisible({ timeout: 20_000 });
  await history.getByRole("button", { name: "Create the translation" }).first().click();
  const link = history.getByRole("link", { name: /^Open the translation/ }).first();
  await expect(link).toBeVisible();
  await link.click();
  await expect(anita.getByRole("heading", { level: 1 })).toContainText("Draft");

  // Verify: findings are shown as text; nothing changes.
  form = await ask("Verify a question");
  await form.getByRole("button", { name: "Run" }).click();
  await expect(history.getByText("Demo check: nothing serious found.")).toBeVisible({
    timeout: 20_000,
  });

  // Over budget: the admin lowers the budget below what one run costs; the next run is refused
  // before anything is sent, and the reason is shown in words.
  const lowered = await owner.request.put("/api/v1/ai/settings", {
    headers: { ...(await ownerHeaders()), "If-Match": '"rev-1"' },
    data: { usd_to_inr: "83", default_budget_inr: "0.01" },
  });
  expect(lowered.status()).toBe(200);
  form = await ask("Solve a question");
  await form.getByRole("button", { name: "Run" }).click();
  await expect(form.getByRole("alert")).toContainText("pass your monthly AI budget");

  // The screens that explain it: her use this month, and the library of prompts.
  await anita.goto("/usage");
  await expect(anita.getByRole("heading", { name: "Your use this month" })).toBeVisible();
  await expectNoSeriousA11yViolations(anita);
  await anita.goto("/prompts");
  await expect(anita.getByRole("heading", { level: 1, name: "Prompt library" })).toBeVisible();
  await expect(anita.getByRole("region", { name: "Tag a question" })).toContainText(
    "the platform default",
  );
  await expectNoSeriousA11yViolations(anita);
});
