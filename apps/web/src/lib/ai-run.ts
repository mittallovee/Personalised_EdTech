import type { components, ErrorResponse } from "@qbank/api-client";

import type { Content } from "@/lib/question-content";

export type Run = components["schemas"]["RunOut"];
export type RunOptions = components["schemas"]["RunOptionsOut"];
export type ModelChoice = components["schemas"]["ModelChoiceOut"];
export type Usage = components["schemas"]["UsageOut"];
type Operation = Run["operation"];

/** The button for each operation, in the order they are offered. */
export const ACTIONS: { operation: Operation; label: string; hint: string }[] = [
  {
    operation: "TAG",
    label: "Tag",
    hint: "Fill chapter, topic, concept, difficulty and Bloom level",
  },
  { operation: "SOLVE", label: "Solve", hint: "Suggest the answer and a worked solution" },
  { operation: "VERIFY", label: "Verify", hint: "Check the question and suggest a correction" },
  { operation: "TRANSLATE", label: "Translate", hint: "Make a linked copy in another language" },
];

const VERB: Record<Operation, string> = {
  TAG: "Run tagging",
  SOLVE: "Run solve",
  VERIFY: "Run verification",
  TRANSLATE: "Run translation",
};

export const runButtonLabel = (operation: Operation): string => VERB[operation];

export const OPERATION_NAME: Record<Operation, string> = {
  TAG: "Tag",
  SOLVE: "Solve",
  VERIFY: "Verify",
  TRANSLATE: "Translate",
};

/**
 * Whether the question can take this operation now. Translation only reads the question, so it
 * works on any question the person can open; the others write to the working text and need an
 * editable question (the API refuses otherwise, this only avoids offering a dead button), unless
 * the run is a test, which never writes.
 */
export function canRun(operation: Operation, editable: boolean, test: boolean): boolean {
  return operation === "TRANSLATE" || test || editable;
}

/** Why a run is not offered, in words; null when it is. */
export function whyNot(operation: Operation, editable: boolean, test: boolean): string | null {
  return canRun(operation, editable, test)
    ? null
    : "This question cannot be edited now, so a result could not be applied. Tick “Test run”, or withdraw the question first.";
}

const PRESENT = new Set(["QUEUED", "RUNNING", "SUBMITTING", "SUBMITTED"]);

/**
 * Whether a run is still going. `phase` is extensible (the API says a client must treat a value it
 * does not know as still in progress), so only the known endings count as finished.
 */
export function inProgress(run: Pick<Run, "phase">): boolean {
  if (PRESENT.has(run.phase)) return true;
  return !ENDINGS.has(run.phase);
}

const ENDINGS = new Set(["SUCCEEDED", "FAILED", "CANCELLED", "EXPIRED", "SUBMISSION_UNKNOWN"]);

const PHASE: Record<string, string> = {
  QUEUED: "Waiting to be sent",
  RUNNING: "Running",
  SUBMITTING: "Being sent to the provider",
  SUBMITTED: "Waiting for the provider",
  SUCCEEDED: "Done",
  FAILED: "Failed",
  CANCELLED: "Cancelled",
  EXPIRED: "Expired",
  SUBMISSION_UNKNOWN: "Not confirmed by the provider: an admin must settle it",
};

/** A run's state in words; a state this screen does not know is shown as still going. */
export function phaseText(run: Pick<Run, "phase">): string {
  return PHASE[run.phase] ?? "In progress";
}

const APPLY: Record<Run["apply_status"], string> = {
  NOT_APPLIED: "Nothing written to the question",
  APPLIED: "Applied to the question",
  OUT_OF_DATE: "Not applied: the question changed meanwhile",
  NEEDS_REVIEW: "Not applied: you can no longer edit this question",
};

/** What happened to the result, in words. A translation never changes the question it came from: applying it makes a new one. */
export function applyText(run: Pick<Run, "apply_status" | "operation">): string {
  if (run.operation === "TRANSLATE" && run.apply_status === "APPLIED") {
    return "Made into a new question; the original was not changed";
  }
  return APPLY[run.apply_status];
}

const PROMPT: Record<Run["prompt_source"], string> = {
  ONE_OFF: "a one-off prompt",
  PERSONAL: "your own prompt",
  COACHING: "the coaching prompt",
  PLATFORM: "the platform prompt",
};

export const promptText = (source: Run["prompt_source"]): string => PROMPT[source];

