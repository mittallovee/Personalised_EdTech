"use client";

import type { components } from "@qbank/api-client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { api, errorMessage } from "@/lib/api";
import { formatLabel } from "@/lib/question-content";
import { AGE_CHOICES, QUEUE_TABS, waited, type QueueCounts, type QueueState } from "@/lib/review";
import { useAll } from "@/lib/use-all";
import { NETWORK } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Row = components["schemas"]["QueueItem"];
type Node = components["schemas"]["NodeOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const FIELD =
  "rounded-md border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-900";

/** The review queue (E-05): what waits for QC, approval or publication, oldest first. */
export default function ReviewPage() {
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
    <AppShell me={me} current="review" onSignOut={signOut} onStopActing={stopActing}>
      {shellError && (
        <p role="alert" className={`mb-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <Queue />
    </AppShell>
  );
}

type Filters = {
  subject: string;
  chapter: string;
  language: string;
  age: number | null;
};

const NO_FILTERS: Filters = { subject: "", chapter: "", language: "", age: null };

function nodes(kind: "SUBJECT" | "CHAPTER", parent: string | null) {
  return (cursor: string | null) =>
    api().GET("/api/v1/taxonomy/nodes", {
      params: {
        query: {
          kind,
          limit: 100,
          ...(parent ? { parent_id: parent } : {}),
          ...(cursor ? { cursor } : {}),
        },
      },
    });
}

function Queue() {
  const [tab, setTab] = useState<QueueState>("IN_REVIEW");
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [counts, setCounts] = useState<QueueCounts | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [denied, setDenied] = useState(false);
  // Each load takes a ticket; an answer to an older ticket (another tab or filter, or a "Show more"
  // for the list that was there before) arrives too late and is dropped.
  const ticket = useRef(0);

  const subjects = useAll<Node>(
    "subjects",
    useMemo(() => nodes("SUBJECT", null), []),
  );
  const chapters = useAll<Node>(
    filters.subject ? `chapters:${filters.subject}` : null,
    useMemo(() => nodes("CHAPTER", filters.subject || null), [filters.subject]),
  );

  const load = useCallback(
    async (cursor: string | null) => {
      const mine = ++ticket.current;
      try {
        const [page, count] = await Promise.all([
          api().GET("/api/v1/review/queue", {
            params: {
              query: {
                state: tab,
                limit: 50,
                ...(filters.subject ? { subject_id: filters.subject } : {}),
                ...(filters.chapter ? { chapter_id: filters.chapter } : {}),
                ...(filters.language ? { language: filters.language } : {}),
                ...(filters.age !== null ? { older_than_days: filters.age } : {}),
                ...(cursor ? { cursor } : {}),
              },
            },
          }),
          cursor ? Promise.resolve(null) : api().GET("/api/v1/review/queue/counts"),
        ]);
        if (mine !== ticket.current) return;
        if (page.response.status === 403) {
          setDenied(true);
          return;
        }
        if (!page.data) {
          setProblem(errorMessage(page.error as never, page.response.status));
          return;
        }
        const data = page.data;
        setRows((now) => (cursor ? [...now, ...data.data] : data.data));
        setNext(data.page.next_cursor ?? null);
        if (count?.data) setCounts(count.data);
        setProblem(null);
        setLoaded(true);
      } catch {
        if (mine === ticket.current) setProblem(NETWORK);
      }
    },
    [tab, filters],
  );

  useEffect(() => {
    // `load` sets state only after the network call returns, never during this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(null);
  }, [load]);

  if (denied) {
    return (
      <p role="alert" className={ALERT}>
        The review queue is for people with the QC, approve or publish grant. Ask an admin if you
        need one.
      </p>
    );
  }

  const subjectName = new Map(subjects.items.map((n) => [n.id, n.name]));
  return (
    <div className="grid max-w-5xl gap-4">
      <h1 className="text-2xl font-semibold">Review</h1>
      <div role="tablist" aria-label="Queue" className="flex flex-wrap gap-2">
        {QUEUE_TABS.map(({ state, label, count }) => (
          <button
            key={state}
            role="tab"
            type="button"
            aria-selected={tab === state}
            onClick={() => setTab(state)}
            className={`rounded-md px-3 py-1 text-sm ${
              tab === state
                ? "bg-zinc-100 font-medium dark:bg-zinc-800"
                : "hover:bg-zinc-50 dark:hover:bg-zinc-900"
            }`}
          >
            {label}
            {counts && ` (${counts[count]})`}
          </button>
        ))}
      </div>

      <fieldset className="flex flex-wrap items-end gap-3 text-sm">
        <legend className="sr-only">Filters</legend>
        <label className="grid gap-1">
          Subject
          <select
            className={FIELD}
            value={filters.subject}
            onChange={(e) => setFilters({ ...filters, subject: e.target.value, chapter: "" })}
          >
            <option value="">All subjects</option>
            {subjects.items.map((n) => (
              <option key={n.id} value={n.id}>
                {n.name}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1">
          Chapter
          <select
            className={FIELD}
            value={filters.chapter}
            disabled={!filters.subject}
            onChange={(e) => setFilters({ ...filters, chapter: e.target.value })}
          >
            <option value="">All chapters</option>
            {chapters.items.map((n) => (
              <option key={n.id} value={n.id}>
                {n.name}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1">
          Language
          <select
            className={FIELD}
            value={filters.language}
            onChange={(e) => setFilters({ ...filters, language: e.target.value })}
          >
            <option value="">Any language</option>
            <option value="en">English</option>
            <option value="hi">Hindi</option>
          </select>
        </label>
        <label className="grid gap-1">
          Waiting
          <select
            className={FIELD}
            value={filters.age ?? ""}
            onChange={(e) =>
              setFilters({ ...filters, age: e.target.value ? Number(e.target.value) : null })
            }
          >
            {AGE_CHOICES.map(({ days, label }) => (
              <option key={label} value={days ?? ""}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className={BUTTON}
          disabled={filters === NO_FILTERS}
          onClick={() => setFilters(NO_FILTERS)}
        >
          Clear filters
        </button>
      </fieldset>
      {(subjects.failed || chapters.failed) && (
        <p className="text-sm text-amber-800 dark:text-amber-300">
          The syllabus could not be read, so some filters are empty.
        </p>
      )}

      {problem && (
        <p role="alert" className={ALERT}>
          {problem}{" "}
          <button type="button" className="underline" onClick={() => void load(null)}>
            Try again
          </button>
        </p>
      )}
      {loaded && rows.length === 0 && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">Nothing is waiting here.</p>
      )}
      {rows.length > 0 && (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-zinc-200 dark:border-zinc-800">
              <th className="py-2 pr-3 font-medium">Code</th>
              <th className="py-2 pr-3 font-medium">Format</th>
              <th className="py-2 pr-3 font-medium">Subject</th>
              <th className="py-2 pr-3 font-medium">Language</th>
              <th className="py-2 pr-3 font-medium">Waiting</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.question_id} className="border-b border-zinc-100 dark:border-zinc-900">
                <td className="py-2 pr-3">
                  <Link href={`/questions/${row.question_id}`} className="font-mono underline">
                    {row.code}
                  </Link>
                  {row.version_number > 1 && (
                    <span className="ml-2 text-xs text-zinc-600 dark:text-zinc-400">
                      correction, version {row.version_number}
                    </span>
                  )}
                </td>
                <td className="py-2 pr-3">{formatLabel(row.question_type ?? undefined)}</td>
                <td className="py-2 pr-3">
                  {row.subject_id ? (subjectName.get(row.subject_id) ?? "—") : "—"}
                </td>
                <td className="py-2 pr-3">{row.language ?? "—"}</td>
                <td className="py-2 pr-3">{waited(row.waiting_since)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {next && (
        <button
          type="button"
          className={`${BUTTON} justify-self-start`}
          onClick={() => void load(next)}
        >
          Show more
        </button>
      )}
    </div>
  );
}
