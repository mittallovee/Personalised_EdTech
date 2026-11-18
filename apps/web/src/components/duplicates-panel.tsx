"use client";

import type { components } from "@qbank/api-client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import {
  CLOSED_TEXT,
  VERDICTS,
  blockedText,
  canDecide,
  decisionText,
  matchText,
  type Duplicate,
  type Verdict,
} from "@/lib/duplicates";
import { NETWORK } from "@/lib/use-catalogue";
import { STATE_LABEL, type State } from "@/lib/workflow";

type Found = components["schemas"]["DuplicatesOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const BUTTON =
  "rounded-md border border-zinc-300 px-2 py-1 text-xs disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-2 py-1 text-xs text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

function stateText(state: string): string {
  return STATE_LABEL[state as State] ?? state;
}

/** The note a decision needs (the API asks for a few words of why), then sends it. */
function DecisionForm({
  ask,
  busy,
  onSend,
  onCancel,
}: {
  ask: string;
  busy: boolean;
  onSend: (note: string) => void;
  onCancel: () => void;
}) {
  const [note, setNote] = useState("");
  const ready = note.trim().length > 0;
  return (
    <form
      className="mt-2 grid gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (ready) onSend(note.trim());
      }}
    >
      <label className="grid gap-1 text-xs">
        {ask}
        <input
          value={note}
          maxLength={1000}
          onChange={(event) => setNote(event.target.value)}
          className="rounded-md border border-zinc-300 px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-900"
        />
      </label>
      <div className="flex gap-2">
        <button type="submit" className={PRIMARY} disabled={busy || !ready}>
          Save decision
        </button>
        <button type="button" className={BUTTON} disabled={busy} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

/**
 * Possible duplicates of this question (D-16): questions in the coaching with the same content or
 * very similar text, that this person may open. A person decides whether each is a duplicate; the
 * API says who may, and which undecided or confirmed copies block Pass QC. Nothing is merged.
 * `stamp` changes when the page wants a fresh check (after a review step), and the button asks
 * for one by hand.
 */
export function DuplicatesPanel({
  questionId,
  myId,
  stamp,
  state,
}: {
  questionId: string;
  myId: string;
  stamp: number;
  state: string;
}) {
  const [found, setFound] = useState<Found | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [deciding, setDeciding] = useState<{ id: string; verdict: Verdict } | null>(null);
  const [busy, setBusy] = useState(false);
  const [fresh, setFresh] = useState(0);
  // A late answer to an older check is dropped, so it never replaces a newer one.
  const ticket = useRef(0);

  const check = useCallback(async () => {
    const mine = ++ticket.current;
    try {
      const result = await api().GET("/api/v1/questions/{question_id}/duplicates", {
        params: { path: { question_id: questionId } },
      });
      if (mine !== ticket.current) return;
      if (result.data) {
        setFound(result.data);
        setProblem(null);
      } else if (result.response.status === 503) {
        setProblem("The check took too long. Try again in a moment.");
      } else {
        setProblem(errorMessage(result.error as never, result.response.status));
      }
    } catch {
      if (mine === ticket.current) setProblem(NETWORK);
    }
  }, [questionId]);

  useEffect(() => {
    // `check` sets state only after the network call returns, never during this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void check();
  }, [check, stamp, fresh]);

  async function decide(other: string, verdict: Verdict, note: string) {
    setBusy(true);
    try {
      const result = await api().POST("/api/v1/questions/{question_id}/duplicates/decisions", {
        params: { path: { question_id: questionId } },
        body: { other_question_id: other, decision: verdict, note },
      });
      if (result.data) {
        setDeciding(null);
        setProblem(null);
        setFresh((n) => n + 1);
      } else if (result.response.status === 403) {
        setProblem("Only the author, an admin, or someone with QC or edit rights may decide this.");
      } else {
        setProblem(errorMessage(result.error as never, result.response.status));
      }
    } catch {
      setProblem(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  const blocked = found ? blockedText(found.qc_blocked_by.map((b) => b.code)) : null;

  return (
    <section
      aria-label="Possible duplicates"
      className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold">Possible duplicates</h2>
        <button type="button" className={BUTTON} onClick={() => setFresh((n) => n + 1)}>
          Check again
        </button>
      </div>
      {problem && (
        <p role="alert" className={`mt-2 ${ALERT}`}>
          {problem}
        </p>
      )}
      {found === null && !problem && <p className="mt-2 text-sm">Checking…</p>}
      {blocked && (
        <p role="status" className="mt-2 text-sm text-amber-800 dark:text-amber-300">
          {blocked}
        </p>
      )}
      {found && found.data.length > 0 && !canDecide(state) && (
        <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{CLOSED_TEXT}</p>
      )}
      {found && found.data.length === 0 && (
        <p className="mt-2 text-sm text-emerald-800 dark:text-emerald-300">
          No similar question found.
        </p>
      )}
      {found && found.data.length > 0 && (
        <ul className="mt-2 grid gap-3">
          {found.data.map((item: Duplicate) => {
            const decided = decisionText(item.decision, myId);
            const open = deciding?.id === item.question_id ? deciding : null;
            return (
              <li
                key={`${item.match}-${item.question_id}`}
                className="rounded-md border border-zinc-200 p-3 text-sm dark:border-zinc-800"
              >
                <p>
                  <Link href={`/questions/${item.question_id}`} className="font-mono underline">
                    {item.code}
                  </Link>{" "}
                  <span className="text-zinc-600 dark:text-zinc-400">
                    {stateText(item.state)} · {matchText(item)}
                  </span>
                </p>
                <p className="mt-1 break-words">{item.preview}</p>
                {decided && <p className="mt-1 text-zinc-700 dark:text-zinc-300">{decided}</p>}
                {!canDecide(state) ? null : open ? (
                  <DecisionForm
                    ask={VERDICTS.find((v) => v.verdict === open.verdict)!.ask}
                    busy={busy}
                    onSend={(note) => void decide(item.question_id, open.verdict, note)}
                    onCancel={() => setDeciding(null)}
                  />
                ) : (
                  <div
                    role="group"
                    aria-label={`Decide about ${item.code}`}
                    className="mt-2 flex gap-2"
                  >
                    {VERDICTS.map(({ verdict, label }) => (
                      <button
                        key={verdict}
                        type="button"
                        className={BUTTON}
                        disabled={busy}
                        onClick={() => setDeciding({ id: item.question_id, verdict })}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