/** What a model costs per million tokens, as the dialog shows it ("$1 in, $2 out"), or "price unknown". */
export function modelPrice(
  model: Pick<ModelChoice, "price_in_per_mtok" | "price_out_per_mtok">,
): string {
  const { price_in_per_mtok: input, price_out_per_mtok: output } = model;
  if (input === null || output === null) return "price unknown";
  return `$${input} in, $${output} out per million tokens`;
}

/** The model offered first for an operation, if it can still be used. */
export function firstModel(options: RunOptions, operation: Operation): ModelChoice | null {
  const chosen = options.operations.find((entry) => entry.operation === operation);
  return options.models.find((model) => model.id === chosen?.default_model_id) ?? null;
}

/** The mode offered first: Economy only when the model allows it. */
export function firstMode(
  options: RunOptions,
  operation: Operation,
  model: ModelChoice | null,
): "NOW" | "ECONOMY" {
  const chosen = options.operations.find((entry) => entry.operation === operation);
  return chosen?.mode === "ECONOMY" && model?.economy ? "ECONOMY" : "NOW";
}

/** What is left of the person's monthly budget, in words. */
export function budgetText(usage: Usage): string {
  if (usage.state === "REACHED") return "Your budget for this month is used up.";
  if (usage.state === "OFF") {
    return "A budget is set but no dollar-to-rupee rate is entered yet, so it cannot be counted. Ask an admin.";
  }
  if (usage.limit_inr === null || usage.remaining_inr === null) {
    return `Spent this month: ₹${usage.spent_inr}. No limit is set.`;
  }
  const warning = usage.state === "WARNING" ? " You are close to the limit." : "";
  return `Budget left this month: ₹${usage.remaining_inr} of ₹${usage.limit_inr}.${warning}`;
}

// --- Reading a result ---------------------------------------------------------------------------
// `result` is untyped JSON in the contract. Each reader checks the shape it needs and answers
// null when it is not there, so a run from a newer server never breaks the screen. Text from the
// model is only ever shown as text, or through the shared content renderer.

type Json = Record<string, unknown>;
const isObject = (value: unknown): value is Json =>
  typeof value === "object" && value !== null && !Array.isArray(value);

function output(run: Run): Json | null {
  const found = run.result?.["output"];
  return isObject(found) ? found : null;
}

export type Finding = { path: string; severity: "error" | "warning" | "note"; message: string };

/** The findings of a verification, in the order the model gave them. */
export function findingsOf(run: Run): Finding[] | null {
  const found = output(run)?.["findings"];
  if (!Array.isArray(found)) return null;
  return found.flatMap((item): Finding[] => {
    if (!isObject(item)) return [];
    const { path, severity, message } = item;
    if (typeof path !== "string" || typeof message !== "string") return [];
    if (severity !== "error" && severity !== "warning" && severity !== "note") return [];
    return [{ path, severity, message }];
  });
}

/** The corrected question a verification offered, if it did. */
export function correctionOf(run: Run): Content | null {
  const found = output(run)?.["corrected_content"];
  return isObject(found) ? found : null;
}

/** The suggested answer and worked solution of a solve run. */
export function solutionOf(run: Run): { answer: Json; solution: unknown } | null {
  const found = output(run);
  if (!found || !isObject(found["answer"])) return null;
  return { answer: found["answer"], solution: found["solution"] };
}

/** The translated question of a translate run, its language, and the new question once made. */
export function translationOf(
  run: Run,
): { language: string; content: Content; created: { id: string; code: string } | null } | null {
  const found = output(run);
  if (!found || !isObject(found["content"]) || typeof found["language"] !== "string") return null;
  const created = found["created_question"];
  return {
    language: found["language"],
    content: found["content"],
    created:
      isObject(created) && typeof created["id"] === "string" && typeof created["code"] === "string"
        ? { id: created["id"], code: created["code"] }
        : null,
  };
}

/** The labels a tag run chose, and the labels they replaced, as plain values. */
export function labelsOf(run: Run): { chosen: Json; before: Json } | null {
  const chosen = output(run);
  if (!chosen) return null;
  const before = run.result?.["before"];
  return { chosen, before: isObject(before) ? before : {} };
}

/**
 * Whether a finished run still has something for the person to decide: a suggested answer, a
 * correction, or a translation not yet made into a question. Never for a test, a failure or a run
 * already applied or out of date (the API refuses those anyway).
 */
