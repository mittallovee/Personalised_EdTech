"use client";

import type { components } from "@qbank/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";

import { StateBadge } from "@/components/workflow-bar";
import { api, errorMessage } from "@/lib/api";
import {
  BLOOM_LEVELS,
  MAX_WORDS,
  NO_FILTERS,
  bankQuery,
  countLine,
  isFiltered,
  type BankFilters,
} from "@/lib/bank";
import { FORMATS, formatLabel } from "@/lib/question-content";
import { useAll } from "@/lib/use-all";
import { NETWORK } from "@/lib/use-catalogue";
import { STATE_LABEL, type State } from "@/lib/workflow";

type Item = components["schemas"]["BankItem"];
type Node = components["schemas"]["NodeOut"];
type Kind = "SUBJECT" | "CHAPTER" | "TOPIC";

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const FIELD =
  "rounded-md border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-900";
/** How long typing must pause before a search is sent (searches are limited per person). */
const SEARCH_PAUSE_MS = 400;

function nodes(kind: Kind, parent: string | null) {
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

/** Open a question by its code (forgiving about case, spaces and dashes; the API decides). */
function CodeBox() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function open() {
    setBusy(true);
    setProblem(null);
    try {
      const result = await api().GET("/api/v1/bank/questions/by-code/{code}", {
        params: { path: { code: code.trim() } },
      });
      if (result.data) router.push(`/questions/${result.data.question_id}`);
      else if (result.response.status === 404) setProblem("No question has that code.");
      else setProblem(errorMessage(result.error as never, result.response.status));
    } catch {
      setProblem(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      aria-label="Open by code"
      className="flex flex-wrap items-end gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (code.trim()) void open();
      }}
    >
      <label className="grid gap-1 text-sm">
        Code
        <input
          value={code}
          maxLength={40}
          onChange={(event) => setCode(event.target.value)}
          className={`${FIELD} font-mono uppercase`}
          placeholder="7K2M9PQX"
        />
      </label>
      <button type="submit" className={BUTTON} disabled={busy || !code.trim()}>
        Open
      </button>
      {problem && (
        <p role="alert" className={`w-full ${ALERT}`}>
          {problem}
        </p>
      )}
    </form>
  );
}

/**
 * The bank (F-01, F-02, F-03): every question you may open, newest change first, with filters, a
 * live count, a search that forgives typos, and a box that opens a question by its code. What you
 * may see, how many match and how a search is ranked all come from the API.
 */
