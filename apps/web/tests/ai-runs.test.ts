import { describe, expect, it } from "vitest";

import {
  answerText,
  changedParts,
  errorText,
  findingsOf,
  isWaiting,
  phaseText,
  solutionText,
} from "../src/lib/ai-runs";

describe("is a run still going", () => {
  it("is for the waiting states and for any state it does not know", () => {
    for (const phase of ["RUNNING", "QUEUED", "SUBMITTING", "SUBMITTED", "SOMETHING_NEW"]) {
      expect(isWaiting({ phase })).toBe(true);
    }
    for (const phase of ["SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED", "SUBMISSION_UNKNOWN"]) {
      expect(isWaiting({ phase })).toBe(false);
    }
  });

  it("describes a state it does not know as in progress", () => {
    expect(phaseText("SOMETHING_NEW")).toBe("In progress");
    expect(phaseText("SUCCEEDED")).toBe("Done");
  });
});

describe("error sentences", () => {
  it("never repeats provider text and has a fallback", () => {
    expect(errorText(null)).toBeNull();
    expect(errorText("AI_OUTPUT_INVALID")).toContain("nothing was changed");
    expect(errorText("AI_PROVIDER_RATE_LIMITED")).toContain("slow down");
    expect(errorText("AI_SOMETHING_ELSE")).toBe("The run did not finish.");
  });
});

describe("what changed", () => {
  it("names the parts that differ and ignores the labels", () => {
    const before = { stem: [1], options: [1], answer: { option_id: "A" }, metadata: { a: 1 } };
    const after = { stem: [1], options: [2], answer: { option_id: "B" }, metadata: { a: 2 } };
    expect(changedParts(before, after)).toEqual(["the options", "the answer"]);
    expect(changedParts(before, before)).toEqual([]);
  });
});

describe("answers and solutions as text", () => {
  it("reads each answer shape", () => {
    expect(answerText({ option_id: "B" })).toBe("option B");
    expect(answerText({ option_ids: ["A", "C"] })).toBe("options A, C");
    expect(answerText({ value: 7 })).toBe("7");
    expect(answerText({ mode: "exact", value: "9.80" })).toBe("exactly 9.80");
    expect(answerText({ mode: "range", lower: "9.79", upper: "9.81" })).toBe("9.79 to 9.81");
    expect(answerText(null)).toBe("none");
    expect(answerText("x")).toBe("none");
  });

  it("joins the paragraphs and shows markup as plain characters", () => {
    const blocks = [
      { kind: "paragraph", text: "First." },
      { kind: "equation", source: "x^2" },
      { kind: "paragraph", text: "<b>Second</b>" },
    ];
    expect(solutionText(blocks)).toBe("First.\n\n<b>Second</b>");
    expect(solutionText(null)).toBe("");
  });
});

describe("findings", () => {
  it("lists errors first and drops malformed items", () => {
    const output = {
      findings: [
        { path: "a", severity: "note", message: "n" },
        { path: "b", severity: "error", message: "e" },
        { path: "c", severity: "warning" },
        "junk",
        { path: "d", severity: "warning", message: "w" },
      ],
    };
    expect(findingsOf(output).map((f) => f.path)).toEqual(["b", "d", "a"]);
    expect(findingsOf(null)).toEqual([]);
  });
});
