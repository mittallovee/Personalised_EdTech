import { expect, test, type Page } from "@playwright/test";

import {
  activate,
  expectNoSeriousA11yViolations,
  inviteByApi,
  signedInOwner,
  unique,
} from "./helpers";

// M6 journey (design note T64), against a stack with the sandboxed document worker running and the
// demo AI provider answering (AI_DEMO_PROVIDER=true). The Owner chooses the reading model; faculty
// uploads a small PDF, sees it turned into pages, has the questions read, reviews them side by side
// with the keyboard, creates one as a draft question, rejects another with a reason, and opens the
// original. Nothing here calls a real provider, and no real coaching content is used.

const FAKE_KEY = "demo-key-" + "b".repeat(16) + "wXyZ"; // plainly fake

/** A two-page PDF made by hand (pdfium reads it): each page carries one line of text. */
function samplePdf(lines: string[]): Buffer {
  const objects: string[] = [];
  const add = (body: string) => objects.push(body) && objects.length;
  add("<< /Type /Catalog /Pages 2 0 R >>");
  add(
    `<< /Type /Pages /Kids [${lines.map((_, i) => `${4 + 2 * i} 0 R`).join(" ")}] /Count ${lines.length} >>`,
  );
  add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
  for (const line of lines) {
    const stream = `BT /F1 18 Tf 20 100 Td (${line}) Tj ET`;
    add(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 3 0 R >> >> /Contents ${objects.length + 2} 0 R >>`,
    );
    add(`<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`);
  }
  let out = "%PDF-1.4\n";
  const offsets: number[] = [];
  objects.forEach((body, i) => {
    offsets.push(out.length);
    out += `${i + 1} 0 obj\n${body}\nendobj\n`;
  });
  const start = out.length;
  out += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets) out += `${String(offset).padStart(10, "0")} 00000 n \n`;
  out += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${start}\n%%EOF\n`;
  return Buffer.from(out, "latin1");
}

async function chooseReadingModel(page: Page) {
  await page.goto("/admin/ai");
  const openai = page.getByRole("form", { name: "OpenAI key" });
  await openai.getByLabel("Key").fill(FAKE_KEY);
  await openai.getByRole("button", { name: "Save key" }).click();
  await expect(page.getByText("Stored, ending wXyZ")).toBeVisible();
  const models = page.getByRole("region", { name: "Models" });
  await models
    .locator("div")
    .filter({ has: page.getByRole("heading", { name: "OpenAI", level: 3 }) })
    .first()
    .getByRole("button", { name: "Refresh the list" })
    .click();
  await expect(models.getByText("Demo large").first()).toBeVisible({ timeout: 30_000 });
  await models.getByLabel("Offer Demo large").click(); // it flips once the server has saved it
  await expect(models.getByLabel("Offer Demo large")).toBeChecked();
  const reading = page.getByRole("form", { name: "Reading documents" });
  await reading.getByLabel("Model").selectOption({ label: "Demo large (OPENAI)" });
  await reading.getByRole("button", { name: "Save" }).click();
  await expect(page.getByText("Documents are read with this model from now on.")).toBeVisible();
}

test("a paper is uploaded, read into questions, reviewed with the keyboard and made into a draft", async ({
  browser,
  baseURL,
}) => {
  test.setTimeout(240_000);
  const { context: ownerContext } = await signedInOwner(browser, baseURL!, `M6 ${unique()}`);
  const anitaLink = (await inviteByApi(ownerContext, baseURL!, "Anita Rao")).link;
  const owner = await ownerContext.newPage();
  await chooseReadingModel(owner);

  // --- Anita uploads a paper and watches it become pages -----------------------------------
  const anita = await activate(browser, anitaLink, "Anita Rao");
  await anita.goto("/uploads");
  await expect(anita.getByRole("heading", { name: "Uploads", level: 1 })).toBeVisible();
  await expectNoSeriousA11yViolations(anita);
  await anita.getByLabel("Choose files to upload").setInputFiles({
    name: "unit-test-paper.pdf",
    mimeType: "application/pdf",
    buffer: samplePdf(["What is 2 plus 3?", "A ball falls for two seconds."]),
  });
  await expect(anita.getByRole("list", { name: "Files being sent" })).toContainText("sent");
  const documents = anita.getByRole("region", { name: "Your documents" });
  await expect(documents).toContainText("unit-test-paper.pdf");
  await expect(documents).toContainText("Pages ready", { timeout: 90_000 }); // the sandbox worker
  await expect(documents).toContainText("2 pages");

  // A file that is not a document is refused with a plain sentence, and nothing is stored.
  await anita.getByLabel("Choose files to upload").setInputFiles({
    name: "notes.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("MZ this is a program, not a pdf"),
  });
  await expect(anita.getByRole("list", { name: "Files being sent" })).toContainText(
    "This is not a PDF, Word",
  );
  await expect(documents).not.toContainText("notes.pdf");

  // --- Open it: pages, then read the questions ---------------------------------------------
  await documents.getByRole("link", { name: "unit-test-paper.pdf" }).click();
  await expect(anita.getByRole("region", { name: "Pages" }).getByRole("img")).toHaveCount(2);
  await expectNoSeriousA11yViolations(anita);
  await anita.getByRole("button", { name: "Read the questions" }).click();
  const found = anita.getByRole("region", { name: "Questions found" });
  await expect(found).toContainText("2 found", { timeout: 120_000 });
  await expect(found).toContainText("2 waiting");
  const original = await anita.request.get(
    (await anita.getByRole("link", { name: "Download the original" }).getAttribute("href"))!,
  );
  expect(original.headers()["content-type"]).toBe("application/pdf");
  expect(original.headers()["content-disposition"]).toContain("attachment");

  // --- Review: the page, the question, the keyboard ----------------------------------------
  await found.getByRole("link", { name: "Review the questions" }).click();
  await expect(anita.getByRole("heading", { name: /^Review:/ })).toBeVisible();
  await expect(anita.getByRole("img", { name: "Page 1 as printed" })).toBeVisible();
  const stem = anita.getByLabel("Question, block 1: paragraph");
  await expect(stem).toHaveValue("What is 2 plus 3?");
  await expectNoSeriousA11yViolations(anita);
  await anita.keyboard.press("j"); // next
  await expect(anita.getByRole("img", { name: "Page 2 as printed" })).toBeVisible();
  await expect(stem).toHaveValue("A ball falls for two seconds.");
  await anita.keyboard.press("k"); // back
  await expect(stem).toHaveValue("What is 2 plus 3?");

  // Typing a letter in a field is typing, never a shortcut.
  await stem.click();
  await stem.press("End");
  await stem.pressSequentially(" ra");
  await expect(stem).toHaveValue("What is 2 plus 3? ra");
  await expect(anita.getByRole("status").filter({ hasText: "Made into a question" })).toHaveCount(
    0,
  );
  await stem.fill("What is 2 plus 3?");

  // Create the first question (button; the shortcut is `a`). It is a draft of Anita's.
  await anita.getByRole("button", { name: "Create question" }).click();
  await expect(anita.getByText("Created as a draft question")).toBeVisible();
  await expect(anita.getByRole("img", { name: "Page 2 as printed" })).toBeVisible(); // moved on
  await anita.getByRole("button", { name: /p1\.1 What is 2 plus 3\?/ }).click();
  const made = anita.getByRole("link", { name: "Open the question made from this" });
  await expect(made).toBeVisible();

  // Reject the second with a reason, using the keyboard to get to the reason box.
  await anita.getByRole("button", { name: /p2\.1/ }).click();
  await anita.keyboard.press("r");
  await expect(anita.getByLabel("Reason to reject")).toBeFocused();
  await anita.keyboard.type("Not a question for this bank");
  await anita.getByRole("button", { name: "Reject" }).click();
  await expect(anita.getByRole("status").filter({ hasText: "Rejected." })).toBeVisible();

  // The document page says where things stand, and the new question is a draft with the text.
  await anita.goto(anita.url().replace("/review", ""));
  await expect(anita.getByRole("region", { name: "Questions found" })).toContainText(
    "1 made into questions",
  );
  await anita
    .getByRole("region", { name: "Questions found" })
    .getByText(/rejected/)
    .waitFor();
  await anita.goto(anita.url().replace(/\/uploads\/.*/, "/notifications"));
  await expect(anita.getByRole("list", { name: "Your notifications" })).toContainText(
    "Your document has been read: 2 questions found",
  );
  await anita.goBack();
});
