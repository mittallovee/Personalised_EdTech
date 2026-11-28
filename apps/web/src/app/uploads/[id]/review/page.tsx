"use client";

import type { components } from "@qbank/api-client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { BlocksField } from "@/components/blocks-field";
import { FindingsPanel } from "@/components/findings-panel";
import { ItemsField } from "@/components/items-field";
import { MatchingField } from "@/components/matching-field";
import { OptionsField } from "@/components/options-field";
import { TypedAnswerField } from "@/components/typed-answer-field";
import { api, errorMessage, ifMatch } from "@/lib/api";
import {
  boxStyle,
  neighbour,
  nextOpen,
  shortcutOf,
  tally,
  titleOf,
  warningText,
  type Candidate,
  type IngestFile,
  type IngestPage,
} from "@/lib/ingest";
import { blocksOf, formatLabel, withField, type Content } from "@/lib/question-content";
import { NETWORK } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Duplicate = components["schemas"]["CandidateDuplicateOut"];
type Finding = components["schemas"]["FindingOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const OK =
  "rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

const STATE_LABEL: Record<Candidate["state"], string> = {
  NEW: "Waiting",
  ACCEPTED: "Made into a question",
  REJECTED: "Rejected",
  DUPLICATE: "Already in the bank",
};

export default function ReviewPage() {
  return (
    <Suspense fallback={<main className="p-8">Loading…</main>}>
      <Screen />
    </Suspense>
  );
}

/**
 * Extraction review (M6, G-06): the page as it was printed, the question the AI read (editable), and
 * what the checks and the bank say about it. AI only proposes: nothing becomes a question until the
 * person presses Create question. Shortcuts: j / k next and previous, n next waiting, a create,
 * r reject, s same as the exact duplicate. They never fire while you type in a field.
 */
function Screen() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const { id } = useParams<{ id: string }>();
  const [file, setFile] = useState<IngestFile | null>(null);
  const [pages, setPages] = useState<IngestPage[]>([]);
  const [list, setList] = useState<Candidate[]>([]);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Content | null>(null);
  const [dirty, setDirty] = useState(false);
  const [duplicates, setDuplicates] = useState<Duplicate[]>([]);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const reasonBox = useRef<HTMLTextAreaElement>(null);
  const signedIn = me !== null;

  const current = list.find((candidate) => candidate.id === currentId) ?? null;
  const decided = current !== null && current.state !== "NEW";

  const loadDuplicates = useCallback(async (candidateId: string) => {
    try {
      const { data } = await api().GET("/api/v1/ingest/candidates/{candidate_id}/duplicates", {
        params: { path: { candidate_id: candidateId } },
      });
      setDuplicates(data?.data ?? []);
    } catch {
      setDuplicates([]);
    }
  }, []);

  const select = useCallback(
    (candidates: Candidate[], target: string | null) => {
      const found = candidates.find((candidate) => candidate.id === target) ?? null;
      setCurrentId(found?.id ?? null);
      setDraft(found ? (structuredClone(found.content) as Content) : null);
      setDirty(false);
      setDuplicates([]);
      setReason("");
      if (found && found.state === "NEW") void loadDuplicates(found.id);
    },
    [loadDuplicates],
  );

  const load = useCallback(async () => {
    try {
      const [one, pageList, candidates] = await Promise.all([
        api().GET("/api/v1/ingest/files/{file_id}", { params: { path: { file_id: id } } }),
        api().GET("/api/v1/ingest/files/{file_id}/pages", { params: { path: { file_id: id } } }),
        api().GET("/api/v1/ingest/files/{file_id}/candidates", {
          params: { path: { file_id: id } },
        }),
      ]);
      if (!one.data || !candidates.data) {
        setProblem(errorMessage(one.error ?? candidates.error, one.response.status));
        return;
      }
      setFile(one.data);
      setPages(pageList.data?.data ?? []);
      setList(candidates.data.data);
      const all = candidates.data.data;
      select(all, all.find((c) => c.state === "NEW")?.id ?? all[0]?.id ?? null);
    } catch {
      setProblem(NETWORK);
    }
  }, [id, select]);

  useEffect(() => {
    if (!signedIn) return;
    const first = setTimeout(() => void load(), 0);
    return () => clearTimeout(first);
  }, [signedIn, load]);

  function replace(updated: Candidate) {
    setList((now) => now.map((candidate) => (candidate.id === updated.id ? updated : candidate)));
  }

  async function save(): Promise<Candidate | null> {
    if (!current || !draft) return null;
    const { data, error, response } = await api().PUT(
      "/api/v1/ingest/candidates/{candidate_id}/content",
      {
        params: {
          path: { candidate_id: current.id },
          header: { "If-Match": ifMatch(current.revision) },
        },
        body: { content: draft },
      },
    );
    if (!data) {
      setProblem(
        response.status === 412
          ? "Someone else changed this candidate. Reload the page to see it."
          : errorMessage(error, response.status),
      );
      return null;
    }
    replace(data);
    setDirty(false);
    void loadDuplicates(data.id);
    return data;
  }

  async function run(work: () => Promise<Candidate | null>, done: string) {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    setNotice(null);
    try {
      const result = await work();
      if (result) {
        replace(result);
        setNotice(done);
        const after = list.map((c) => (c.id === result.id ? result : c));
        select(after, nextOpen(after, result.id) ?? result.id);
      }
    } catch {
      setProblem(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  const post = async (
    path: "accept" | "reject" | "same-as",
    body?: object,
  ): Promise<Candidate | null> => {
    if (!current) return null;
    if (dirty && path === "accept" && !(await save())) return null;
    const params = { params: { path: { candidate_id: current.id } } };
    const answer =
      path === "accept"
        ? await api().POST("/api/v1/ingest/candidates/{candidate_id}/accept", params)
        : path === "reject"
          ? await api().POST("/api/v1/ingest/candidates/{candidate_id}/reject", {
              ...params,
              body: { reason: (body as { reason: string }).reason },
            })
          : await api().POST("/api/v1/ingest/candidates/{candidate_id}/same-as", {
              ...params,
              body: { question_id: (body as { question_id: string }).question_id },
            });
    if (!answer.data) {
      setProblem(errorMessage(answer.error, answer.response.status));
      return null;
    }
    return answer.data;
  };

  const act = {
    accept: () =>
      void run(
        () => post("accept"),
        "Created as a draft question. It is yours to finish and submit.",
      ),
    reject: () => {
      if (reason.trim() === "") {
        reasonBox.current?.focus();
        return;
      }
      void run(() => post("reject", { reason }), "Rejected.");
    },
    same: () => {
      const exact = duplicates.filter((d) => d.exact);
      if (exact.length === 1) {
        void run(
          () => post("same-as", { question_id: exact[0]!.question_id }),
          "Marked as already in the bank.",
        );
      } else {
        setProblem("Choose which question it is the same as from the list on the right.");
      }
    },
  };
  const latest = useRef({ act, list, currentId, decided, select });
  useEffect(() => {
    latest.current = { act, list, currentId, decided, select };
  });

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const { act, list, currentId, decided, select } = latest.current;
      const key = shortcutOf({
        key: event.key,
        ctrlKey: event.ctrlKey,
        metaKey: event.metaKey,
        altKey: event.altKey,
        target: event.target as HTMLElement | null,
      });
      if (key === null) return;
      event.preventDefault();
      if (key === "next") select(list, neighbour(list, currentId, 1));
      else if (key === "previous") select(list, neighbour(list, currentId, -1));
      else if (key === "next-open") select(list, nextOpen(list, currentId) ?? currentId);
      else if (decided) return;
      else if (key === "accept") act.accept();
      else if (key === "reject") reasonBox.current?.focus();
      else if (key === "same") act.same();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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

  const page = current ? pages.find((p) => p.page_no === current.page_no) : undefined;
  const counts = tally(list);
  const type = draft ? String(draft.question_type) : "";
  const hasOptions = ["SCQ", "MULTI_CORRECT", "ASSERTION_REASON", "MULTIPLE_STATEMENT"].includes(
    type,
  );
  const typed = ["INTEGER", "SINGLE_DIGIT", "NUMERICAL"].includes(type);
  const frozen = decided || busy;
  const box = current ? boxStyle(current.region) : null;

  return (
    <AppShell me={me} current="uploads" onSignOut={signOut} onStopActing={stopActing}>
      {shellError && (
        <p role="alert" className={`mb-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <div className="grid gap-4">
        <div>
          <Link href={`/uploads/${id}`} className="text-sm underline">
            Back to the document
          </Link>
          <h1 className="mt-1 text-2xl font-semibold">Review: {file?.file_name ?? "…"}</h1>
          <p className="text-sm text-zinc-700 dark:text-zinc-300" role="status">
            {list.length === 0
              ? "No questions were found in this document yet."
              : `${counts.NEW} waiting of ${list.length}. Shortcuts: j and k move, n next waiting, a create, r reject, s same as.`}
          </p>
        </div>
        {problem && (
          <p role="alert" className={ALERT}>
            {problem}
          </p>
        )}
        {notice && (
          <p role="status" className={OK}>
            {notice}
          </p>
        )}

        {current && draft && (
          <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr_20rem]">
            <section aria-label="The page" className="grid content-start gap-2">
              <h2 className="text-base font-semibold">
                Page {current.page_no} of {file?.page_count ?? "?"}
              </h2>
              {page?.has_picture ? (
                <div className="relative">
                  {/* eslint-disable-next-line @next/next/no-img-element -- our own re-encoded page picture behind the sign-in */}
                  <img
                    src={`/api/v1/ingest/files/${id}/pages/${current.page_no}/image`}
                    alt={`Page ${current.page_no} as printed`}
                    className="w-full rounded border border-zinc-200 dark:border-zinc-800"
                  />
                  {box && (
                    <div
                      aria-hidden="true"
                      className="pointer-events-none absolute rounded border-2 border-sky-500 bg-sky-500/10"
                      style={box}
                    />
                  )}
                </div>
              ) : (
                <p className="whitespace-pre-wrap rounded border border-zinc-200 p-3 text-sm dark:border-zinc-800">
                  {page?.text ?? "(no text)"}
                </p>
              )}
            </section>

            <section aria-label="The question" className="grid content-start gap-4">
              <h2 className="text-base font-semibold">
                {formatLabel(draft.question_type)} · {STATE_LABEL[current.state]}
              </h2>
              <BlocksField
                label="Question"
                blocks={blocksOf(draft.stem)}
                disabled={frozen}
                onChange={(next) => {
                  setDraft(withField(draft, "stem", next));
                  setDirty(true);
                }}
              />
              {type === "ASSERTION_REASON" && (
                <>
                  <BlocksField
                    label="Assertion (A)"
                    blocks={blocksOf(draft.assertion)}
                    disabled={frozen}
                    onChange={(next) => {
                      setDraft(withField(draft, "assertion", next));
                      setDirty(true);
                    }}
                  />
                  <BlocksField
                    label="Reason (R)"
                    blocks={blocksOf(draft.reason)}
                    disabled={frozen}
                    onChange={(next) => {
                      setDraft(withField(draft, "reason", next));
                      setDirty(true);
                    }}
                  />
                </>
              )}
              {type === "MULTIPLE_STATEMENT" && (
                <ItemsField
                  content={draft}
                  field="statements"
                  prefix="S"
                  legend="Statements"
                  nameOf={(index) => `Statement ${index + 1}`}
                  addLabel="Add statement"
                  disabled={frozen}
                  onChange={(next) => {
                    setDraft(next);
                    setDirty(true);
                  }}
                />
              )}
              {type === "MATCHING" && (
                <MatchingField
                  content={draft}
                  disabled={frozen}
                  onChange={(next) => {
                    setDraft(next);
                    setDirty(true);
                  }}
                />
              )}
              {hasOptions && (
                <OptionsField
                  content={draft}
                  disabled={frozen}
                  onChange={(next) => {
                    setDraft(next);
                    setDirty(true);
                  }}
                />
              )}
              {typed && (
                <TypedAnswerField
                  content={draft}
                  disabled={frozen}
                  onChange={(next) => {
                    setDraft(next);
                    setDirty(true);
                  }}
                />
              )}
              <BlocksField
                label="Solution (optional)"
                blocks={blocksOf(draft.solution)}
                disabled={frozen}
                onChange={(next) => {
                  setDraft(withField(draft, "solution", next));
                  setDirty(true);
                }}
              />
              {!decided && (
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={BUTTON}
                    disabled={!dirty || busy}
                    onClick={() => void run(save, "Saved.")}
                  >
                    Save changes
                  </button>
                  <button type="button" className={PRIMARY} disabled={busy} onClick={act.accept}>
                    Create question
                  </button>
                </div>
              )}
              {current.state === "ACCEPTED" && current.question_id && (
                <p className="text-sm">
                  <Link className="underline" href={`/questions/${current.question_id}`}>
                    Open the question made from this
                  </Link>
                </p>
              )}
              {current.state === "DUPLICATE" && current.question_id && (
                <p className="text-sm">
                  <Link className="underline" href={`/questions/${current.question_id}`}>
                    Open the question it is the same as
                  </Link>
                </p>
              )}
              {current.state === "REJECTED" && (
                <p className="text-sm">Rejected: {current.reject_reason}</p>
              )}
            </section>

            <aside aria-label="Checks and the bank" className="grid content-start gap-4">
              {current.warnings.length > 0 && (
                <ul
                  aria-label="Things to check"
                  className="grid gap-1 text-sm text-amber-800 dark:text-amber-300"
                >
                  {current.warnings.map((code) => (
                    <li key={code}>{warningText(code)}</li>
                  ))}
                </ul>
              )}
              <FindingsPanel findings={current.findings as unknown as Finding[]} title="Checks" />
              <section
                aria-label="Possible duplicates"
                className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800"
              >
                <h2 className="text-base font-semibold">Already in the bank?</h2>
                {duplicates.length === 0 ? (
                  <p className="mt-1 text-sm text-emerald-800 dark:text-emerald-300">
                    No similar question found.
                  </p>
                ) : (
                  <ul className="mt-2 grid gap-2 text-sm">
                    {duplicates.map((d) => (
                      <li key={d.question_id}>
                        <Link className="font-mono underline" href={`/questions/${d.question_id}`}>
                          {d.code}
                        </Link>{" "}
                        {d.exact ? "Exact copy" : `${d.similarity_percent}% alike`}
                        <p className="text-zinc-700 dark:text-zinc-300">{d.preview}</p>
                        {!decided && (
                          <button
                            type="button"
                            className={`${BUTTON} mt-1`}
                            disabled={busy}
                            onClick={() =>
                              void run(
                                () => post("same-as", { question_id: d.question_id }),
                                "Marked as already in the bank.",
                              )
                            }
                          >
                            This is that question
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              {!decided && (
                <div className="grid gap-2">
                  <label className="grid gap-1 text-sm">
                    Reason to reject
                    <textarea
                      ref={reasonBox}
                      className="rounded-md border border-zinc-300 bg-transparent px-2 py-1 dark:border-zinc-700"
                      rows={2}
                      maxLength={500}
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    className={`${BUTTON} justify-self-start`}
                    disabled={busy || reason.trim() === ""}
                    onClick={act.reject}
                  >
                    Reject
                  </button>
                </div>
              )}
              <section aria-label="All questions found">
                <h2 className="text-base font-semibold">All questions</h2>
                <ul className="mt-2 grid gap-1 text-sm">
                  {list.map((candidate) => (
                    <li key={candidate.id}>
                      <button
                        type="button"
                        aria-current={candidate.id === currentId ? "true" : undefined}
                        className={`w-full rounded-md px-2 py-1 text-left hover:bg-zinc-50 dark:hover:bg-zinc-900 ${
                          candidate.id === currentId
                            ? "bg-zinc-100 font-medium dark:bg-zinc-800"
                            : ""
                        }`}
                        onClick={() => select(list, candidate.id)}
                      >
                        p{candidate.page_no}.{candidate.ordinal} {titleOf(candidate.content)}
                        <span className="block text-xs text-zinc-600 dark:text-zinc-400">
                          {STATE_LABEL[candidate.state]}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            </aside>
          </div>
        )}
      </div>
    </AppShell>
  );
}
