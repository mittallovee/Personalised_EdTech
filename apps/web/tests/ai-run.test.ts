import { describe, expect, it } from "vitest";

import {
  answerText,
  applyText,
  budgetText,
  canApply,
  canRun,
  correctionOf,
  findingsOf,
  firstMode,
  failureText,
  firstModel,
  inProgress,
  noticeWrites,
  phaseText,
  problemsOf,
  modelPrice,
  percentUsed,
  solutionOf,
  translationOf,
  withSolution,
  type ModelChoice,
  type Run,
  type RunOptions,
  type Usage,
} from "../src/lib/ai-run";

function run(changes: Partial<Run> = {}): Run {
  return {
    id: "r1",
    question_id: "q1",
    operation: "SOLVE",
    mode: "NOW",
    status: "SUCCEEDED",
    phase: "SUCCEEDED",
    cancel_requested: false,
    apply_status: "NOT_APPLIED",
    is_test: false,
    requested_by: "u1",
    prompt_source: "COACHING",
    prompt_version_id: null,
    answered_by: "m",
    result: null,
    error_code: null,
    started_at: "2026-11-28T00:00:00Z",
    finished_at: null,
    attempts: [],
    ...changes,
  };
}

const model = (changes: Partial<ModelChoice> = {}): ModelChoice => ({
  id: "m1",
  provider: "OPENAI",
  display_name: "small",
  price_in_per_mtok: "1",
  price_out_per_mtok: "2",
  economy: true,
  ...changes,
});

describe("what can be run", () => {
  it("lets translation run on any question, and the others only on an editable one", () => {
    expect(canRun("TRANSLATE", false, false)).toBe(true);
    expect(canRun("SOLVE", false, false)).toBe(false);
    expect(canRun("SOLVE", true, false)).toBe(true);
  });
  it("lets a test run on a question that cannot be edited, because a test never writes", () => {
    expect(canRun("VERIFY", false, true)).toBe(true);
  });
});

describe("a run still going", () => {
  it("is going until one of the known endings", () => {
    for (const phase of ["QUEUED", "RUNNING", "SUBMITTING", "SUBMITTED"]) {
      expect(inProgress({ phase })).toBe(true);
    }
    for (const phase of ["SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED", "SUBMISSION_UNKNOWN"]) {
      expect(inProgress({ phase })).toBe(false);
    }
  });
  it("treats a state it does not know as still going, as the contract says", () => {
    expect(inProgress({ phase: "SOMETHING_NEW" })).toBe(true);
    expect(phaseText({ phase: "SOMETHING_NEW" })).toBe("In progress");
  });
});

describe("the model and its price", () => {
  const options: RunOptions = {
    operations: [
      { operation: "SOLVE", default_model_id: "m1", mode: "ECONOMY" },
      { operation: "TAG", default_model_id: null, mode: "NOW" },
    ],
    models: [model(), model({ id: "m2", economy: false })],
  };
  it("offers the operation's own model first, and none when it is not set", () => {
    expect(firstModel(options, "SOLVE")?.id).toBe("m1");
    expect(firstModel(options, "TAG")).toBeNull();
  });
  it("offers Economy first only when the model allows it", () => {
    expect(firstMode(options, "SOLVE", model())).toBe("ECONOMY");
    expect(firstMode(options, "SOLVE", model({ economy: false }))).toBe("NOW");
    expect(firstMode(options, "SOLVE", null)).toBe("NOW");
  });
  it("shows a price as text and says when it is not known", () => {
    expect(modelPrice(model())).toBe("$1 in, $2 out per million tokens");
    expect(modelPrice(model({ price_out_per_mtok: null }))).toBe("price unknown");
  });
});

