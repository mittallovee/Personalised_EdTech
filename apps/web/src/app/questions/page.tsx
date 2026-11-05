"use client";

import type { components } from "@qbank/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";
import { FORMATS, emptyContent, formatLabel } from "@/lib/question-content";
import { useAdd, useCatalogueList } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Summary = components["schemas"]["QuestionSummary"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/**
 * Questions (D-11): the ones you may open, newest first, and a way to start a new one. Every
 * question gets its permanent code when it is started; a draft with gaps is saved and the editor
 * says what is missing. The API decides who sees what: your own drafts, or all of them for admins
 * and people who may edit others' drafts.
 */
export default function QuestionsPage() {
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
    <AppShell me={me} current="questions" onSignOut={signOut} onStopActing={stopActing}>
      <h1 className="text-2xl font-semibold">Questions</h1>
      {shellError && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <div className="mt-6 grid max-w-3xl gap-10">
        <NewQuestion />
        <QuestionList />
      </div>
    </AppShell>
  );
}

function NewQuestion() {
  const router = useRouter();
  const [type, setType] = useState("SCQ");
  const adder = useAdd<components["schemas"]["QuestionOut"]>(
    (body, key) =>
      api().POST("/api/v1/questions", {
        body: body as components["schemas"]["CreateQuestion"],
        params: { header: { "Idempotency-Key": key } },
      }),
    (created) => router.push(`/questions/${created.id}`),
  );

  return (
    <form
      aria-label="Start a question"
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        void adder.add({ content: emptyContent(type) });
      }}
    >
      <fieldset className="grid gap-2">
        <legend className="mb-1 text-lg font-medium">Start a new question</legend>
        {FORMATS.map((format) => (
          <label key={format.value} className="flex items-start gap-2 text-sm">
            <input
              type="radio"
              name="format"
              value={format.value}
              checked={type === format.value}
              onChange={() => setType(format.value)}
              className="mt-1"
            />
            <span>
              <span className="font-medium">{format.label}</span>
              <span className="block text-zinc-600 dark:text-zinc-400">{format.hint}</span>
            </span>
          </label>
        ))}
      </fieldset>
      {adder.addError && (
        <p role="alert" className={ALERT}>
          {adder.addError}
        </p>
      )}
      <div>
        <button type="submit" disabled={adder.adding} className={PRIMARY}>
          {adder.adding ? "Starting…" : "Start question"}
        </button>
      </div>
    </form>
  );
}

function QuestionList() {
  const [mine, setMine] = useState(false);
  const [archived, setArchived] = useState(false);
  const fetchPage = useCallback(
    (cursor: string | null) =>
      api().GET("/api/v1/questions", {
        params: { query: { mine, archived, limit: 25, cursor: cursor ?? undefined } },
      }),
    [mine, archived],
  );
  const list = useCatalogueList<Summary>(fetchPage);

  return (
    <section aria-label="Your questions" className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-medium">{archived ? "Archived questions" : "Questions"}</h2>
        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} />
            Only mine
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={archived}
              onChange={(e) => setArchived(e.target.checked)}
            />
            Archived
          </label>
        </div>
      </div>
      {list.state === "loading" && <p className="text-sm">Loading…</p>}
      {list.state === "denied" && (
        <p role="alert" className={ALERT}>
          Your role may not open questions.
        </p>
      )}
      {list.state === "failed" && (
        <p role="alert" className={ALERT}>
          {list.listError}{" "}
          <button type="button" className="underline" onClick={() => void list.reload()}>
            Try again
          </button>
        </p>
      )}
      {list.state === "ready" && list.items.length === 0 && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          {archived ? "No archived questions." : "No questions yet. Start one above."}
        </p>
      )}
      {list.items.length > 0 && (
        <ul className="divide-y divide-zinc-200 rounded-md border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {list.items.map((question) => (
            <li key={question.id}>
              <Link
                href={`/questions/${question.id}`}
                className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900"
              >
                <span>
                  <span className="font-mono font-medium">{question.code}</span>{" "}
                  <span className="text-zinc-600 dark:text-zinc-400">
                    {formatLabel(question.question_type)}
                  </span>
                </span>
                <FindingCounts counts={question.finding_counts} />
              </Link>
            </li>
          ))}
        </ul>
      )}
      {list.nextCursor && (
        <div>
          <button
            type="button"
            className="rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700"
            onClick={() => void list.showMore()}
          >
            Show more
          </button>
        </div>
      )}
    </section>
  );
}

function FindingCounts({ counts }: { counts: Summary["finding_counts"] }) {
  const parts = [
    counts.error > 0 && `${counts.error} mistake${counts.error === 1 ? "" : "s"}`,
    counts.incomplete > 0 && `${counts.incomplete} to do`,
    counts.warning > 0 && `${counts.warning} to check`,
  ].filter(Boolean);
  return (
    <span className="text-xs text-zinc-600 dark:text-zinc-400">
      {parts.length > 0 ? parts.join(" · ") : "Nothing left to fix"}
    </span>
  );
}
