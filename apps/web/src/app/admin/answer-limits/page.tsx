"use client";

import type { components } from "@qbank/api-client";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { api, errorMessage, ifMatch } from "@/lib/api";
import { GROUP_LIST, formFrom, valuesFrom } from "@/lib/answer-limits";
import { canManageCatalogues } from "@/lib/syllabus";
import { useAll } from "@/lib/use-all";
import { NETWORK } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Limits = components["schemas"]["AnswerRulesOut"];
type Exam = components["schemas"]["ExamOut"];
type Card = { examId: string; form: Record<string, string> };

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/**
 * Answer limits (D-03): the numbers that say what an answer may be, for the whole coaching and, if
 * wanted, for one exam. A changed limit never rewrites a saved question; it only changes what the
 * findings say. The API decides who may do this and whether the numbers can be used.
 */
export default function AnswerLimitsPage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();

  if (loadError) {
    return (
      <main className="p-8">
        <p role="alert" className={ALERT}>
          {loadError}
        </p>
        <button type="button" onClick={retry} className="mt-4 underline">
          Try again
        </button>
      </main>
    );
  }
  if (!me) return <main className="p-8">Loading…</main>;

  return (
    <AppShell me={me} current="answer-limits" onSignOut={signOut} onStopActing={stopActing}>
      <h1 className="text-2xl font-semibold">Answer limits</h1>
      <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        What an answer may be: how many items a matching question has, and the range of an integer,
        single-digit or numerical key. A change never rewrites a saved question; it only changes
        what the checks say about it.
      </p>
      {shellError && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <div className="mt-6 max-w-3xl">
        {canManageCatalogues(me) ? (
          <Loader />
        ) : (
          <p role="alert" className={ALERT}>
            Only the Owner and admins may see or change these limits.
          </p>
        )}
      </div>
    </AppShell>
  );
}

function Loader() {
  const [limits, setLimits] = useState<Limits | null>(null);
  const [problem, setProblem] = useState<"denied" | "failed" | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      let result;
      try {
        result = await api().GET("/api/v1/settings/answer-rules");
      } catch {
        if (!cancelled) setProblem("failed");
        return;
      }
      if (cancelled) return;
      if (result.data) setLimits(result.data);
      else setProblem(result.response.status === 403 ? "denied" : "failed");
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  if (problem === "denied") {
    return (
      <p role="alert" className={ALERT}>
        Only the Owner and admins may see or change these limits.
      </p>
    );
  }
  if (problem === "failed") {
    return (
      <p role="alert" className={ALERT}>
        The limits could not be loaded.{" "}
        <button
          type="button"
          className="underline"
          onClick={() => {
            setProblem(null);
            setAttempt((n) => n + 1);
          }}
        >
          Try again
        </button>
      </p>
    );
  }
  if (!limits) return <p>Loading…</p>;
  return <Editor key={limits.revision} initial={limits} reload={() => setAttempt((n) => n + 1)} />;
}

function cardsOf(limits: Limits): Card[] {
  return limits.exams.map((exam) => ({ examId: exam.exam_id, form: formFrom(exam.values) }));
}

