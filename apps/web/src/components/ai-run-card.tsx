"use client";

import { QuestionPreview } from "@qbank/content-renderer";
import Link from "next/link";
import { useState } from "react";

import { OPERATION_LABEL } from "@/lib/ai-admin";
import {
  APPLY_TEXT,
  answerText,
  changedParts,
  errorText,
  findingsOf,
  isWaiting,
  phaseText,
  solutionText,
  type Run,
} from "@/lib/ai-runs";
import { api, errorMessage } from "@/lib/api";
import { NETWORK } from "@/lib/use-catalogue";

type Output = Record<string, unknown>;

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const NOTE =
  "rounded-md bg-zinc-50 px-3 py-2 text-sm text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/**
 * One AI run on a question: what it was, how it ended, and what it suggests. A suggestion
 * (an answer, a correction, a translation) is shown beside what it would replace and applied only
 * by a click here. Everything the model wrote is shown as text, never as markup. Whether a run may
 * be applied or cancelled is the API's decision; this card only offers the buttons that fit.
 */
export function AiRunCard({
  run,
  names,
  onChanged,
}: {
  run: Run;
  names: Record<string, string>;
  onChanged: (applied: boolean) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const output = (run.result?.output ?? null) as Output | null;
  const before = (run.result?.before ?? null) as Output | null;
  const failure = errorText(run.error_code);
  const created = output?.created_question as { id: string; code: string } | undefined;
  const canApply =
    run.status === "SUCCEEDED" &&
    run.apply_status === "NOT_APPLIED" &&
    !run.is_test &&
    output !== null &&
    (run.operation === "SOLVE" ||
      run.operation === "TRANSLATE" ||
      (run.operation === "VERIFY" && output.corrected_content !== undefined));
  const canCancel =
    run.mode === "ECONOMY" &&
    !run.cancel_requested &&
    ["QUEUED", "SUBMITTING", "SUBMITTED"].includes(run.phase);

  async function send(path: "apply" | "cancel") {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    try {
      const params = { path: { run_id: run.id } };
      const { data, error, response } =
        path === "apply"
          ? await api().POST("/api/v1/ai/runs/{run_id}/apply", { params })
          : await api().POST("/api/v1/ai/runs/{run_id}/cancel", { params });
      if (data) onChanged(path === "apply" && data.apply_status === "APPLIED");
      else setProblem(errorMessage(error as never, response.status));
    } catch {
      setProblem(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="grid gap-2 rounded-md border border-zinc-200 p-3 text-sm dark:border-zinc-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium">
          {OPERATION_LABEL[run.operation]}
          {run.is_test && " (test)"}
          {run.mode === "ECONOMY" && " · Economy"}
        </p>
        <p className="text-zinc-600 dark:text-zinc-400">
          {phaseText(run.phase)} · {new Date(run.started_at).toLocaleString()}
          {run.answered_by && ` · ${run.answered_by}`}
        </p>
      </div>
      {isWaiting(run) && run.cancel_requested && (
        <p className={NOTE}>Cancelling: whatever arrives will not be applied.</p>
      )}
      {failure && (
        <p role="alert" className={ALERT}>
          {failure}
        </p>
      )}
      {run.attempts.length > 1 && (
        <p className="text-zinc-600 dark:text-zinc-400">
          Tried {run.attempts.map((a) => `${a.model} (${a.outcome})`).join(", then ")}.
        </p>
      )}
      {output && run.operation === "TAG" && (
        <TagResult output={output} before={before} names={names} />
      )}
      {output && run.operation === "SOLVE" && <SolveResult output={output} before={before} />}
      {output && run.operation === "VERIFY" && <VerifyResult output={output} before={before} />}
      {output && run.operation === "TRANSLATE" && <TranslateResult output={output} />}
      {run.status === "SUCCEEDED" && (
        <p className="text-zinc-700 dark:text-zinc-300">
          {run.is_test ? "Test run: nothing was changed." : APPLY_TEXT[run.apply_status]}.
          {created && (
            <>
              {" "}
              <Link href={`/questions/${created.id}`} className="underline">
                Open the translation {created.code}
              </Link>
            </>
          )}
        </p>
      )}
      {problem && (
        <p role="alert" className={ALERT}>
          {problem}
        </p>
      )}
      {(canApply || canCancel) && (
        <div className="flex flex-wrap gap-2">
          {canApply && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void send("apply")}
              className={PRIMARY}
            >
              {run.operation === "SOLVE"
                ? "Apply the answer and solution"
                : run.operation === "VERIFY"
                  ? "Apply the correction"
                  : "Create the translation"}
            </button>
          )}
          {canCancel && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void send("cancel")}
              className={BUTTON}
            >
              Cancel this run
            </button>
          )}
        </div>
      )}
    </li>
  );
}