export function BankList({ myId }: { myId: string }) {
  const [filters, setFilters] = useState<BankFilters>(NO_FILTERS);
  const [typed, setTyped] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [truncated, setTruncated] = useState(false);
  const [next, setNext] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [denied, setDenied] = useState(false);
  // Each load takes a ticket; a late answer to an older one (other filters, older words, a "Show
  // more" for the list that was there before) is dropped, so it never replaces the newer list.
  const ticket = useRef(0);

  // The search words follow the box after a pause, so typing sends one search, not one per key.
  useEffect(() => {
    const timer = window.setTimeout(
      () => setFilters((now) => (now.words === typed ? now : { ...now, words: typed })),
      SEARCH_PAUSE_MS,
    );
    return () => window.clearTimeout(timer);
  }, [typed]);

  const subjects = useAll<Node>(
    "subjects",
    useMemo(() => nodes("SUBJECT", null), []),
  );
  const chapters = useAll<Node>(
    filters.subject ? `chapters:${filters.subject}` : null,
    useMemo(() => nodes("CHAPTER", filters.subject || null), [filters.subject]),
  );
  const topics = useAll<Node>(
    filters.chapter ? `topics:${filters.chapter}` : null,
    useMemo(() => nodes("TOPIC", filters.chapter || null), [filters.chapter]),
  );

  const load = useCallback(
    async (cursor: string | null) => {
      const mine = ++ticket.current;
      try {
        const result = await api().GET("/api/v1/bank/questions", {
          params: { query: bankQuery(filters, myId, cursor) },
        });
        if (mine !== ticket.current) return;
        if (result.response.status === 403) {
          setDenied(true);
          return;
        }
        if (!result.data) {
          setProblem(errorMessage(result.error as never, result.response.status));
          return;
        }
        const page = result.data;
        setItems((now) => (cursor ? [...now, ...page.data] : page.data));
        setTotal(page.total);
        setTruncated(page.truncated ?? false);
        setNext(page.page.next_cursor ?? null);
        setProblem(null);
      } catch {
        if (mine === ticket.current) setProblem(NETWORK);
      }
    },
    [filters, myId],
  );

  useEffect(() => {
    // `load` sets state only after the network call returns, never during this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(null);
  }, [load]);

  if (denied) {
    return (
      <p role="alert" className={ALERT}>
        Your role may not open questions.
      </p>
    );
  }

  const names = new Map(
    [...subjects.items, ...chapters.items, ...topics.items].map((n) => [n.id, n.name]),
  );
  const set = (change: Partial<BankFilters>) => setFilters((now) => ({ ...now, ...change }));
  const searching = filters.words.trim().length > 0;

  return (
    <section aria-label="Question bank" className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h2 className="text-lg font-medium">{filters.archived ? "Archive" : "Question bank"}</h2>
        <CodeBox />
      </div>

      <label className="grid gap-1 text-sm">
        Search the stem, options and solution
        <input
          type="search"
          value={typed}
          maxLength={MAX_WORDS}
          onChange={(event) => setTyped(event.target.value)}
          className={FIELD}
          placeholder={'Words, "a phrase", or -leave-out'}
        />
      </label>

      <fieldset className="flex flex-wrap items-end gap-3 text-sm">
        <legend className="sr-only">Filters</legend>
        <Select
          label="Subject"
          value={filters.subject}
          onChange={(subject) => set({ subject, chapter: "", topic: "" })}
          any="All subjects"
          choices={subjects.items.map((n) => ({ value: n.id, label: n.name }))}
        />
        <Select
          label="Chapter"
          value={filters.chapter}
          disabled={!filters.subject}
          onChange={(chapter) => set({ chapter, topic: "" })}
          any="All chapters"
          choices={chapters.items.map((n) => ({ value: n.id, label: n.name }))}
        />
        <Select
          label="Topic"
          value={filters.topic}
          disabled={!filters.chapter}
          onChange={(topic) => set({ topic })}
          any="All topics"
          choices={topics.items.map((n) => ({ value: n.id, label: n.name }))}
        />
        <Select
          label="Format"
          value={filters.format}
          onChange={(format) => set({ format })}
          any="Any format"
          choices={FORMATS.map((f) => ({ value: f.value, label: f.label }))}
        />
        <Select
          label="Difficulty"
          value={filters.difficulty}
          onChange={(difficulty) => set({ difficulty })}
          any="Any"
          choices={Array.from({ length: 10 }, (_, i) => ({
            value: String(i + 1),
            label: String(i + 1),
          }))}
        />
        <Select
          label="Bloom level"
          value={filters.bloom}
          onChange={(bloom) => set({ bloom })}
          any="Any"
          choices={[...BLOOM_LEVELS]}
        />
        <Select
          label="Language"
          value={filters.language}
          onChange={(language) => set({ language })}
          any="Any language"
          choices={[
            { value: "en", label: "English" },
            { value: "hi", label: "Hindi" },
          ]}
        />
        <Select
          label="State"
          value={filters.state}
          onChange={(state) => set({ state })}
          any="Any state"
          choices={(Object.keys(STATE_LABEL) as State[]).map((s) => ({
            value: s,
            label: STATE_LABEL[s],
          }))}
        />
        <Check label="Past-year" checked={filters.pyq} onChange={(pyq) => set({ pyq })} />
        <Check
          label="Has a solution"
          checked={filters.solution}
          onChange={(solution) => set({ solution })}
        />
        <Check label="Has a video" checked={filters.video} onChange={(video) => set({ video })} />
        <Check label="Only mine" checked={filters.mine} onChange={(mine) => set({ mine })} />
        <Check
          label="Archived"
          checked={filters.archived}
          onChange={(archived) => set({ archived })}
        />
        <button
          type="button"
          className={BUTTON}
          disabled={!isFiltered(filters) && typed === ""}
          onClick={() => {
            setTyped("");
            setFilters(NO_FILTERS);
          }}
        >
          Clear
        </button>
      </fieldset>
      {(subjects.failed || chapters.failed || topics.failed) && (
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
      {total !== null && (
        <p role="status" aria-live="polite" className="text-sm text-zinc-700 dark:text-zinc-300">
          {countLine(total, searching, truncated)}
        </p>
      )}
      {total === 0 && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          {isFiltered(filters) ? "Nothing matches. Try fewer filters." : "No questions yet."}
        </p>
      )}
      {items.length > 0 && (
        <ul className="divide-y divide-zinc-200 rounded-md border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {items.map((item) => (
            <li key={item.question_id} className="grid gap-1 px-4 py-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  href={`/questions/${item.question_id}`}
                  className="font-mono font-medium underline"
                >
                  {item.code}
                </Link>
                <StateBadge state={item.state as State} />
                <span className="text-zinc-600 dark:text-zinc-400">
                  {formatLabel(item.question_type ?? undefined)}
                </span>
                {item.has_open_correction && (
                  <span className="text-xs text-zinc-600 dark:text-zinc-400">
                    correction in progress
                  </span>
                )}
              </div>
              {item.preview && <p className="text-zinc-800 dark:text-zinc-200">{item.preview}</p>}
              <p className="text-xs text-zinc-600 dark:text-zinc-400">
                {[
                  item.subject_id && names.get(item.subject_id),
                  item.chapter_id && names.get(item.chapter_id),
                  item.difficulty !== null && `difficulty ${item.difficulty}`,
                  item.is_pyq && `past-year${item.exam_year ? ` ${item.exam_year}` : ""}`,
                  `changed ${new Date(item.updated_at).toLocaleDateString()}`,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </li>
          ))}
        </ul>
      )}
      {next && !searching && (
        <button
          type="button"
          className={`${BUTTON} justify-self-start`}
          onClick={() => void load(next)}
        >
          Show more
        </button>
      )}
    </section>
  );
}

function Select({
  label,
  value,
  onChange,
  any,
  choices,
  disabled = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  any: string;
  choices: { value: string; label: string }[];
  disabled?: boolean;
}) {
  // Named by its label alone, not by the label and every option's text run together.
  const id = useId();
  return (
    <label className="grid gap-1">
      <span id={id}>{label}</span>
      <select
        aria-labelledby={id}
        className={FIELD}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{any}</option>
        {choices.map((choice) => (
          <option key={choice.value} value={choice.value}>
            {choice.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function Check({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 pb-1">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      {label}
    </label>
  );
}
