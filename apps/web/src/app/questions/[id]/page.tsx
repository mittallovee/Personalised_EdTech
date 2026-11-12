"use client";

import type { components } from "@qbank/api-client";
import { QuestionPreview } from "@qbank/content-renderer";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { BlocksField } from "@/components/blocks-field";
import { FindingsPanel } from "@/components/findings-panel";
import { ItemsField } from "@/components/items-field";
import { MatchingField } from "@/components/matching-field";
import { MetadataField } from "@/components/metadata-field";
import { OptionsField } from "@/components/options-field";
import { PassagePanel } from "@/components/passage-panel";
import { TypedAnswerField } from "@/components/typed-answer-field";
import { api, errorMessage, ifMatch } from "@/lib/api";
import { moveToCheckpoint, pinOf } from "@/lib/passage-pin";
import { blocksOf, formatLabel, savedLabel, withField } from "@/lib/question-content";
import { useAutosave, type SaveState } from "@/lib/use-autosave";
import { NETWORK } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";
import { usePinnedPassage } from "@/lib/use-pinned-passage";

type Question = components["schemas"]["QuestionOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/**
 * The question editor (D-11, E-04): write the stem, see the findings, preview it as a student
 * will see it, save a checkpoint, archive. Typing is saved by itself a moment after you stop.
 * All eight formats are edited here. A question written under a passage shows that passage above
 * the editor and in the preview.
 */
export default function QuestionPage() {
  // useParams reads the address at request time, so the page needs a boundary to wait behind.
  return (
    <Suspense fallback={<main className="p-8">Loading…</main>}>
      <QuestionScreen />
    </Suspense>
  );
}

function QuestionScreen() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const { id } = useParams<{ id: string }>();

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
      {shellError && (
        <p role="alert" className={`mb-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <Loader id={id} />
    </AppShell>
  );
}

/** Reads the question, then hands it to the editor (which owns it from then on). */
function Loader({ id }: { id: string }) {
  const [question, setQuestion] = useState<Question | null>(null);
  const [problem, setProblem] = useState<"missing" | "failed" | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      let result;
      try {
        result = await api().GET("/api/v1/questions/{question_id}", {
          params: { path: { question_id: id } },
        });
      } catch {
        if (!cancelled) setProblem("failed");
        return;
      }
      if (cancelled) return;
      if (result.data) setQuestion(result.data);
      else setProblem(result.response.status === 404 ? "missing" : "failed");
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [id, attempt]);

  if (problem === "missing") {
    return (
      <div>
        <p role="alert" className={ALERT}>
          This question does not exist, or you may not open it.
        </p>
        <Link href="/questions" className="mt-4 inline-block underline">
          Back to questions
        </Link>
      </div>
    );
  }
  if (problem === "failed") {
    return (
      <div>
        <p role="alert" className={ALERT}>
          The question could not be loaded.
        </p>
        <button
          type="button"
          className="mt-4 underline"
          onClick={() => {
            setProblem(null);
            setAttempt((n) => n + 1);
          }}
        >
          Try again
        </button>
      </div>
    );
  }
  if (!question) return <p>Loading…</p>;
  return <Editor key={question.id} initial={question} />;
}

const STATE_TEXT: Record<SaveState, string> = {
  saved: "All changes saved",
  dirty: "Unsaved changes…",
  saving: "Saving…",
  failed: "Not saved",
  conflict: "Not saved",
  archived: "Archived",
};

function Editor({ initial }: { initial: Question }) {
  const save = useAutosave(initial);
  const passage = usePinnedPassage(pinOf(save.content));
  const [tab, setTab] = useState<"edit" | "preview">("edit");
  const [reveal, setReveal] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [version, setVersion] = useState({ number: initial.version_number, id: initial.id });
  const archived = save.state === "archived";
  const type = save.content.question_type;
  // These formats list four options written as content; matching's options are mappings instead.
  const hasOptions = ["SCQ", "MULTI_CORRECT", "ASSERTION_REASON", "MULTIPLE_STATEMENT"].includes(
    String(type),
  );
  const typed = ["INTEGER", "SINGLE_DIGIT", "NUMERICAL"].includes(
    String(save.content.question_type),
  );
  const locked = archived || save.state === "conflict";

  /**
   * Run one of the buttons: only one at a time, and the text cannot be edited meanwhile, so
   * nothing typed can be replaced by the answer. What is typed is saved first, except when
   * restoring: the question is archived, so saving has to wait for the restore, and the typing is
   * kept (`keepEdits`) and saved afterwards.
   */
  const act = useCallback(
    async (
      work: () => Promise<{ data?: Question; error?: unknown; response: Response }>,
      keepEdits = false,
    ) => {
      if (busy) return;
      setBusy(true);
      setProblem(null);
      setNotice(null);
      try {
        if (!keepEdits && !(await save.flush())) {
          setProblem("Your changes could not be saved yet, so nothing else was done.");
          return;
        }
        const { data, error, response } = await work();
        if (data) {
          save.adopt(data, keepEdits);
          setVersion((v) => ({ ...v, number: data.version_number }));
        } else if (response.status === 412) {
          // The screen is out of date: stop saving and offer to reload, as a refused save does.
          save.markConflict();
        } else {
          setProblem(errorMessage(error as never, response.status));
        }
        return data;
      } catch {
        setProblem(NETWORK);
      } finally {
        setBusy(false);
      }
    },
    [busy, save],
  );

  async function checkpoint() {
    const done = await act(() =>
      api().POST("/api/v1/questions/{question_id}/checkpoints", {
        params: {
          path: { question_id: initial.id },
          header: { "If-Match": ifMatch(save.revision.current) },
        },
      }),
    );
    if (done) setNotice("Checkpoint saved. You can keep editing.");
  }

  async function setArchived(archive: boolean) {
    const done = await act(
      () =>
        api().POST(
          archive
            ? "/api/v1/questions/{question_id}/archive"
            : "/api/v1/questions/{question_id}/restore",
          { params: { path: { question_id: initial.id } } },
        ),
      !archive,
    );
    if (done) setNotice(archive ? "Archived. It is hidden from the list." : "Restored.");
  }

  async function reload() {
    const result = await api().GET("/api/v1/questions/{question_id}", {
      params: { path: { question_id: initial.id } },
    });
    if (result.data) {
      save.adopt(result.data);
      setProblem(null);
    } else {
      setProblem(errorMessage(result.error as never, result.response.status));
    }
  }

  const status =
    save.state === "saved" && save.savedAt ? savedLabel(save.savedAt) : STATE_TEXT[save.state];

  return (
    <div className="grid max-w-5xl gap-6">
      <div>
        <Link
          href="/questions"
          className="text-sm underline"
          onClick={(event) => {
            // Typing still waiting for its pause is saved as the editor closes; only typing that
            // could not be saved is at risk, so that is what asks first.
            const failed = save.state === "failed" || save.state === "conflict";
            if (
              failed &&
              save.unsaved() &&
              !window.confirm("Your latest changes were not saved. Leave without them?")
            ) {
              event.preventDefault();
            }
          }}
        >
          Back to questions
        </Link>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">
            Question <span className="font-mono">{initial.code}</span>{" "}
            <span className="text-base font-normal text-zinc-600 dark:text-zinc-400">
              {formatLabel(save.content.question_type)}
            </span>
          </h1>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={PRIMARY}
              disabled={busy || locked}
              onClick={() => void checkpoint()}
            >
              Save checkpoint
            </button>
            <button
              type="button"
              className={BUTTON}
              disabled={busy || save.state === "conflict"}
              onClick={() => void setArchived(!archived)}
            >
              {archived ? "Restore" : "Archive"}
            </button>
          </div>
        </div>
        <p
          role="status"
          aria-live="polite"
          className="mt-1 text-sm text-zinc-600 dark:text-zinc-400"
        >
          {status} · version {version.number}
        </p>
      </div>

      {(save.message || problem) && (
        <p role="alert" className={ALERT}>
          {problem ?? save.message}{" "}
          {save.state === "failed" && (
            <button type="button" className="underline" onClick={() => void save.flush()}>
              Try saving again
            </button>
          )}
          {save.state === "conflict" && (
            <button type="button" className="underline" onClick={() => void reload()}>
              Reload
            </button>
          )}
        </p>
      )}
      {notice && (
        <p
          role="status"
          className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
        >
          {notice}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_18rem]">
        <div className="grid gap-4">
          <div role="tablist" aria-label="Editor" className="flex gap-2">
            {(["edit", "preview"] as const).map((name) => (
              <button
                key={name}
                role="tab"
                type="button"
                aria-selected={tab === name}
                aria-controls={`panel-${name}`}
                id={`tab-${name}`}
                onClick={() => setTab(name)}
                className={`rounded-md px-3 py-1 text-sm ${
                  tab === name
                    ? "bg-zinc-100 font-medium dark:bg-zinc-800"
                    : "hover:bg-zinc-50 dark:hover:bg-zinc-900"
                }`}
              >
                {name === "edit" ? "Edit" : "Preview"}
              </button>
            ))}
          </div>

          {tab === "edit" ? (
            <div role="tabpanel" id="panel-edit" aria-labelledby="tab-edit" className="grid gap-6">
              <PassagePanel
                passage={passage}
                disabled={locked || busy}
                onMove={(checkpointId) => {
                  save.setContent(moveToCheckpoint(save.content, checkpointId));
                  setNotice("Moved to the newest checkpoint of the passage.");
                }}
              />
              <BlocksField
                label="Question"
                blocks={blocksOf(save.content.stem)}
                disabled={locked || busy}
                onChange={(next) => save.setContent(withField(save.content, "stem", next))}
              />
              {type === "ASSERTION_REASON" && (
                <>
                  <BlocksField
                    label="Assertion (A)"
                    blocks={blocksOf(save.content.assertion)}
                    disabled={locked || busy}
                    onChange={(next) => save.setContent(withField(save.content, "assertion", next))}
                  />
                  <BlocksField
                    label="Reason (R)"
                    blocks={blocksOf(save.content.reason)}
                    disabled={locked || busy}
                    onChange={(next) => save.setContent(withField(save.content, "reason", next))}
                  />
                </>
              )}
              {type === "MULTIPLE_STATEMENT" && (
                <ItemsField
                  content={save.content}
                  field="statements"
                  prefix="S"
                  legend="Statements"
                  nameOf={(index) => `Statement ${index + 1}`}
                  addLabel="Add statement"
                  disabled={locked || busy}
                  onChange={save.setContent}
                />
              )}
              {type === "MATCHING" && (
                <MatchingField
                  content={save.content}
                  disabled={locked || busy}
                  onChange={save.setContent}
                />
              )}
              {hasOptions && (
                <OptionsField
                  content={save.content}
                  disabled={locked || busy}
                  onChange={save.setContent}
                />
              )}
              {typed && (
                <TypedAnswerField
                  content={save.content}
                  disabled={locked || busy}
                  onChange={save.setContent}
                />
              )}
              <BlocksField
                label="Solution (optional)"
                blocks={blocksOf(save.content.solution)}
                disabled={locked || busy}
                onChange={(next) => save.setContent(withField(save.content, "solution", next))}
              />
              <MetadataField
                content={save.content}
                disabled={locked || busy}
                onChange={save.setContent}
              />
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                The preview shows what is saved so far.
              </p>{" "}
            </div>
          ) : (
            <div
              role="tabpanel"
              id="panel-preview"
              aria-labelledby="tab-preview"
              className="grid gap-4"
            >
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={reveal}
                  onChange={(event) => setReveal(event.target.checked)}
                />
                Show the answer and solution
              </label>
              <div className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
                <QuestionPreview
                  content={save.content}
                  reveal={reveal}
                  passage={passage.state === "ready" ? passage.revision.content : undefined}
                />
              </div>
            </div>
          )}
        </div>
        <FindingsPanel findings={save.findings} />
      </div>
    </div>
  );
}
