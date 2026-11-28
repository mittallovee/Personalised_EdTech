"use client";

import type { components, ErrorResponse } from "@qbank/api-client";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import {
  ACTIONS,
  OPERATION_NAME,
  applyText,
  inProgress,
  noticeWrites,
  phaseText,
  problemsOf,
  type Run,
  type RunOptions,
  type Usage,
} from "@/lib/ai-run";
import { NETWORK } from "@/lib/use-catalogue";

import { RunForm } from "./ai-run-form";
import { RunResult } from "./ai-result";

type Operation = components["schemas"]["Operation"];
type StartRun = components["schemas"]["StartRun"];
type Language = components["schemas"]["LanguageOut"];
type Template = components["schemas"]["TemplateOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const POLL_MS = 5000;

/** The server's sentence, and for a prompt it cannot use, what is wrong with it. */
function refused(error: unknown, status: number): string {
  const found = error as ErrorResponse | undefined;
  return [errorMessage(found, status), ...problemsOf(found)].join(" ");
}

type Loaded = {
  options: RunOptions;
  usage: Usage | null;
  personal: Template[];
  languages: Language[];
};

/**
 * AI on one question (H-07 to H-10): the four operations, the run form, what the last run said,
 * and the question's AI history (the person's own runs; an admin sees everyone's). The editor
 * hands over four things: `prepare` (save what is typed, because a run reads the saved text),
 * `onQuestionChanged` (the server changed the question, so load it again), `onChangedInBackground`
 * (it did so later, from an Economy run, so typing in progress must not be thrown away), and `onWorking`
 * (keep the text still while a run is going, so nothing typed can be replaced by the answer).
 */
export function AiPanel({
  questionId,
  myId,
  sourceLanguage,
  editable,
  prepare,
  onQuestionChanged,
  onChangedInBackground,
  onWorking,
}: {
  questionId: string;
  myId: string;
  sourceLanguage: string | null;
  editable: boolean;
  prepare: () => Promise<boolean>;
  onQuestionChanged: () => Promise<void>;
  /** A run the person started earlier has written to the question while they did something else. */
  onChangedInBackground: () => void;
  onWorking: (working: boolean) => void;
}) {
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [runs, setRuns] = useState<Run[]>([]);
  const [choosing, setChoosing] = useState<Operation | null>(null);
  const [shownId, setShownId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  // What each run's state was at the last look, to notice a background run that has just written
  // to the question (an Economy tagging run): the screen's copy of the question is then stale.
  const seen = useRef<Map<string, string>>(new Map());
  // The latest `onQuestionChanged`, so a new copy of it (the editor makes one on every change) does
  // not make the panel read everything again.
  const changed = useRef(onQuestionChanged);
  const background = useRef(onChangedInBackground);
  useEffect(() => {
    changed.current = onQuestionChanged;
    background.current = onChangedInBackground;
  });

  const refreshRuns = useCallback(async () => {
    try {
      const { data } = await api().GET("/api/v1/questions/{question_id}/ai/runs", {
        params: { path: { question_id: questionId } },
      });
      if (!data) return;
      const { written, next } = noticeWrites(seen.current, data.data);
      seen.current = next;
      setRuns(data.data);
      if (written) background.current();
    } catch {
      // The list is only a convenience; the next look tries again.
    }
  }, [questionId]);

  const refreshUsage = useCallback(async () => {
    try {
      const { data } = await api().GET("/api/v1/ai/usage/me");
      if (data) setLoaded((now) => (now ? { ...now, usage: data } : now));
    } catch {
      // The budget line is a convenience; a run is checked by the server whatever it shows.
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      void refreshRuns();
      try {
        const [options, usage, prompts, languages] = await Promise.all([
          api().GET("/api/v1/ai/options"),
          api().GET("/api/v1/ai/usage/me"),
          api().GET("/api/v1/ai/prompts", { params: { query: { scope: "PERSONAL" } } }),
          api().GET("/api/v1/languages"),
        ]);
        if (cancelled) return;
        if (!options.data) {
          setLoadError(errorMessage(options.error as never, options.response.status));
          return;
        }
        setLoaded({
          options: options.data,
          usage: usage.data ?? null,
          personal: (prompts.data?.data ?? []).filter((entry) => entry.owner_user_id === myId),
          languages: languages.data ?? [],
        });
      } catch {
        if (!cancelled) setLoadError(NETWORK);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [myId, attempt, refreshRuns]);

  const anyGoing = runs.some(inProgress);
  useEffect(() => {
    if (!anyGoing) return;
    const timer = setInterval(() => void refreshRuns(), POLL_MS);
    return () => clearInterval(timer);
  }, [anyGoing, refreshRuns]);

  /** Run something that reads or changes the question: save first, keep the text still meanwhile. */
  async function working(work: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    onWorking(true);
    setMessage(null);
    try {
      if (!(await prepare())) {
        setMessage("Your changes could not be saved yet, so nothing was done.");
        return;
      }
      await work();
    } catch {
      setMessage(NETWORK);
    } finally {
      setBusy(false);
      onWorking(false);
    }
  }

  const shown = runs.find((run) => run.id === shownId) ?? null;

  function remember(run: Run) {
    seen.current.set(run.id, run.apply_status);
    setShownId(run.id);
    setRuns((now) => [run, ...now.filter((entry) => entry.id !== run.id)]);
  }

  function start(body: StartRun) {
    void working(async () => {
      const { data, error, response } = await api().POST(
        "/api/v1/questions/{question_id}/ai/runs",
        { params: { path: { question_id: questionId } }, body },
      );
      if (!data) {
        setMessage(refused(error, response.status));
        return;
      }
      remember(data);
      setChoosing(null);
      void refreshUsage();
      if (data.apply_status === "APPLIED") await changed.current();
    });
  }

  function apply(run: Run) {
    void working(async () => {
      const { data, error, response } = await api().POST("/api/v1/ai/runs/{run_id}/apply", {
        params: { path: { run_id: run.id } },
      });
      if (!data) {
        setMessage(refused(error, response.status));
        return;
      }
      remember(data);
      // A translation makes a new question; the others changed this one.
      if (data.apply_status === "APPLIED" && data.operation !== "TRANSLATE") {
        await changed.current();
      }
    });
  }

  function cancel(run: Run) {
    void (async () => {
      setMessage(null);
      try {
        const { data, error, response } = await api().POST("/api/v1/ai/runs/{run_id}/cancel", {
          params: { path: { run_id: run.id } },
        });
        if (data) remember(data);
        else setMessage(refused(error, response.status));
      } catch {
        setMessage(NETWORK);
      }
    })();
  }

  if (loadError) {
    return (
      <div className="grid gap-2">
        <p role="alert" className={ALERT}>
          {loadError}
        </p>
        <button
          type="button"
          className="justify-self-start underline"
          onClick={() => {
            setLoadError(null);
            setAttempt((n) => n + 1);
          }}
        >
          Try again
        </button>
      </div>
    );
  }
  if (!loaded) return <p>Loading…</p>;

  return (
    <div className="grid gap-4">
      <div role="group" aria-label="AI actions" className="flex flex-wrap gap-2">
        {ACTIONS.map(({ operation, label, hint }) => (
          <button
            key={operation}
            type="button"
            title={hint}
            aria-pressed={choosing === operation}
            className={BUTTON}
            disabled={busy}
            onClick={() => {
              setMessage(null);
              setChoosing(choosing === operation ? null : operation);
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {message && (
        <p role="alert" className={ALERT}>
          {message}
        </p>
      )}

      {choosing && (
        <RunForm
          key={choosing}
          operation={choosing}
          options={loaded.options}
          usage={loaded.usage}
          personal={loaded.personal.filter((entry) => entry.operation === choosing)}
          languages={loaded.languages}
          sourceLanguage={sourceLanguage}
          editable={editable}
          busy={busy}
          onRun={start}
          onCancel={() => setChoosing(null)}
        />
      )}

      {shown && <RunResult run={shown} busy={busy} onApply={apply} onCancel={cancel} />}

      <section aria-label="AI history">
        <h3 className="text-base font-semibold">AI history</h3>
        {runs.length === 0 ? (
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
            Nothing has been run on this question yet.
          </p>
        ) : (
          <ul className="mt-2 grid gap-1">
            {runs.map((run) => (
              <li key={run.id}>
                <button
                  type="button"
                  aria-current={run.id === shownId ? "true" : undefined}
                  className={`w-full rounded-md px-3 py-2 text-left text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900 ${
                    run.id === shownId ? "bg-zinc-100 dark:bg-zinc-800" : ""
                  }`}
                  onClick={() => setShownId(run.id)}
                >
                  <span className="font-medium">{OPERATION_NAME[run.operation]}</span>
                  {run.is_test && " (test)"} · {new Date(run.started_at).toLocaleString()} ·{" "}
                  {phaseText(run)} · {applyText(run)}
                  {run.requested_by !== myId && " · by a colleague"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
