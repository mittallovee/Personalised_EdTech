"use client";

import type { components } from "@qbank/api-client";
import { useEffect, useRef, useState } from "react";

import { OPERATIONS, OPERATION_LABEL, type Mode, type Operation } from "@/lib/ai-admin";
import { isWaiting, type Run } from "@/lib/ai-runs";
import { api, errorMessage } from "@/lib/api";
import { formatInr } from "@/lib/ai-admin";
import { NETWORK } from "@/lib/use-catalogue";

import { AiRunCard } from "./ai-run-card";

type Language = components["schemas"]["LanguageOut"];
type Template = components["schemas"]["TemplateOut"];
type Usage = components["schemas"]["UsageOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

const BLURB: Record<Operation, string> = {
  TAG: "Chooses the chapter, topic, main concept, difficulty and Bloom level from your coaching's own syllabus and fills them in. You can change them afterwards. The subject must be chosen first.",
  TRANSLATE:
    "Translates this question into another language as a new draft question linked to this one. This question is not changed.",
  SOLVE: "Suggests an answer and a worked solution. Nothing is changed until you apply it.",
  VERIFY:
    "Checks the question and lists what looks wrong. If the model is sure how to fix it, it also offers a correction, which you apply yourself.",
};

const STATE_TEXT: Record<string, string> = {
  OK: "within your budget",
  WARNING: "above 80% of your budget",
  REACHED: "your budget is used up",
  NO_LIMIT: "no limit set",
  OFF: "budgets are off (no rate set)",
};

/**
 * The AI tab of a question: ask for one of the four operations, see what each run did, apply a
 * suggestion, and cancel an Economy run that is still waiting. The server decides whether the run
 * may happen (permission, budget, model, key); this tab shows its answer in words. Typing is saved
 * first, because a run reads the saved question, and a run that changes the question makes the
 * editor read it again.
 */
export function AiPanel({
  questionId,
  editable,
  beforeRun,
  onApplied,
}: {
  questionId: string;
  editable: boolean;
  beforeRun: () => Promise<boolean>;
  onApplied: () => void;
}) {
  const [operation, setOperation] = useState<Operation>("TAG");
  const [mode, setMode] = useState<Mode | "">("");
  const [language, setLanguage] = useState("");
  const [extra, setExtra] = useState("");
  const [promptChoice, setPromptChoice] = useState("default");
  const [oneOff, setOneOff] = useState("");
  const [test, setTest] = useState(false);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [mine, setMine] = useState<Template[]>([]);
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [names, setNames] = useState<Record<string, string>>({});
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const asked = useRef(new Set<string>());
  const waiting = runs?.some(isWaiting) ?? false;

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [list, langs, prompts, used] = await Promise.all([
          api().GET("/api/v1/questions/{question_id}/ai/runs", {
            params: { path: { question_id: questionId } },
          }),
          api().GET("/api/v1/languages"),
          api().GET("/api/v1/ai/prompts"),
          api().GET("/api/v1/ai/usage/me"),
        ]);
        if (cancelled) return;
        if (list.data) setRuns(list.data.data);
        else setProblem(errorMessage(list.error as never, list.response.status));
        if (langs.data) setLanguages(langs.data);
        if (prompts.data) setMine(prompts.data.data.filter((item) => item.scope === "PERSONAL"));
        if (used.data) setUsage(used.data);
      } catch {
        if (!cancelled) setProblem(NETWORK);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [questionId, attempt]);

  // A run waiting for its batch is asked about every 15 seconds, so the answer appears by itself.
  useEffect(() => {
    if (!waiting) return;
    const timer = window.setInterval(() => setAttempt((n) => n + 1), 15000);
    return () => window.clearInterval(timer);
  }, [waiting]);

  // The names of the syllabus items a tagging run chose, looked up once each.
  useEffect(() => {
    const wanted: string[] = [];
    for (const run of runs ?? []) {
      const output = run.result?.output as Record<string, unknown> | undefined;
      for (const key of ["chapter_id", "topic_id", "primary_concept_id"]) {
        const value = output?.[key];
        if (typeof value === "string" && !asked.current.has(value)) wanted.push(value);
      }
    }
    if (wanted.length === 0) return;
    let cancelled = false;
    async function lookUp() {
      for (const id of wanted) {
        asked.current.add(id);
        try {
          const node = await api().GET("/api/v1/taxonomy/nodes/{node_id}", {
            params: { path: { node_id: id } },
          });
          const found = node.data
            ? node.data.name
            : (
                await api().GET("/api/v1/taxonomy/concepts/{concept_id}", {
                  params: { path: { concept_id: id } },
                })
              ).data?.name;
          if (!cancelled && found) setNames((current) => ({ ...current, [id]: found }));
        } catch {
          // The id is shown as it is; the names are a convenience.
        }
      }
    }
    void lookUp();
    return () => {
      cancelled = true;
    };
  }, [runs]);

  const personal = mine.filter((item) => item.operation === operation);

  async function run() {
    if (busy) return;
    setProblem(null);
    if (operation === "TRANSLATE" && language === "") {
      setProblem("Choose the language to translate into.");
      return;
    }
    if (promptChoice === "one-off" && oneOff.trim() === "") {
      setProblem("Write the prompt for this run, or choose another.");
      return;
    }
    setBusy(true);
    try {
      if (!(await beforeRun())) {
        setProblem("Your changes could not be saved yet, so nothing was run.");
        return;
      }
      const { data, error, response } = await api().POST(
        "/api/v1/questions/{question_id}/ai/runs",
        {
          params: { path: { question_id: questionId } },
          body: {
            operation,
            mode: mode === "" ? null : mode,
            target_language: operation === "TRANSLATE" ? language : null,
            extra_instructions: extra.trim() === "" ? null : extra,
            prompt: promptChoice === "one-off" ? oneOff : null,
            personal_prompt_id:
              promptChoice !== "default" && promptChoice !== "one-off" ? promptChoice : null,
            test,
          },
        },
      );
      if (data) {
        setAttempt((n) => n + 1);
        if (data.apply_status === "APPLIED") onApplied();
      } else {
        setProblem(errorMessage(error as never, response.status));
      }
    } catch {
      setProblem(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-5">
      <form
        aria-label="Ask the AI"
        className="grid gap-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800"
        onSubmit={(event) => {
          event.preventDefault();
          void run();
        }}
      >
        <label className="grid gap-1 text-sm">
          What should the AI do?
          <select
            value={operation}
            onChange={(event) => {
              setOperation(event.target.value as Operation);
              setPromptChoice("default");
            }}
            className={FIELD}
          >
            {OPERATIONS.map((item) => (
              <option key={item} value={item}>
                {OPERATION_LABEL[item]}
              </option>
            ))}
          </select>
        </label>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">{BLURB[operation]}</p>
        {operation === "TRANSLATE" && (
          <label className="grid gap-1 text-sm">
            Translate into
            <select
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
              className={FIELD}
            >
              <option value="">Choose…</option>
              {languages.map((item) => (
                <option key={item.tag} value={item.tag}>
                  {item.english_name}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="grid gap-1 text-sm">
          Prompt
          <select
            value={promptChoice}
            onChange={(event) => setPromptChoice(event.target.value)}
            className={FIELD}
          >
            <option value="default">
              The one in use (your coaching&apos;s or the platform&apos;s)
            </option>
            {personal.map((item) => (
              <option key={item.id} value={item.id}>
                My prompt: {item.name}
              </option>
            ))}
            <option value="one-off">Write one for this run only</option>
          </select>
        </label>
        {promptChoice === "one-off" && (
          <label className="grid gap-1 text-sm">
            Prompt for this run
            <textarea
              value={oneOff}
              onChange={(event) => setOneOff(event.target.value)}
              rows={6}
              className={`${FIELD} font-mono text-sm`}
            />
            <span className="text-xs text-zinc-600 dark:text-zinc-400">
              It must use the places for data the library lists for this operation. It is kept on
              the run only.
            </span>
          </label>
        )}
        <label className="grid gap-1 text-sm">
          Extra instructions (optional)
          <input
            value={extra}
            maxLength={1000}
            onChange={(event) => setExtra(event.target.value)}
            className={FIELD}
          />
        </label>
        <label className="grid gap-1 text-sm sm:max-w-xs">
          Price
          <select
            value={mode}
            onChange={(event) => setMode(event.target.value as Mode | "")}
            className={FIELD}
          >
            <option value="">The default for this operation</option>
            <option value="NOW">Now (normal price)</option>
            <option value="ECONOMY">Economy (about half price, done within 24 hours)</option>
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={test}
            onChange={(event) => setTest(event.target.checked)}
          />
          Test only: show me the result but never change the question
        </label>
        {!editable && !test && operation !== "TRANSLATE" && (
          <p className="text-sm text-amber-700 dark:text-amber-400">
            This question cannot be edited now, so a real run is refused. Tick the test box, or
            withdraw the question first.
          </p>
        )}
        {usage && (
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            This month you have used {formatInr(usage.spent_inr)}
            {usage.limit_inr !== null && ` of ${formatInr(usage.limit_inr)}`} (
            {STATE_TEXT[usage.state] ?? usage.state}). A run is refused if it would pass your
            budget.
          </p>
        )}
        {problem && (
          <p role="alert" className={ALERT}>
            {problem}
          </p>
        )}
        <div>
          <button type="submit" disabled={busy} className={PRIMARY}>
            {busy ? "Working…" : "Run"}
          </button>
        </div>
      </form>

      <section aria-label="AI history" className="grid gap-2">
        <h2 className="text-lg font-medium">History of this question</h2>
        {!runs && <p>Loading…</p>}
        {runs && runs.length === 0 && <p className="text-sm">No AI runs on this question yet.</p>}
        {runs && runs.length > 0 && (
          <ul className="grid gap-3">
            {runs.map((item) => (
              <AiRunCard
                key={item.id}
                run={item}
                names={names}
                onChanged={(applied) => {
                  setAttempt((n) => n + 1);
                  if (applied) onApplied();
                }}
              />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
