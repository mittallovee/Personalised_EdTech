import { describe, expect, it } from "vitest";

import {
  VERDICTS,
  blockedText,
  decisionText,
  matchText,
  type Decision,
} from "../src/lib/duplicates";

function decision(change: Partial<Decision>): Decision {
  return {
    other_question_id: "q",
    decision: "NOT_DUPLICATE",
    note: "different numbers",
    decided_by: "me",
    decided_at: "2026-11-17T10:00:00Z",
    ...change,
  };
}

describe("the possible duplicates", () => {
  it("says how a question matches", () => {
    expect(matchText({ match: "EXACT", similarity_percent: 100 })).toBe("Same content");
    expect(matchText({ match: "NEAR", similarity_percent: 83 })).toBe("Similar text (83%)");
  });

  it("says nothing when nobody has decided", () => {
    expect(decisionText(null, "me")).toBeNull();
  });

  it("says what was decided, by whom, and why", () => {
    expect(decisionText(decision({}), "me")).toBe(
      "You decided: not a duplicate. different numbers",
    );
    expect(
      decisionText(decision({ decision: "DUPLICATE_OF", decided_by: "x", note: "same" }), "me"),
    ).toBe("A colleague decided: a copy of this one. same");
  });

  it("offers both verdicts, each asking its own question", () => {
    expect(VERDICTS.map((v) => v.verdict)).toEqual(["NOT_DUPLICATE", "DUPLICATE_OF"]);
    expect(new Set(VERDICTS.map((v) => v.ask)).size).toBe(2);
  });

  it("says what blocks Pass QC, and nothing when nothing does", () => {
    expect(blockedText([])).toBeNull();
    expect(blockedText(["AAAA1111"])).toBe(
      "Pass QC is blocked by this question: AAAA1111. Decide whether each one is a duplicate.",
    );
    expect(blockedText(["AAAA1111", "BBBB2222"])).toBe(
      "Pass QC is blocked by these questions: AAAA1111, BBBB2222. Decide whether each one is a duplicate.",
    );
  });
});
