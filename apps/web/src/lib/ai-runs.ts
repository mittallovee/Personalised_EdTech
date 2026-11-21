import type { components } from "@qbank/api-client";

export type Run = components["schemas"]["RunOut"];

const WAITING = new Set(["RUNNING", "QUEUED", "SUBMITTING", "SUBMITTED"]);

/**
 * Whether the run is still going (a Now run in progress, or an Economy run waiting for its batch).
 * `phase` is extensible: a value this page does not know counts as still going, as the API says.
 */
export function isWaiting(run: Pick<Run, "phase">): boolean {
  const known = ["SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED", "SUBMISSION_UNKNOWN"].includes(
    run.phase,
  );
  return WAITING.has(run.phase) || !known;
}

export const PHASE_TEXT: Record<string, string> = {
  RUNNING: "Running",
  QUEUED: "Waiting to be sent (Economy)",
  SUBMITTING: "Being sent (Economy)",
  SUBMITTED: "With the provider (Economy)",
  SUCCEEDED: "Done",
  FAILED: "Failed",
  CANCELLED: "Cancelled",
  EXPIRED: "Expired",
  SUBMISSION_UNKNOWN: "Not confirmed by the provider",
};

export function phaseText(phase: string): string {
  return PHASE_TEXT[phase] ?? "In progress";
}

export const APPLY_TEXT: Record<Run["apply_status"], string> = {
  NOT_APPLIED: "Nothing was changed",
  APPLIED: "Applied to the question",
  OUT_OF_DATE: "Not applied: the question changed while this ran",
  NEEDS_REVIEW: "Not applied: you can no longer change this question",
};

/** What went wrong, in a sentence, from the code the run keeps. Never the provider's own words. */
export function errorText(code: string | null): string | null {
  if (code === null) return null;
  const known: Record<string, string> = {
    AI_OUTPUT_INVALID:
      "The model's answer could not be used, so nothing was changed. The cost of the call is still counted.",
    AI_PROVIDER_AUTH: "The provider refused the coaching's key. An admin must check it.",
    AI_PROVIDER_RATE_LIMITED: "The provider asked us to slow down. Try again in a minute.",
    AI_PROVIDER_TIMEOUT: "The provider did not answer in time.",
    AI_PROVIDER_UNAVAILABLE: "The provider could not be reached.",
    AI_PROVIDER_BAD_REQUEST: "The provider refused the request.",
    AI_PROVIDER_BAD_OUTPUT: "The provider's answer could not be read.",
    AI_PROVIDER_TOO_LARGE: "The provider's answer was too large to read.",
    AI_PROVIDER_BATCH_FAILED: "The provider could not finish the batch. You were not charged.",
    AI_PROVIDER_BATCH_EXPIRED: "The provider did not finish in time. You were not charged.",
    AI_RUN_CANCELLED: "Cancelled. You were not charged.",
    AI_RUN_ABANDONED: "The server stopped while this was running. You were not charged.",
    AI_KEY_UNREADABLE: "The coaching's key could not be opened. An admin must enter it again.",
    AI_SUBMISSION_UNKNOWN:
      "The provider never confirmed this run. An admin has settled the cost by hand.",
    AI_RESULT_UNCHECKABLE:
      "The answer could not be checked any more because the lists it refers to changed.",
  };
  return known[code] ?? "The run did not finish.";
}

/** The names of the top-level parts of a question that differ between two contents. */
export function changedParts(
  before: Record<string, unknown>,
  after: Record<string, unknown>,
): string[] {
  const keys = new Set([...Object.keys(before), ...Object.keys(after)]);
  const names: Record<string, string> = {
    stem: "the question",
    options: "the options",
    answer: "the answer",
    solution: "the solution",
    assertion: "the assertion",
    reason: "the reason",
    statements: "the statements",
    left: "the left column",
    right: "the right column",
    language: "the language",
  };
  return [...keys]
    .filter(
      (key) => key !== "metadata" && JSON.stringify(before[key]) !== JSON.stringify(after[key]),
    )
    .map((key) => names[key] ?? key);
}

/** A key as a short sentence: "option B", "options A, C", "7", "9.79 to 9.81", "exactly 9.80". */
export function answerText(answer: unknown): string {
  if (typeof answer !== "object" || answer === null) return "none";
  const a = answer as Record<string, unknown>;
  if (typeof a.option_id === "string") return `option ${a.option_id}`;
  if (Array.isArray(a.option_ids)) return `options ${a.option_ids.join(", ")}`;
  if (typeof a.value === "number") return String(a.value);
  if (a.mode === "exact" && typeof a.value === "string") return `exactly ${a.value}`;
  if (a.mode === "range") return `${String(a.lower)} to ${String(a.upper)}`;
  return "none";
}

/** The paragraphs of a worked solution as plain text. Content is only ever shown as text. */
export function solutionText(blocks: unknown): string {
  if (!Array.isArray(blocks)) return "";
  return blocks
    .map((block) =>
      typeof block === "object" &&
      block !== null &&
      typeof (block as { text?: unknown }).text === "string"
        ? (block as { text: string }).text
        : "",
    )
    .filter((text) => text !== "")
    .join("\n\n");
}

export type Finding = { path: string; severity: string; message: string };

/** The findings of a verify run that are well formed, errors first. */
export function findingsOf(output: unknown): Finding[] {
  const listed = (output as { findings?: unknown } | null)?.findings;
  if (!Array.isArray(listed)) return [];
  const rank: Record<string, number> = { error: 0, warning: 1, note: 2 };
  return listed
    .filter(
      (item): item is Finding =>
        typeof item === "object" &&
        item !== null &&
        typeof (item as Finding).path === "string" &&
        typeof (item as Finding).severity === "string" &&
        typeof (item as Finding).message === "string",
    )
    .sort((a, b) => (rank[a.severity] ?? 3) - (rank[b.severity] ?? 3));
}
