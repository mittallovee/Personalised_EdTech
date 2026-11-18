import type { components } from "@qbank/api-client";

/**
 * Words for the possible-duplicates panel (D-16, M4 design note §7.8–§7.9, §11.4). The API finds
 * the candidates, applies the visibility rule and says what blocks QC; this only names them.
 */

export type Duplicate = components["schemas"]["DuplicateOut"];
export type Decision = components["schemas"]["DecisionOut"];
export type Verdict = Decision["decision"];

/** How it matches: the same content, or similar text with how similar. */
export function matchText(duplicate: Pick<Duplicate, "match" | "similarity_percent">): string {
  return duplicate.match === "EXACT"
    ? "Same content"
    : `Similar text (${duplicate.similarity_percent}%)`;
}

/** What was decided about the pair, or null when nobody has decided yet. */
export function decisionText(decision: Decision | null, myId: string): string | null {
  if (decision === null) return null;
  const who = decision.decided_by === myId ? "You" : "A colleague";
  const what = decision.decision === "NOT_DUPLICATE" ? "not a duplicate" : "a copy of this one";
  return `${who} decided: ${what}. ${decision.note}`;
}

/** The words for the buttons that record a decision. */
export const VERDICTS: readonly { verdict: Verdict; label: string; ask: string }[] = [
  { verdict: "NOT_DUPLICATE", label: "Not a duplicate", ask: "Why is it not a duplicate?" },
  { verdict: "DUPLICATE_OF", label: "This question copies it", ask: "How does this copy it?" },
];

/** The sentence above the list when Pass QC is blocked by undecided or confirmed copies. */
export function blockedText(codes: readonly string[]): string | null {
  if (codes.length === 0) return null;
  return `Pass QC is blocked by ${codes.length === 1 ? "this question" : "these questions"}: ${codes.join(", ")}. Decide whether each one is a duplicate.`;
}