export function canApply(run: Run): boolean {
  if (run.is_test || run.phase !== "SUCCEEDED" || run.apply_status !== "NOT_APPLIED") return false;
  if (run.operation === "SOLVE") return solutionOf(run) !== null;
  if (run.operation === "VERIFY") return correctionOf(run) !== null;
  if (run.operation === "TRANSLATE") {
    const made = translationOf(run);
    return made !== null && made.created === null;
  }
  return false;
}

/** The content with the suggested answer and solution put in, to preview the suggestion. */
export function withSolution(
  content: Content,
  suggestion: { answer: Json; solution: unknown },
): Content {
  return { ...content, answer: suggestion.answer, solution: suggestion.solution };
}

/**
 * A suggested or current answer in words, for the old/new view. Reads the answer shapes of the
 * formats (an option, several options, a whole number, an exact value or a range); anything else
 * is "no answer", never a guess.
 */
export function answerText(answer: unknown): string {
  if (!isObject(answer)) return "No answer yet";
  if (typeof answer["option_id"] === "string") return `Option ${answer["option_id"]}`;
  const ids = answer["option_ids"];
  if (Array.isArray(ids) && ids.every((id) => typeof id === "string")) {
    return ids.length === 0 ? "No option" : `Options ${ids.join(", ")}`;
  }
  if (typeof answer["value"] === "number") return String(answer["value"]);
  if (
    answer["mode"] === "range" &&
    answer["lower"] !== undefined &&
    answer["upper"] !== undefined
  ) {
    return `From ${String(answer["lower"])} to ${String(answer["upper"])}`;
  }
  if (typeof answer["value"] === "string") return answer["value"];
  return "No answer yet";
}

/** The marks a verification finding is shown with. */
export const SEVERITY: Record<Finding["severity"], { label: string; className: string }> = {
  error: { label: "Mistake", className: "text-red-700 dark:text-red-300" },
  warning: { label: "Worth a look", className: "text-amber-800 dark:text-amber-300" },
  note: { label: "Note", className: "text-zinc-700 dark:text-zinc-300" },
};

/** A failed run's reason in words; the API gives only a code, and a code never reaches the screen alone. */
export function failureText(code: string | null): string {
  if (code === null) return "The run did not finish.";
  if (code.startsWith("AI_PROVIDER_")) {
    return "The AI provider did not give a usable answer (it was too slow, refused, or was busy). Nothing was changed. You can try again or pick another model.";
  }
  if (code === "AI_RUN_CANCELLED") return "The run was cancelled.";
  return "The answer could not be used, so nothing was changed. You can try again or pick another model.";
}

/** Rupees as text ("42.5", "500.00") in whole paise, or null if it is not a plain amount. */
function paise(value: string): number | null {
  const match = /^(\d{1,12})(?:\.(\d{1,2}))?\d*$/.exec(value.trim());
  if (!match) return null;
  return Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0") || "0");
}

/**
 * How much of a budget is spent, as a whole percent from 0 to 100 for a bar, or null when there is
 * no limit. Worked in whole paise (whole numbers, exact at these sizes), not in fractions of a
 * rupee; only the bar's width comes from it.
 */
export function percentUsed(spentInr: string, limitInr: string | null): number | null {
  if (limitInr === null) return null;
  const spent = paise(spentInr);
  const limit = paise(limitInr);
  if (spent === null || limit === null) return null;
  if (limit === 0) return 100;
  return Math.min(100, Math.floor((spent * 100) / limit));
}

/**
 * What is wrong with a prompt the server refused, one sentence each. The API lists them in
 * `details.problems`; any other error has none.
 */
export function problemsOf(error: ErrorResponse | undefined): string[] {
  const problems = error?.error.details["problems"];
  if (!Array.isArray(problems)) return [];
  return problems.flatMap((item) => {
    const message = (item as { message?: unknown } | null)?.message;
    return typeof message === "string" ? [message] : [];
  });
}

/**
 * Whether any run already known has just been applied to the question since the last look, and
 * what each run's apply state is now. A run seen for the first time never counts: the first look
 * only sets the baseline, so opening the tab does not look like a change.
 */
export function noticeWrites(
  before: ReadonlyMap<string, string>,
  runs: Pick<Run, "id" | "apply_status">[],
): { written: boolean; next: Map<string, string> } {
  let written = false;
  const next = new Map<string, string>();
  for (const run of runs) {
    const was = before.get(run.id);
    if (was !== undefined && was !== "APPLIED" && run.apply_status === "APPLIED") written = true;
    next.set(run.id, run.apply_status);
  }
  return { written, next };
}
