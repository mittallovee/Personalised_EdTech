"use client";

import type { components } from "@qbank/api-client";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import {
  comparable,
  defaultPair,
  entryText,
  opText,
  pathText,
  reasonTexts,
  segmentsOf,
  valueText,
  type Change,
  type HistoryEntry,
  type Segment,
} from "@/lib/history";
import { NETWORK } from "@/lib/use-catalogue";

type Diff = components["schemas"]["DiffOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const MUTED = "text-sm text-zinc-600 dark:text-zinc-400";
const SELECT = "rounded-md border border-zinc-300 px-2 py-1 dark:border-zinc-700 dark:bg-zinc-900";

type Loaded =
  | { state: "loading" }
  | { state: "failed"; message: string }
  | { state: "ready"; entries: HistoryEntry[] };

/** Reads the history each time the tab opens, so a step just taken is in it. */
function useHistory(questionId: string): Loaded {
  const [loaded, setLoaded] = useState<Loaded>({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const result = await api().GET("/api/v1/questions/{question_id}/history", {
          params: { path: { question_id: questionId } },
        });
        if (cancelled) return;
        setLoaded(
          result.data
            ? { state: "ready", entries: result.data.data }
            : {
                state: "failed",
                message: errorMessage(result.error as never, result.response.status),
              },
        );
      } catch {
        if (!cancelled) setLoaded({ state: "failed", message: NETWORK });
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [questionId]);

  return loaded;
}

/** Who did what and when (E-09), oldest first. A return shows its reasons and note. */
export function HistoryPanel({ questionId, myId }: { questionId: string; myId: string }) {
  const loaded = useHistory(questionId);
  if (loaded.state === "loading") return <p>Loading the history…</p>;
  if (loaded.state === "failed") {
    return (
      <p role="alert" className={ALERT}>
        {loaded.message}
      </p>
    );
  }
  return (
    <section aria-label="History" className="grid gap-3">
      <h2 className="text-base font-semibold">History</h2>
      <ol className="grid gap-3">
        {loaded.entries.map((entry, index) => (
          <li
            key={`${entry.at}-${index}`}
            className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800"
          >
            <p className="text-sm font-medium">{entryText(entry, myId)}</p>
            <p className={MUTED}>{new Date(entry.at).toLocaleString()}</p>
            {entry.reasons.length > 0 && (
              <ul className="mt-1 list-disc pl-5 text-sm">
                {reasonTexts(entry.reasons).map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            )}
            {entry.note && <p className="mt-1 text-sm">Note: {entry.note}</p>}
          </li>
        ))}
      </ol>
    </section>
  );
}

/** Prose with its changed words marked: added words underlined, removed words struck through. */
function Marked({ segments }: { segments: readonly Segment[] }) {
  return (
    <p className="whitespace-pre-wrap text-sm">
      {segments.map((segment, index) =>
        segment.kind === "insert" ? (
          <ins
            key={index}
            className="bg-emerald-100 text-emerald-900 underline dark:bg-emerald-950 dark:text-emerald-200"
          >
            {segment.text}
          </ins>
        ) : segment.kind === "delete" ? (
          <del
            key={index}
            className="bg-red-100 text-red-900 line-through dark:bg-red-950 dark:text-red-200"
          >
            {segment.text}
          </del>
        ) : (
          <span key={index}>{segment.text}</span>
        ),
      )}
    </p>
  );
}

function ChangeRow({ change }: { change: Change }) {
  const segments = segmentsOf(change);
  return (
    <li className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
      <p className="text-sm font-medium">
        {opText(change.op)}: {pathText(change.path)}
      </p>
      {segments ? (
        <Marked segments={segments} />
      ) : (
        <dl className="mt-1 grid gap-1 text-sm">
          {change.op !== "add" && (
            <div>
              <dt className="inline font-medium">Before: </dt>
              <dd className="inline whitespace-pre-wrap break-words">{valueText(change.before)}</dd>
            </div>
          )}
          {change.op !== "remove" && (
            <div>
              <dt className="inline font-medium">After: </dt>
              <dd className="inline whitespace-pre-wrap break-words">{valueText(change.after)}</dd>
            </div>
          )}
        </dl>
      )}
    </li>
  );
}

type Shown =
  | { state: "idle" }
  | { state: "loading" }
  | { state: "failed"; message: string }
  | { state: "ready"; diff: Diff };

/**
 * What changed between two saved texts (E-08): pick an older and a newer one from the history.
 * The two newest are chosen at first. The API compares and checks that each text may be read;
 * a late answer to an older choice is dropped.
 */
export function ComparePanel({ questionId }: { questionId: string }) {
  const loaded = useHistory(questionId);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [shown, setShown] = useState<Shown>({ state: "idle" });
  const ticket = useRef(0);

  const entries = loaded.state === "ready" ? loaded.entries : null;
  const choices = entries ? comparable(entries) : [];

  useEffect(() => {
    if (!entries) return;
    const pair = defaultPair(comparable(entries));
    if (pair) {
      // Chosen once, when the history arrives; the person can change both afterwards.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFrom(pair.from);
      setTo(pair.to);
    }
  }, [entries]);

  const compare = useCallback(
    async (older: string, newer: string) => {
      const mine = ++ticket.current;
      setShown({ state: "loading" });
      try {
        const result = await api().GET("/api/v1/questions/{question_id}/diff", {
          params: { path: { question_id: questionId }, query: { from: older, to: newer } },
        });
        if (mine !== ticket.current) return;
        setShown(
          result.data
            ? { state: "ready", diff: result.data }
            : {
                state: "failed",
                message:
                  result.response.status === 404
                    ? "One of these texts does not exist, or you may not read it."
                    : errorMessage(result.error as never, result.response.status),
              },
        );
      } catch {
        if (mine === ticket.current) setShown({ state: "failed", message: NETWORK });
      }
    },
    [questionId],
  );

  useEffect(() => {
    if (!from || !to) return;
    // `compare` sets state before and after its network call, never as a loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void compare(from, to);
  }, [from, to, compare]);

  if (loaded.state === "loading") return <p>Loading the saved texts…</p>;
  if (loaded.state === "failed") {
    return (
      <p role="alert" className={ALERT}>
        {loaded.message}
      </p>
    );
  }
  if (choices.length < 2) {
    return (
      <p className={MUTED}>
        There is only one saved text so far. Save a checkpoint or submit the question, then compare
        again.
      </p>
    );
  }

  return (
    <section aria-label="Compare" className="grid gap-4">
      <h2 className="text-base font-semibold">Compare two saved texts</h2>
      <div className="flex flex-wrap gap-4">
        <label className="grid gap-1 text-sm">
          Older text
          <select value={from} onChange={(event) => setFrom(event.target.value)} className={SELECT}>
            {choices.map((choice) => (
              <option key={choice.id} value={choice.id}>
                {choice.label}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-sm">
          Newer text
          <select value={to} onChange={(event) => setTo(event.target.value)} className={SELECT}>
            {choices.map((choice) => (
              <option key={choice.id} value={choice.id}>
                {choice.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div aria-live="polite">
        {shown.state === "loading" && <p>Comparing…</p>}
        {shown.state === "failed" && (
          <p role="alert" className={ALERT}>
            {shown.message}
          </p>
        )}
        {shown.state === "ready" &&
          (shown.diff.identical ? (
            <p role="status">These two texts are the same.</p>
          ) : (
            <ul className="grid gap-3" aria-label="Changes">
              {shown.diff.changes.map((change, index) => (
                <ChangeRow key={index} change={change} />
              ))}
            </ul>
          ))}
      </div>
    </section>
  );
}
