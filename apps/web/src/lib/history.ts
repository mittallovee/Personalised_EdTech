import type { components } from "@qbank/api-client";

import { RETURN_REASONS, type ReturnReason } from "./workflow";

/**
 * Words for a question's history and for the comparison of two saved texts (M4 design note §8,
 * §11.4). The API decides which entries and texts a person may see, and does the comparing; this
 * file only names things. Everything here is text: nothing from a question is turned into markup.
 */

export type HistoryEntry = components["schemas"]["HistoryEntry"];
export type HistoryKind = components["schemas"]["HistoryKind"];
export type Change = components["schemas"]["ChangeOut"];
export type Segment = components["schemas"]["SegmentOut"];

/** "SOMETHING_NEW" or "display_name" as a sentence: "Something new". */
function humanize(code: string): string {
  const words = code.replaceAll("_", " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const KIND_TEXT: Record<HistoryKind, string> = {
  CREATED: "Started",
  CHECKPOINT: "Saved a checkpoint",
  SUBMIT: "Submitted for review",
  RETURN: "Returned to the author",
  PASS_QC: "Passed QC",
  APPROVE: "Approved",
  PUBLISH: "Published",
  WITHDRAW: "Withdrawn from review",
  START_CORRECTION: "Started a correction",
  ARCHIVED: "Archived",
  RESTORED: "Restored",
};

/** Who did it, from the id the API gives: "you", or a colleague (names are not in the entry). */
export function actorText(actorId: string | null, myId: string): string {
  if (actorId === null) return "someone";
  return actorId === myId ? "you" : "a colleague";
}

/** One entry as a sentence: "Submitted for review by you · version 1". */
export function entryText(entry: HistoryEntry, myId: string): string {
  const version = entry.version_number === null ? "" : ` · version ${entry.version_number}`;
  return `${KIND_TEXT[entry.kind]} by ${actorText(entry.actor_id, myId)}${version}`;
}

/** The reasons of a return, in words. An unknown code is shown as it came, never dropped. */
export function reasonTexts(reasons: readonly string[]): string[] {
  return reasons.map(
    (code) =>
      RETURN_REASONS.find((r) => r.code === (code as ReturnReason))?.label ?? humanize(code),
  );
}

export type TextChoice = { id: string; label: string };

/**
 * The saved texts a person can compare, oldest first: each history entry that names one (a
 * checkpoint, or the step that took a text into review), once. The label says which step it was.
 */
export function comparable(entries: readonly HistoryEntry[]): TextChoice[] {
  const seen = new Set<string>();
  const choices: TextChoice[] = [];
  for (const entry of entries) {
    const id = entry.revision_id;
    if (id === null || seen.has(id)) continue;
    seen.add(id);
    const version = entry.version_number === null ? "" : `Version ${entry.version_number}: `;
    const when = new Date(entry.at).toLocaleString();
    choices.push({ id, label: `${version}${KIND_TEXT[entry.kind]}, ${when}` });
  }
  return choices;
}

/** The two newest texts, older first, or null when there are fewer than two to compare. */
export function defaultPair(choices: readonly TextChoice[]): { from: string; to: string } | null {
  if (choices.length < 2) return null;
  return { from: choices[choices.length - 2]!.id, to: choices[choices.length - 1]!.id };
}

const FIELD_TEXT: Record<string, string> = {
  question_type: "Format",
  stem: "Question",
  assertion: "Assertion",
  reason: "Reason",
  statements: "Statements",
  options: "Options",
  answer: "Answer",
  solution: "Solution",
  matching: "Matching",
  metadata: "Labels",
  passage: "Passage",
};

/** Where in the question a change is: "Question › part 1", "Options › 3 › text". */
export function pathText(path: readonly (string | number)[]): string {
  if (path.length === 0) return "The whole question";
  return path
    .map((part, index) => {
      if (typeof part === "number") return index === 0 ? `part ${part + 1}` : `${part + 1}`;
      return index === 0 ? (FIELD_TEXT[part] ?? humanize(part)) : humanize(part);
    })
    .join(" › ");
}

const MOST_SHOWN = 400;

/** A value from a change as text, shortened. Always text: never markup. */
export function valueText(value: unknown): string {
  if (value === null || value === undefined) return "—";
  const text = typeof value === "string" ? value : JSON.stringify(value);
  if (text === "") return "(empty)";
  return text.length > MOST_SHOWN ? `${text.slice(0, MOST_SHOWN)}…` : text;
}

/** What the change did, in a word. */
export function opText(op: Change["op"]): string {
  return op === "add" ? "Added" : op === "remove" ? "Removed" : "Changed";
}

/** The word-by-word marks of a changed text, when the API gave them (prose only). */
export function segmentsOf(change: Change): readonly Segment[] | null {
  return change.segments && change.segments.length > 0 ? change.segments : null;
}
