import type { components } from "@qbank/api-client";

export type IngestFile = components["schemas"]["IngestFileOut"];
export type IngestPage = components["schemas"]["IngestPageOut"];
export type Candidate = components["schemas"]["CandidateOut"];
export type IngestRun = components["schemas"]["StartedRun"];

export const MB = 1024 * 1024;
export const MAX_DOCUMENT_BYTES = 50 * MB;
export const MAX_IMAGE_BYTES = 10 * MB;
/** What the file picker offers; the server decides the kind from the bytes whatever the name says. */
export const ACCEPT = ".pdf,.docx,.jpg,.jpeg,.png,.webp,.heic,.heif";

const STATE: Record<string, string> = {
  UPLOADED: "Waiting to be read",
  RENDERING: "Making pages",
  READY: "Pages ready",
  EXTRACTING: "Reading the questions",
  DONE: "Done",
  PARTIAL: "Done, with some pages not read",
  FAILED: "Failed",
  CANCELLED: "Cancelled",
};

/** A file's state in words; a state this screen does not know is shown as still going. */
export function stateText(state: string): string {
  return STATE[state] ?? "In progress";
}

const ENDED = new Set(["READY", "DONE", "PARTIAL", "FAILED", "CANCELLED"]);

/** Whether a file is still being worked on (so the list looks again soon). Unknown states count as going. */
export function isActive(state: string): boolean {
  return !ENDED.has(state);
}

/** Whether the person can still stop it. */
export function canCancel(state: string): boolean {
  return (
    state === "UPLOADED" || state === "RENDERING" || state === "READY" || state === "EXTRACTING"
  );
}

export function canRetry(state: string): boolean {
  return state === "FAILED" || state === "CANCELLED";
}

/** Whether the questions of this file can be read (again). */
export function canRead(state: string): boolean {
  return state === "READY" || state === "DONE" || state === "PARTIAL" || state === "FAILED";
}

const ERRORS: Record<string, string> = {
  UNREADABLE_DOCUMENT: "The file could not be opened. It may be damaged or not what its name says.",
  UNREADABLE_PICTURE: "The picture could not be read.",
  PICTURE_TOO_LARGE: "The picture is too large to read.",
  NOT_A_WORD_FILE: "This is not a Word (.docx) document.",
  DOCUMENT_TOO_LARGE: "The document is too large or too complicated to read.",
  PASSWORD_PROTECTED:
    "The document is password protected. Remove the password and upload it again.",
  EMPTY_DOCUMENT: "The document has nothing in it to read.",
  TOO_MANY_PAGES: "The document has more than 200 pages. Split it and upload the parts.",
  TOO_SLOW: "Reading the document took too long. You can try again.",
  NO_READABLE_PAGE: "No page of the document could be read.",
  SOME_PAGES_FAILED: "Some pages could not be read; the others are kept.",
  ORIGINAL_MISSING: "The original file is no longer available.",
  PAGE_TOO_LARGE: "This page is too large to read.",
  PAGE_UNREADABLE: "This page could not be read.",
  PICTURE_MISSING: "The page picture is missing.",
  AI_BUDGET_EXCEEDED: "Your AI budget for this month is used up. Reading stopped.",
  AI_KEY_MISSING: "No provider key is stored. An admin adds one under Admin, AI.",
  AI_KEY_UNREADABLE: "The stored provider key could not be opened. An admin must enter it again.",
  AI_MODEL_NOT_ENABLED: "The model chosen for reading is no longer enabled.",
  AI_MODEL_UNAVAILABLE: "The provider no longer lists the model chosen for reading.",
  AI_MODEL_NO_VISION: "The model chosen for reading is not known to read pictures.",
  AI_OUTPUT_INVALID: "The AI's answer for this page could not be used.",
  NO_PAGE_READ: "No page could be read by the AI.",
};

/** A failure code in words. A code never reaches the screen alone: an unknown one gets a plain sentence. */
export function errorText(code: string | null | undefined): string | null {
  if (!code) return null;
  if (ERRORS[code]) return ERRORS[code];
  if (code.startsWith("AI_PROVIDER_")) {
    return "The AI provider did not answer well (too slow, busy or refused). You can try again.";
  }
  return "Something went wrong with this document. You can try again.";
}

const WARNINGS: Record<string, string> = {
  HANDWRITTEN: "Handwritten: check it carefully",
  LOW_CONFIDENCE: "The AI was not sure",
  ANSWER_NOT_READ: "The printed answer could not be read",
  OVERPRECISE_ANSWER: "The printed answer has more decimal places than allowed (not rounded)",
  EQUATION_AS_TEXT: "An equation is kept as text: check it by eye",
};

