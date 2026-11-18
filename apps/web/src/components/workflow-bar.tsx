"use client";

import { STATE_LABEL, STEP_LABEL, visibleSteps, type State, type Step } from "@/lib/workflow";

const BADGE: Record<State, string> = {
  DRAFT: "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200",
  IN_REVIEW: "bg-sky-100 text-sky-900 dark:bg-sky-950 dark:text-sky-200",
  CHANGES_REQUESTED: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-200",
  QC_PASSED: "bg-indigo-100 text-indigo-900 dark:bg-indigo-950 dark:text-indigo-200",
  APPROVED: "bg-violet-100 text-violet-900 dark:bg-violet-950 dark:text-violet-200",
  PUBLISHED: "bg-emerald-100 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-200",
};

const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";

/** The question's workflow state, as a badge. */
export function StateBadge({ state }: { state: State }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${BADGE[state]}`}>
      {STATE_LABEL[state]}
    </span>
  );
}

/**
 * The review steps this person may take now (E-01): exactly the API's `allowed_steps`, nothing
 * worked out here. The first one is the main button.
 */
export function WorkflowBar({
  allowed,
  disabled,
  onStep,
}: {
  allowed: readonly Step[];
  disabled: boolean;
  onStep: (step: Step) => void;
}) {
  const steps = visibleSteps(allowed);
  if (steps.length === 0) return null;
  return (
    <div role="group" aria-label="Review steps" className="flex flex-wrap items-center gap-2">
      {steps.map((step, index) => (
        <button
          key={step}
          type="button"
          className={index === 0 ? PRIMARY : BUTTON}
          disabled={disabled}
          onClick={() => onStep(step)}
        >
          {STEP_LABEL[step]}
        </button>
      ))}
    </div>
  );
}