function TagResult({
  output,
  before,
  names,
}: {
  output: Output;
  before: Output | null;
  names: Record<string, string>;
}) {
  const rows: [string, string][] = [
    ["Chapter", "chapter_id"],
    ["Topic", "topic_id"],
    ["Main concept", "primary_concept_id"],
    ["Difficulty", "difficulty"],
    ["Bloom level", "bloom_level"],
  ];
  const show = (value: unknown) =>
    value === null || value === undefined ? "not set" : (names[String(value)] ?? String(value));
  return (
    <dl className="grid gap-1 sm:grid-cols-2">
      {rows.map(([label, key]) =>
        output[key] === undefined ? null : (
          <div key={key} className="flex gap-2">
            <dt className="text-zinc-600 dark:text-zinc-400">{label}:</dt>
            <dd>
              {show(output[key])}
              {before && String(before[key] ?? "") !== String(output[key]) && (
                <span className="text-zinc-600 dark:text-zinc-400"> (was {show(before[key])})</span>
              )}
            </dd>
          </div>
        ),
      )}
    </dl>
  );
}

function SolveResult({ output, before }: { output: Output; before: Output | null }) {
  return (
    <div className="grid gap-2">
      <p>
        Suggested answer: <strong>{answerText(output.answer)}</strong>
        {before && ` (now: ${answerText(before.answer)})`}
      </p>
      <p className="whitespace-pre-wrap rounded-md bg-zinc-50 p-2 dark:bg-zinc-900">
        {solutionText(output.solution)}
      </p>
    </div>
  );
}

function VerifyResult({ output, before }: { output: Output; before: Output | null }) {
  const findings = findingsOf(output);
  const corrected = output.corrected_content as Record<string, unknown> | undefined;
  const original = (before?.content ?? null) as Record<string, unknown> | null;
  const parts = corrected && original ? changedParts(original, corrected) : [];
  return (
    <div className="grid gap-2">
      {findings.length === 0 ? (
        <p>The model found nothing to report.</p>
      ) : (
        <ul className="grid gap-1">
          {findings.map((finding, index) => (
            <li key={index} className="flex gap-2">
              <span
                className={
                  finding.severity === "error"
                    ? "font-medium text-red-700 dark:text-red-300"
                    : finding.severity === "warning"
                      ? "font-medium text-amber-700 dark:text-amber-300"
                      : "text-zinc-600 dark:text-zinc-400"
                }
              >
                {finding.severity}
              </span>
              <span>
                <span className="font-mono text-xs">{finding.path}</span> {finding.message}
              </span>
            </li>
          ))}
        </ul>
      )}
      {corrected && (
        <details className="rounded-md border border-zinc-200 p-2 dark:border-zinc-800">
          <summary className="cursor-pointer">
            A corrected version is offered
            {parts.length > 0 && `: it changes ${parts.join(", ")}`}
          </summary>
          <div className="mt-2 grid gap-3 sm:grid-cols-2">
            {original && (
              <div>
                <p className="mb-1 font-medium">Now</p>
                <QuestionPreview content={original} reveal />
              </div>
            )}
            <div>
              <p className="mb-1 font-medium">Corrected</p>
              <QuestionPreview content={corrected} reveal />
            </div>
          </div>
        </details>
      )}
    </div>
  );
}

function TranslateResult({ output }: { output: Output }) {
  const content = output.content as Record<string, unknown> | undefined;
  if (!content) return null;
  return (
    <details className="rounded-md border border-zinc-200 p-2 dark:border-zinc-800">
      <summary className="cursor-pointer">The translation ({String(output.language)})</summary>
      <div className="mt-2">
        <QuestionPreview content={content} reveal />
      </div>
    </details>
  );
}