export function warningText(code: string): string {
  return WARNINGS[code] ?? "Check this carefully";
}

/** The first line of a candidate's question, for a list. */
export function titleOf(content: Record<string, unknown>): string {
  const stem = content["stem"];
  if (Array.isArray(stem)) {
    for (const block of stem) {
      const text = (block as { text?: unknown } | null)?.text;
      if (typeof text === "string" && text.trim() !== "") return text.trim().slice(0, 120);
    }
  }
  return "(no text)";
}

/** Whether a file the person picked can be sent: its size is under the limit for its kind. A hint only; the server decides. */
export function sizeProblem(file: { name: string; size: number }): string | null {
  const isImage = /\.(jpe?g|png|webp|heic|heif)$/i.test(file.name);
  const limit = isImage ? MAX_IMAGE_BYTES : MAX_DOCUMENT_BYTES;
  if (file.size === 0) return "The file is empty.";
  if (file.size > limit) {
    return `${file.name} is larger than ${limit / MB} MB${isImage ? " (the limit for a picture)" : ""}.`;
  }
  return null;
}

/** The counts of a file's candidates by state, for the summary line. */
export function tally(candidates: Pick<Candidate, "state">[]): Record<Candidate["state"], number> {
  const counts: Record<Candidate["state"], number> = {
    NEW: 0,
    ACCEPTED: 0,
    REJECTED: 0,
    DUPLICATE: 0,
  };
  for (const candidate of candidates) counts[candidate.state] += 1;
  return counts;
}

/** The candidate after or before the current one, staying put at either end; the first still-open one when there is no current. */
export function neighbour(
  list: Pick<Candidate, "id">[],
  currentId: string | null,
  step: 1 | -1,
): string | null {
  if (list.length === 0) return null;
  const at = list.findIndex((candidate) => candidate.id === currentId);
  if (at < 0) return list[0]!.id;
  return list[Math.min(list.length - 1, Math.max(0, at + step))]!.id;
}

/** The first candidate still waiting for a decision after `currentId`, wrapping to the start; null when none is. */
export function nextOpen(
  list: Pick<Candidate, "id" | "state">[],
  currentId: string | null,
): string | null {
  const start = list.findIndex((candidate) => candidate.id === currentId);
  for (let step = 1; step <= list.length; step += 1) {
    const candidate = list[(start + step) % list.length];
    if (candidate && candidate.state === "NEW" && candidate.id !== currentId) return candidate.id;
  }
  return null;
}

export type Shortcut = "next" | "previous" | "accept" | "reject" | "same" | "next-open" | null;

/**
 * The review screen's keyboard shortcuts. Nothing fires while a person is typing in a field or
 * holding a modifier, so a letter typed into the question is never an action.
 */
export function shortcutOf(event: {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  altKey?: boolean;
  target?: { tagName?: string; isContentEditable?: boolean } | null;
}): Shortcut {
  if (event.ctrlKey || event.metaKey || event.altKey) return null;
  const tag = event.target?.tagName?.toUpperCase();
  if (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    event.target?.isContentEditable
  ) {
    return null;
  }
  switch (event.key) {
    case "j":
    case "ArrowDown":
      return "next";
    case "k":
    case "ArrowUp":
      return "previous";
    case "a":
      return "accept";
    case "r":
      return "reject";
    case "s":
      return "same";
    case "n":
      return "next-open";
    default:
      return null;
  }
}

/** A region of the page as CSS percentages for an overlay, kept inside the page; null when there is none. */
export function boxStyle(
  region: Record<string, number> | null,
): { left: string; top: string; width: string; height: string } | null {
  if (!region) return null;
  const clamp = (value: unknown) =>
    typeof value === "number" && Number.isFinite(value) ? Math.min(1, Math.max(0, value)) : null;
  const x = clamp(region["x"]);
  const y = clamp(region["y"]);
  const w = clamp(region["w"]);
  const h = clamp(region["h"]);
  if (x === null || y === null || w === null || h === null || w === 0 || h === 0) return null;
  const percent = (value: number) => `${Math.round(value * 10000) / 100}%`;
  return {
    left: percent(x),
    top: percent(y),
    width: percent(Math.min(w, 1 - x)),
    height: percent(Math.min(h, 1 - y)),
  };
}
