import { describe, expect, it } from "vitest";

import {
  CONFIRM,
  RETURN_REASONS,
  STATE_LABEL,
  STEP_DONE,
  STEP_LABEL,
  STEP_ORDER,
  STEP_PATH,
  findingsTitle,
  isEditable,
  returnReady,
  stepIfMatch,
  visibleSteps,
  type State,
  type Step,
} from "../src/lib/workflow";

const STATES: State[] = [
  "DRAFT",
  "IN_REVIEW",
  "CHANGES_REQUESTED",
  "QC_PASSED",
  "APPROVED",
  "PUBLISHED",
];

describe("the steps", () => {
  it("each step has one place, a label, a route and a message", () => {
    expect(new Set(STEP_ORDER).size).toBe(STEP_ORDER.length);
    expect(STEP_ORDER).toHaveLength(Object.keys(STEP_LABEL).length);
    for (const step of STEP_ORDER) {
      expect(STEP_LABEL[step].length).toBeGreaterThan(0);
      expect(STEP_DONE[step].length).toBeGreaterThan(0);
      expect(STEP_PATH[step]).toMatch(/^\/api\/v1\/questions\/\{question_id\}\/[a-z-]+$/);
    }
    expect(new Set(Object.values(STEP_PATH)).size).toBe(STEP_ORDER.length);
  });

  it("shows exactly the allowed steps, in screen order", () => {
    const allowed: Step[] = ["WITHDRAW", "RETURN", "PASS_QC"];
    expect(visibleSteps(allowed)).toEqual(["PASS_QC", "RETURN", "WITHDRAW"]);
    expect(visibleSteps([])).toEqual([]);
  });

  it("checks submit against the text and every other step against the workflow", () => {
    expect(stepIfMatch("SUBMIT", 7, '"flow-3"')).toBe('"rev-7"');
    for (const step of STEP_ORDER.filter((s) => s !== "SUBMIT")) {
      expect(stepIfMatch(step, 7, '"flow-3"')).toBe('"flow-3"');
    }
  });

  it("asks before the steps that change something for good", () => {
    expect(Object.keys(CONFIRM).sort()).toEqual(["PUBLISH", "START_CORRECTION"]);
  });
});

describe("the states", () => {
  it("names every state", () => {
    for (const state of STATES) expect(STATE_LABEL[state].length).toBeGreaterThan(0);
  });

  it("lets only a draft and a returned question be edited", () => {
    expect(STATES.filter(isEditable)).toEqual(["DRAFT", "CHANGES_REQUESTED"]);
  });

  it("calls the findings the publication checklist once submitted", () => {
    expect(findingsTitle(null)).toBe("Findings");
    expect(findingsTitle("a-revision")).toBe("Publication checklist");
  });
});

describe("returning a question", () => {
  it("offers each reason once", () => {
    const codes = RETURN_REASONS.map((r) => r.code);
    expect(new Set(codes).size).toBe(codes.length);
    expect(codes).toContain("OTHER");
  });

  it("needs a reason and a note of at least ten characters", () => {
    expect(returnReady([], "A long enough note.")).toBe(false);
    expect(returnReady(["ANSWER_WRONG"], "short")).toBe(false);
    expect(returnReady(["ANSWER_WRONG"], "          x")).toBe(false); // spaces do not count
    expect(returnReady(["ANSWER_WRONG"], "The key says B.")).toBe(true);
    expect(returnReady(["ANSWER_WRONG"], "x".repeat(2001))).toBe(false);
  });
});