function Editor({ initial, reload }: { initial: Limits; reload: () => void }) {
  const [revision, setRevision] = useState(initial.revision);
  const [coaching, setCoaching] = useState(() => formFrom(initial.defaults, initial.built_in));
  const [cards, setCards] = useState<Card[]>(() => cardsOf(initial));
  const [problems, setProblems] = useState<Record<string, string>>({});
  const [general, setGeneral] = useState<string[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const [busy, setBusy] = useState(false);

  const fetchExams = useCallback(
    (cursor: string | null) =>
      api().GET("/api/v1/exams", {
        params: { query: { limit: 100, cursor: cursor ?? undefined } },
      }),
    [],
  );
  const exams = useAll<Exam>("exams", fetchExams);
  const nameOf = (id: string) => exams.items.find((exam) => exam.id === id)?.name ?? "An exam";
  const free = exams.items.filter((exam) => !cards.some((card) => card.examId === exam.id));

  async function save() {
    if (busy) return;
    const found: Record<string, string> = {};
    const mine = valuesFrom(coaching, initial.built_in);
    for (const [name, message] of Object.entries(mine.problems))
      found[`defaults.${name}`] = message;
    const examValues: Record<string, Record<string, number | string>> = {};
    for (const card of cards) {
      const layer = valuesFrom(card.form);
      for (const [name, message] of Object.entries(layer.problems)) {
        found[`exams.${card.examId}.${name}`] = message;
      }
      examValues[card.examId] = layer.values;
    }
    setProblems(found);
    setGeneral([]);
    setNotice(null);
    setStale(false);
    if (Object.keys(found).length > 0) return;

    setBusy(true);
    try {
      const { data, error, response } = await api().PUT("/api/v1/settings/answer-rules", {
        params: { header: { "If-Match": ifMatch(revision) } },
        body: { defaults: mine.values, exams: examValues },
      });
      if (data) {
        setRevision(data.revision);
        setCoaching(formFrom(data.defaults, data.built_in));
        setCards(cardsOf(data));
        setNotice("Saved. The checks use these limits from now on.");
      } else if (response.status === 412) {
        setStale(true);
      } else if (response.status === 422) {
        const details = (error as { error?: { details?: { problems?: unknown } } } | undefined)
          ?.error?.details?.problems;
        const listed = Array.isArray(details)
          ? (details as { path: string; message: string }[])
          : [];
        const byField: Record<string, string> = {};
        const others: string[] = [];
        for (const item of listed) {
          if (/^(defaults|exams\.[^.]+)\.[a-z_]+$/.test(item.path))
            byField[item.path] = item.message;
          else
            others.push(
              `${item.path === "defaults" ? "The coaching" : "An exam"}: ${item.message}`,
            );
        }
        setProblems(byField);
        setGeneral(others.length > 0 ? others : ["Some of these limits cannot be used."]);
      } else {
        setGeneral([errorMessage(error as never, response.status)]);
      }
    } catch {
      setGeneral([NETWORK]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      aria-label="Answer limits"
      className="grid gap-8"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <LimitsFields
        title="For the whole coaching"
        scope="Coaching"
        form={coaching}
        onChange={setCoaching}
        problems={problems}
        prefix="defaults."
        bounds={initial.bounds}
        disabled={busy}
      />

      <section aria-label="Limits for one exam" className="grid gap-4">
        <div>
          <h2 className="text-lg font-medium">For one exam</h2>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            A question labelled with the exam uses these limits instead. Leave a box empty to keep
            the coaching&apos;s value.
          </p>
        </div>
        {cards.map((card) => (
          <div
            key={card.examId}
            className="grid gap-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800"
          >
            <LimitsFields
              title={nameOf(card.examId)}
              scope={nameOf(card.examId)}
              form={card.form}
              onChange={(next) =>
                setCards((current) =>
                  current.map((c) => (c.examId === card.examId ? { ...c, form: next } : c)),
                )
              }
              problems={problems}
              prefix={`exams.${card.examId}.`}
              placeholders={coaching}
              bounds={initial.bounds}
              disabled={busy}
            />
            <div>
              <button
                type="button"
                className={BUTTON}
                disabled={busy}
                onClick={() =>
                  setCards((current) => current.filter((c) => c.examId !== card.examId))
                }
              >
                Remove the limits for {nameOf(card.examId)}
              </button>
            </div>
          </div>
        ))}
        {exams.failed && (
          <p role="alert" className={ALERT}>
            The exams could not be loaded.
          </p>
        )}
        <label className="grid max-w-sm gap-1 text-sm">
          <span>Add limits for an exam</span>
          <select
            value=""
            disabled={busy || exams.loading || free.length === 0}
            className={FIELD}
            onChange={(event) => {
              if (event.target.value) {
                setCards((current) => [
                  ...current,
                  { examId: event.target.value, form: formFrom({}) },
                ]);
              }
            }}
          >
            <option value="">
              {free.length === 0 && !exams.loading ? "No other exams" : "Choose an exam…"}
            </option>
            {free.map((exam) => (
              <option key={exam.id} value={exam.id}>
                {exam.name}
                {exam.state === "DEPRECATED" ? " (retired)" : ""}
              </option>
            ))}
          </select>
        </label>
      </section>

      {stale && (
        <p role="alert" className={ALERT}>
          Someone else changed these limits. Reload to see their version; your edits here were not
          saved.{" "}
          <button type="button" className="underline" onClick={reload}>
            Reload
          </button>
        </p>
      )}
      {general.length > 0 && (
        <ul role="alert" className={`grid gap-1 ${ALERT}`}>
          {general.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}
      {notice && (
        <p
          role="status"
          className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
        >
          {notice}
        </p>
      )}
      <div>
        <button type="submit" disabled={busy} className={PRIMARY}>
          {busy ? "Saving…" : "Save limits"}
        </button>
      </div>
    </form>
  );
}

/** One set of the ten numbers, in groups. */
function LimitsFields({
  title,
  scope,
  form,
  onChange,
  problems,
  prefix,
  placeholders,
  bounds,
  disabled,
}: {
  title: string;
  scope: string;
  form: Record<string, string>;
  onChange: (next: Record<string, string>) => void;
  problems: Record<string, string>;
  prefix: string;
  placeholders?: Record<string, string>;
  bounds: Limits["bounds"];
  disabled: boolean;
}) {
  return (
    <section aria-label={`Limits: ${scope}`} className="grid gap-4">
      <h2 className="text-lg font-medium">{title}</h2>
      {GROUP_LIST.map((group) => (
        <fieldset key={group.title} disabled={disabled} className="grid gap-2">
          <legend className="mb-1 text-sm font-medium">{group.title}</legend>
          <div className="grid gap-3 sm:grid-cols-2">
            {group.settings.map((setting) => {
              const message = problems[`${prefix}${setting.name}`];
              const limit = bounds[setting.name];
              return (
                <label key={setting.name} className="grid gap-1 text-sm">
                  <span>{setting.label}</span>
                  <input
                    type="text"
                    inputMode={setting.kind === "int" ? "numeric" : "decimal"}
                    value={form[setting.name] ?? ""}
                    placeholder={placeholders?.[setting.name] ?? ""}
                    aria-label={`${scope}, ${group.title}: ${setting.label}`}
                    aria-invalid={message ? true : undefined}
                    aria-describedby={message ? `err-${prefix}${setting.name}` : undefined}
                    className={FIELD}
                    onChange={(event) => onChange({ ...form, [setting.name]: event.target.value })}
                  />
                  {limit && (
                    <span className="text-xs text-zinc-600 dark:text-zinc-400">
                      From {limit.low} to {limit.high}
                    </span>
                  )}
                  {message && (
                    <span
                      id={`err-${prefix}${setting.name}`}
                      className="text-xs text-red-700 dark:text-red-300"
                    >
                      {message}
                    </span>
                  )}
                </label>
              );
            })}
          </div>
        </fieldset>
      ))}
    </section>
  );
}