describe("the budget in words", () => {
  const usage = (changes: Partial<Usage>): Usage => ({
    period: "2026-11",
    spent_usd: "0.5",
    spent_inr: "42.00",
    limit_inr: "500.00",
    remaining_inr: "458.00",
    state: "OK",
    ...changes,
  });
  it("says what is left, a warning near the limit, and when it is used up", () => {
    expect(budgetText(usage({}))).toBe("Budget left this month: ₹458.00 of ₹500.00.");
    expect(budgetText(usage({ state: "WARNING" }))).toContain("close to the limit");
    expect(budgetText(usage({ state: "REACHED" }))).toContain("used up");
  });
  it("says what was spent when there is no limit, and explains a budget without a rate", () => {
    expect(budgetText(usage({ limit_inr: null, remaining_inr: null, state: "NO_LIMIT" }))).toBe(
      "Spent this month: ₹42.00. No limit is set.",
    );
    expect(budgetText(usage({ state: "OFF", remaining_inr: null }))).toContain("rate");
  });
});

describe("reading a result", () => {
  it("reads verification findings and drops malformed or unknown ones", () => {
    const found = findingsOf(
      run({
        operation: "VERIFY",
        result: {
          output: {
            findings: [
              { path: "answer", severity: "error", message: "Wrong sign." },
              { path: "x", severity: "fatal", message: "unknown severity" },
              { path: 1, severity: "note", message: "bad path" },
              "junk",
            ],
          },
        },
      }),
    );
    expect(found).toEqual([{ path: "answer", severity: "error", message: "Wrong sign." }]);
  });
  it("answers null when the result is not there or not in the expected shape", () => {
    expect(findingsOf(run({ result: null }))).toBeNull();
    expect(correctionOf(run({ result: { output: { corrected_content: "text" } } }))).toBeNull();
    expect(solutionOf(run({ result: { output: { answer: "C" } } }))).toBeNull();
    expect(translationOf(run({ result: { output: { language: "hi" } } }))).toBeNull();
  });
  it("puts a suggested answer and solution into the question to preview it", () => {
    const suggestion = solutionOf(
      run({
        result: { output: { answer: { option_id: "C" }, solution: [{ kind: "paragraph" }] } },
      }),
    );
    expect(suggestion).not.toBeNull();
    const preview = withSolution({ question_type: "SCQ", answer: { option_id: "A" } }, suggestion!);
    expect(preview).toEqual({
      question_type: "SCQ",
      answer: { option_id: "C" },
      solution: [{ kind: "paragraph" }],
    });
  });
});

describe("whether a result is waiting for a decision", () => {
  const solved = { output: { answer: { option_id: "C" }, solution: [] } };
  const corrected = { output: { findings: [], corrected_content: { question_type: "SCQ" } } };
  const translated = { output: { language: "hi", content: { question_type: "SCQ" } } };
  it("is waiting for a solve, a verify with a correction, and a translation not yet made", () => {
    expect(canApply(run({ result: solved }))).toBe(true);
    expect(canApply(run({ operation: "VERIFY", result: corrected }))).toBe(true);
    expect(canApply(run({ operation: "TRANSLATE", result: translated }))).toBe(true);
  });
  it("is not waiting for a verify without a correction, a translation already made, or tagging", () => {
    expect(canApply(run({ operation: "VERIFY", result: { output: { findings: [] } } }))).toBe(
      false,
    );
    const made = { output: { ...translated.output, created_question: { id: "q2", code: "ABC" } } };
    expect(canApply(run({ operation: "TRANSLATE", result: made }))).toBe(false);
    expect(canApply(run({ operation: "TAG", result: solved }))).toBe(false);
  });
  it("is never waiting for a test, a failure, or a result already applied or out of date", () => {
    expect(canApply(run({ result: solved, is_test: true }))).toBe(false);
    expect(canApply(run({ result: solved, phase: "FAILED" }))).toBe(false);
    expect(canApply(run({ result: solved, phase: "RUNNING" }))).toBe(false);
    expect(canApply(run({ result: solved, apply_status: "APPLIED" }))).toBe(false);
    expect(canApply(run({ result: solved, apply_status: "OUT_OF_DATE" }))).toBe(false);
  });
});

