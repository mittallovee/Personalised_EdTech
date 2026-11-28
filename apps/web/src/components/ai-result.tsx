"use client";

import { Blocks, QuestionPreview } from "@qbank/content-renderer";
import Link from "next/link";

import {
  OPERATION_NAME,
  SEVERITY,
  answerText,
  applyText,
  canApply,
  correctionOf,
  failureText,
  findingsOf,
  inProgress,
  labelsOf,
  phaseText,
  promptText,
  solutionOf,
  translationOf,
  type Run,
} from "@/lib/ai-run";

const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";
const BOX = "rounded-md border border-zinc-200 p-3 dark:border-zinc-800";

const APPLY_LABEL = {
  SOLVE: "Apply the answer and solution",
  VERIFY: "Apply the correction",
  TRANSLATE: "Create the translation as a new question",
} as const;

/**
 * What one run did: its state, then what the model answered. Everything the model wrote is shown
 * as text or through the shared content renderer, never as markup. A suggestion (an answer, a
 * correction, a translation) shows old and new and waits for an explicit button; the server
 * applies it only to the exact text the run read.
 */
export function RunResult({
  run,
  busy,
  onApply,
  onCancel,
}: {
  run: Run;
  busy: boolean;
  onApply: (run: Run) => void;
  onCancel: (run: Run) => void;
}) {
  const going = inProgress(run);
  return (
    <section
      aria-label={`${OPERATION_NAME[run.operation]} result`}
      className="grid gap-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800"
    >
      <div>
        <h3 className="text-base font-semibold">
          {OPERATION_NAME[run.operation]}
          {run.is_test && (
            <span className="ml-2 rounded bg-zinc-100 px-2 py-0.5 text-xs font-normal dark:bg-zinc-800">
              test
            </span>
          )}
        </h3>
        <p className="text-sm text-zinc-700 dark:text-zinc-300">
          {phaseText(run)}
          {run.answered_by && ` · answered by ${run.answered_by}`} · {promptText(run.prompt_source)}
          {run.mode === "ECONOMY" && " · Economy"}
        </p>
        <p className="text-sm text-zinc-700 dark:text-zinc-300">{applyText(run)}</p>
      </div>

      {going && run.mode === "ECONOMY" && (
        <div className={BOX}>
          <p className="text-sm">
            This is an Economy run. You can keep working: you will be notified when it is done.
          </p>
          {!run.cancel_requested && (
            <button
              type="button"
              className={`${BUTTON} mt-2`}
              disabled={busy}
              onClick={() => onCancel(run)}
            >
              Cancel this run
            </button>
          )}
          {run.cancel_requested && <p className="mt-2 text-sm">Cancel requested.</p>}
        </div>
      )}

      {!going && run.phase !== "SUCCEEDED" && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {failureText(run.error_code)}
        </p>
      )}

      {run.phase === "SUCCEEDED" && <Body run={run} />}

      {canApply(run) && run.operation !== "TAG" && (
        <div>
          <button type="button" className={PRIMARY} disabled={busy} onClick={() => onApply(run)}>
            {busy ? "Working…" : APPLY_LABEL[run.operation]}
          </button>
        </div>
      )}
    </section>
  );
}

function Body({ run }: { run: Run }) {
  switch (run.operation) {
    case "TAG":
      return <TagBody run={run} />;
    case "SOLVE":
      return <SolveBody run={run} />;
    case "VERIFY":
      return <VerifyBody run={run} />;
    case "TRANSLATE":
      return <TranslateBody run={run} />;
  }
}

function TagBody({ run }: { run: Run }) {
  const labels = labelsOf(run);
  if (!labels) return null;
  const { chosen, before } = labels;
  return (
    <div className={BOX}>
      <p className="text-sm">
        {run.apply_status === "APPLIED" ? "Applied" : "Suggested"}: difficulty{" "}
        <strong>{String(chosen["difficulty"] ?? "?")}</strong>, Bloom level{" "}
        <strong>{String(chosen["bloom_level"] ?? "?")}</strong>
        {before["difficulty"] != null && (
          <>
            {" "}
            (was {String(before["difficulty"])}, {String(before["bloom_level"] ?? "none")})
          </>
        )}
        .
      </p>
      <p className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
        {run.apply_status === "APPLIED"
          ? "The chapter, topic and concept were filled in too. You can change any of them in the Edit tab."
          : "The chapter, topic and concept were chosen too, but nothing was written to the question."}
      </p>
    </div>
  );
}

function SolveBody({ run }: { run: Run }) {
  const suggestion = solutionOf(run);
  if (!suggestion) return <p className="text-sm">The result could not be read.</p>;
  const before = run.result?.["before"] as { answer?: unknown; solution?: unknown } | undefined;
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <div className={BOX}>
        <h4 className="text-sm font-medium">Now</h4>
        <p className="mt-1 text-sm">{answerText(before?.answer)}</p>
        <div className="mt-2 text-sm">
          <Blocks blocks={before?.solution} />
        </div>
      </div>
      <div className={BOX}>
        <h4 className="text-sm font-medium">Suggested</h4>
        <p className="mt-1 text-sm">{answerText(suggestion.answer)}</p>
        <div className="mt-2 text-sm">
          <Blocks blocks={suggestion.solution} />
        </div>
      </div>
    </div>
  );
}

function VerifyBody({ run }: { run: Run }) {
  const findings = findingsOf(run);
  const correction = correctionOf(run);
  const before = run.result?.["before"] as { content?: unknown } | undefined;
  if (findings === null) return <p className="text-sm">The result could not be read.</p>;
  return (
    <div className="grid gap-3">
      {findings.length === 0 ? (
        <p className="text-sm text-emerald-800 dark:text-emerald-300">No problems found.</p>
      ) : (
        <ul className="grid gap-1 text-sm">
          {findings.map((finding, index) => (
            <li key={index}>
              <span className={`font-medium ${SEVERITY[finding.severity].className}`}>
                {SEVERITY[finding.severity].label}
              </span>
              {finding.path && (
                <span className="text-zinc-600 dark:text-zinc-400"> ({finding.path})</span>
              )}
              : {finding.message}
            </li>
          ))}
        </ul>
      )}
      {correction && (
        <div className="grid gap-3 md:grid-cols-2">
          <div className={BOX}>
            <h4 className="text-sm font-medium">Now</h4>
            <QuestionPreview content={before?.content} reveal />
          </div>
          <div className={BOX}>
            <h4 className="text-sm font-medium">Corrected</h4>
            <QuestionPreview content={correction} reveal />
          </div>
        </div>
      )}
    </div>
  );
}

function TranslateBody({ run }: { run: Run }) {
  const made = translationOf(run);
  if (!made) return <p className="text-sm">The result could not be read.</p>;
  return (
    <div className="grid gap-3">
      {made.created && (
        <p className="text-sm">
          Created as a new draft:{" "}
          <Link className="underline" href={`/questions/${made.created.id}`}>
            question <span className="font-mono">{made.created.code}</span>
          </Link>
          . The original was not changed.
        </p>
      )}
      <div className={BOX}>
        <h4 className="text-sm font-medium">Translation ({made.language})</h4>
        <QuestionPreview content={made.content} reveal />
      </div>
    </div>
  );
}
