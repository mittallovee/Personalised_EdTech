import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test, type BrowserContext } from "@playwright/test";

import { csrfOf, expectNoSeriousA11yViolations, signedInOwner, unique } from "./helpers";

// M3 exit check (design note T32): every one of the nine formats, through the real stack and a real
// browser. The spec-v1 fixtures are the same ones the backend tests use (T23): the incomplete draft
// saves and says what is missing, the content-ready version has nothing left to fix and previews as
// a student will see it, a wrong answer is named as a mistake, and a checkpoint keeps the question.

type Content = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
type Fixture = { draft: Content; ready: Content; invalid_answer: { answer: unknown } };

const FIXTURES = JSON.parse(
  readFileSync(
    path.resolve(__dirname, "../../../services/api/tests/fixtures/spec_v1_questions.json"),
    "utf-8",
  ),
) as Record<string, Fixture>;

// Which fixtures, and how the editor names them. A passage-based question is one of the eight
// formats with a `context` (it sits under a checkpoint of a passage).
const KINDS: { kind: string; label: RegExp; options: boolean }[] = [
  { kind: "SCQ", label: /Single correct/, options: true },
  { kind: "MULTI_CORRECT", label: /Multiple correct/, options: true },
  { kind: "INTEGER", label: /Integer/, options: false },
  { kind: "SINGLE_DIGIT", label: /digit/i, options: false },
  { kind: "NUMERICAL", label: /Numerical/, options: false },
  { kind: "MATCHING", label: /Matching/, options: true },
  { kind: "ASSERTION_REASON", label: /Assertion/, options: true },
  { kind: "MULTIPLE_STATEMENT", label: /Multiple statement/, options: true },
  { kind: "PASSAGE_CHILD", label: /.+/, options: true },
];

/** A syllabus branch for the labels, and (for the passage child) a passage with one checkpoint. */
async function prepare(context: BrowserContext, origin: string, withPassage: boolean) {
  const headers = { Origin: origin, "X-CSRF-Token": await csrfOf(context) };
  const post = async (url: string, data: object) => {
    const res = await context.request.post(url, { headers, data });
    expect(res.status(), url).toBe(201);
    return res;
  };
  const id = async (url: string, data: object) =>
    ((await (await post(url, data)).json()) as { id: string }).id;
  const node = (kind: string, parent_id: string | null, name: string) =>
    id("/api/v1/taxonomy/nodes", { kind, parent_id, name, sort_order: 1 });
  const klass = await node("CLASS", null, "Class 11");
  const subject = await node("SUBJECT", klass, "Physics");
  const chapter = await node("CHAPTER", subject, "Kinematics");
  const topic = await node("TOPIC", chapter, "Motion in a line");
  const concept = await id("/api/v1/taxonomy/concepts", {
    subject_id: subject,
    name: "Velocity",
    aliases: [],
  });
  let checkpointId: string | null = null;
  if (withPassage) {
    const passage = (await (
      await post("/api/v1/passages", {
        content: {
          schema_version: 1,
          title: "Free fall",
          body: [{ kind: "paragraph", text: "A stone is dropped from a tower." }],
        },
      })
    ).json()) as { id: string; revision: number };
    const after = (await (
      await context.request.post(`/api/v1/passages/${passage.id}/checkpoints`, {
        headers: { ...headers, "If-Match": `"rev-${passage.revision}"` },
      })
    ).json()) as { latest_checkpoint: { id: string } };
    checkpointId = after.latest_checkpoint.id;
  }
  const labelled = (content: Content): Content => {
    const copy = structuredClone(content);
    if (copy.metadata) {
      Object.assign(copy.metadata, {
        class_id: klass,
        subject_id: subject,
        chapter_id: chapter,
        topic_id: topic,
        primary_concept_id: concept,
      });
    }
    if (copy.context && checkpointId) copy.context.passage_revision_id = checkpointId;
    return copy;
  };
  return { headers, labelled };
}

for (const { kind, label, options } of KINDS) {
  test(`${kind}: the draft saves, the finished question has nothing left to fix, a wrong answer is named, a checkpoint keeps it`, async ({
    browser,
    baseURL,
  }) => {
    const fixture = FIXTURES[kind]!;
    const { context } = await signedInOwner(browser, baseURL!, `Exit ${kind} ${unique()}`);
    const { headers, labelled } = await prepare(context, baseURL!, kind === "PASSAGE_CHILD");

    // 1. The incomplete draft is saved, and the editor says what is still to do.
    const started = await context.request.post("/api/v1/questions", {
      headers,
      data: { content: labelled(fixture.draft) },
    });
    expect(started.status()).toBe(201);
    const question = (await started.json()) as { id: string; code: string; revision: number };
    const page = await context.newPage();
    await page.goto(`/questions/${question.id}`);
    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toContainText(question.code);
    await expect(heading).toContainText(label);
    const findings = page.getByRole("region", { name: "Findings" });
    await expect(findings).toContainText("Still to do");

    // 2. The content-ready question has nothing left to fix, and previews as a student sees it.
    let revision = question.revision;
    const save = async (content: Content) => {
      const response = await context.request.put(
        `/api/v1/questions/${question.id}/working-revision`,
        {
          headers: { ...headers, "If-Match": `"rev-${revision}"` },
          data: { content },
        },
      );
      expect(response.status()).toBe(200);
      revision = ((await response.json()) as { revision: number }).revision;
    };
    await save(labelled(fixture.ready));
    await page.reload();
    await expect(findings).toContainText("Nothing left to fix.");
    if (kind === "PASSAGE_CHILD") {
      await expect(page.getByRole("region", { name: "Passage" })).toContainText(
        "A stone is dropped from a tower.",
      );
    }
    await expectNoSeriousA11yViolations(page);

    await page.getByRole("tab", { name: "Preview" }).click();
    const preview = page.locator(".qb-question").last();
    await expect(preview).not.toBeEmpty();
    // Nothing about the answer shows until the author asks for it.
    await expect(preview.locator('[data-correct="true"]')).toHaveCount(0);
    await page.getByLabel("Show the answer and solution").check();
    if (options) {
      await expect(preview.locator('[data-correct="true"]').first()).toBeVisible();
    } else {
      await expect(preview.locator(".qb-answer-box")).toBeVisible();
    }
    await page.getByRole("tab", { name: "Edit" }).click();

    // 3. A wrong answer is named as a mistake; putting the right one back clears it.
    await save({ ...labelled(fixture.ready), answer: fixture.invalid_answer.answer });
    await page.reload();
    await expect(findings.getByRole("heading", { name: /^Mistakes/ })).toBeVisible();
    await expect(findings).not.toContainText("Nothing left to fix.");
    await save(labelled(fixture.ready));
    await page.reload();
    await expect(findings).toContainText("Nothing left to fix.");

    // 4. A checkpoint keeps the question: it is still there, unchanged, after coming back.
    await page.getByRole("button", { name: "Save checkpoint" }).click();
    await expect(page.getByText("Checkpoint saved. You can keep editing.")).toBeVisible();
    await page.goto("/questions");
    await expect(page.getByRole("link", { name: new RegExp(question.code) })).toBeVisible();
    await page.getByRole("link", { name: new RegExp(question.code) }).click();
    await expect(findings).toContainText("Nothing left to fix.");
    const history = (await (
      await context.request.get(`/api/v1/questions/${question.id}/revisions`)
    ).json()) as { data: { working: boolean }[] };
    expect(history.data.filter((r) => !r.working)).toHaveLength(1);
  });
}