describe("an answer in words", () => {
  it("reads each shape of answer", () => {
    expect(answerText({ option_id: "C" })).toBe("Option C");
    expect(answerText({ option_ids: ["A", "C"] })).toBe("Options A, C");
    expect(answerText({ value: 42 })).toBe("42");
    expect(answerText({ mode: "exact", value: "9.81", lower: null, upper: null })).toBe("9.81");
    expect(answerText({ mode: "range", value: null, lower: "9.00", upper: "10.00" })).toBe(
      "From 9.00 to 10.00",
    );
  });
  it("says there is no answer rather than guess", () => {
    expect(answerText(null)).toBe("No answer yet");
    expect(answerText({})).toBe("No answer yet");
    expect(answerText({ option_ids: [1, 2] })).toBe("No answer yet");
  });
});

describe("why a run failed", () => {
  it("never shows a bare code", () => {
    expect(failureText("AI_PROVIDER_TIMEOUT")).toContain("Nothing was changed");
    expect(failureText("AI_RUN_CANCELLED")).toBe("The run was cancelled.");
    expect(failureText("AI_BAD_OUTPUT")).toContain("could not be used");
    expect(failureText(null)).toBe("The run did not finish.");
  });
});

describe("the budget bar", () => {
  it("is the whole percent spent, held at 100", () => {
    expect(percentUsed("0.00", "500.00")).toBe(0);
    expect(percentUsed("125.00", "500.00")).toBe(25);
    expect(percentUsed("250.5", "500")).toBe(50);
    expect(percentUsed("999", "500")).toBe(100);
  });
  it("has no bar without a limit, and is full for a limit of nothing", () => {
    expect(percentUsed("10.00", null)).toBeNull();
    expect(percentUsed("0.00", "0.00")).toBe(100);
    expect(percentUsed("abc", "500")).toBeNull();
  });
});

describe("what happened to a result", () => {
  it("says what applying did, and that a translation made a new question", () => {
    expect(applyText({ operation: "SOLVE", apply_status: "APPLIED" })).toBe(
      "Applied to the question",
    );
    expect(applyText({ operation: "TRANSLATE", apply_status: "APPLIED" })).toContain(
      "new question",
    );
    expect(applyText({ operation: "VERIFY", apply_status: "OUT_OF_DATE" })).toContain("changed");
  });
});

describe("what is wrong with a refused prompt", () => {
  const refusedWith = (details: Record<string, unknown>) =>
    ({
      error: { code: "AI_PROMPT_INVALID", message: "This prompt cannot be used.", details },
    }) as never;
  it("lists each problem the server gave", () => {
    expect(
      problemsOf(
        refusedWith({
          problems: [{ code: "a", message: "Add {{question}}." }, { message: "Too long." }],
        }),
      ),
    ).toEqual(["Add {{question}}.", "Too long."]);
  });
  it("is empty for any other error, and ignores entries it cannot read", () => {
    expect(problemsOf(refusedWith({}))).toEqual([]);
    expect(problemsOf(undefined)).toEqual([]);
    expect(problemsOf(refusedWith({ problems: [null, 3, { message: 4 }] }))).toEqual([]);
  });
});

describe("noticing a run that wrote to the question", () => {
  it("sees a run known as waiting that is now applied", () => {
    const before = new Map([["r1", "NOT_APPLIED"]]);
    const seen = noticeWrites(before, [{ id: "r1", apply_status: "APPLIED" }]);
    expect(seen.written).toBe(true);
    expect(seen.next.get("r1")).toBe("APPLIED");
  });
  it("does not count the first look, a run already applied, or one still waiting", () => {
    expect(noticeWrites(new Map(), [{ id: "r1", apply_status: "APPLIED" }]).written).toBe(false);
    expect(
      noticeWrites(new Map([["r1", "APPLIED"]]), [{ id: "r1", apply_status: "APPLIED" }]).written,
    ).toBe(false);
    expect(
      noticeWrites(new Map([["r1", "NOT_APPLIED"]]), [{ id: "r1", apply_status: "NOT_APPLIED" }])
        .written,
    ).toBe(false);
  });
});
