import type { components } from "@qbank/api-client";

/**
 * Words and routes for the review workflow (M4 design note §4). The screen holds no rules: which
 * steps a person may take comes from the API (`allowed_steps`), and so do the checks behind each
 * step. This file only says what each state and step is called and where each step is sent.
 */

export type State = components["schemas"]["State"];
export type Step = components["schemas"]["Step"];
export type ReturnReason = components["schemas"]["ReturnReason"];

export const STATE_LABEL: Record<State, string> = {
  DRAFT: "Draft",
  IN_REVIEW: "In review",
  CHANGES_REQUESTED: "Returned to the author",
  QC_PASSED: "QC passed",
  APPROVED: "Approved",
  PUBLISHED: "Published",
};

/** Only a draft and a returned question can be edited; the API refuses saves otherwise. */
export function isEditable(state: State): boolean {
  return state === "DRAFT" || state === "CHANGES_REQUESTED";
}

/** The order the buttons appear in: the step that moves the question on first. */
export const STEP_ORDER: readonly Step[] = [
  "SUBMIT",
  "PASS_QC",
  "APPROVE",
  "PUBLISH",
  "START_CORRECTION",
  "RETURN",
  "WITHDRAW",
];

export const STEP_LABEL: Record<Step, string> = {
  SUBMIT: "Submit for review",
  PASS_QC: "Pass QC",
  APPROVE: "Approve",
  PUBLISH: "Publish",
  START_CORRECTION: "Start a correction",
  RETURN: "Return to the author",
  WITHDRAW: "Withdraw to edit",
};

/** What the screen says once the step went through. */
export const STEP_DONE: Record<Step, string> = {
  SUBMIT: "Submitted for review. It can no longer be edited unless it is withdrawn or returned.",
  PASS_QC: "QC passed. It now waits for approval.",
  APPROVE: "Approved. It now waits to be published.",
  PUBLISH: "Published. Everyone in the coaching can now use it; it will never change.",
  START_CORRECTION: "A correction has started as a new version. The published one stays as it is.",
  RETURN: "Returned to the author with your reasons.",
  WITHDRAW: "Withdrawn. You can edit it again; submit it when it is ready.",
};

export type StepPath =
  | "/api/v1/questions/{question_id}/submit"
  | "/api/v1/questions/{question_id}/pass-qc"
  | "/api/v1/questions/{question_id}/approve"
  | "/api/v1/questions/{question_id}/publish"
  | "/api/v1/questions/{question_id}/start-correction"
  | "/api/v1/questions/{question_id}/return"
  | "/api/v1/questions/{question_id}/withdraw";

export const STEP_PATH: Record<Step, StepPath> = {
  SUBMIT: "/api/v1/questions/{question_id}/submit",
  PASS_QC: "/api/v1/questions/{question_id}/pass-qc",
  APPROVE: "/api/v1/questions/{question_id}/approve",
  PUBLISH: "/api/v1/questions/{question_id}/publish",
  START_CORRECTION: "/api/v1/questions/{question_id}/start-correction",
  RETURN: "/api/v1/questions/{question_id}/return",
  WITHDRAW: "/api/v1/questions/{question_id}/withdraw",
};

/**
 * Submit is checked against the text being submitted (its revision ETag, `"rev-N"`); every later
 * step against the workflow ETag (`"flow-N"`), so a step taken on an out-of-date screen is refused.
 */
export function stepIfMatch(step: Step, revision: number, flowEtag: string): string {
  return step === "SUBMIT" ? `"rev-${revision}"` : flowEtag;
}

/** The steps to show, in screen order: exactly the ones the API allows. */
export function visibleSteps(allowed: readonly Step[]): Step[] {
  return STEP_ORDER.filter((step) => allowed.includes(step));
}

/** Steps that change something for good, so the screen asks first. */
export const CONFIRM: Partial<Record<Step, { question: string; detail: string }>> = {
  PUBLISH: {
    question: "Publish this question?",
    detail:
      "A published question never changes. Mistakes found later are fixed in a correction, which" +
      " becomes the next version when it is published.",
  },
  START_CORRECTION: {
    question: "Start a correction?",
    detail:
      "This makes a new draft version as a copy of the published one. The published version stays" +
      " in use, unchanged, until the correction is published.",
  },
};

/** The fixed reasons for returning a question (design note appendix), as the author reads them. */
export const RETURN_REASONS: readonly { code: ReturnReason; label: string }[] = [
  { code: "ANSWER_WRONG", label: "The answer is wrong or does not match the question" },
  { code: "STATEMENT_UNCLEAR", label: "The question text is unclear, incomplete or ambiguous" },
  { code: "OPTIONS_FLAWED", label: "An option is wrong, repeated, or gives the answer away" },
  { code: "SOLUTION_WRONG", label: "The solution is wrong or skips steps" },
  { code: "LABELS_WRONG", label: "Class, subject, chapter, topic or concept is wrong" },
  { code: "DIFFICULTY_OR_BLOOM_WRONG", label: "The difficulty or Bloom level does not fit" },
  { code: "DUPLICATE", label: "This looks like a copy of another question" },
  { code: "FORMATTING", label: "Equations, pictures or layout need fixing" },
  { code: "OTHER", label: "Something else (explained in the note)" },
];

/** The note's limits, as the API states them (`ReturnIn`). */
export const NOTE_MIN = 10;
export const NOTE_MAX = 2000;

/** Whether the Return form can be sent; the API checks the same again and has the last word. */
export function returnReady(reasons: readonly ReturnReason[], note: string): boolean {
  return reasons.length > 0 && note.trim().length >= NOTE_MIN && note.length <= NOTE_MAX;
}

/** The findings panel's title: once submitted it is the publication checklist (E-07). */
export function findingsTitle(reviewRevisionId: string | null): string {
  return reviewRevisionId === null ? "Findings" : "Publication checklist";
}
