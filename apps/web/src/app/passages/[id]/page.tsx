"use client";

import type { components } from "@qbank/api-client";
import { Blocks } from "@qbank/content-renderer";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { BlocksField } from "@/components/blocks-field";
import { FindingsPanel } from "@/components/findings-panel";
import { api, errorMessage, ifMatch } from "@/lib/api";
import { FORMATS, blocksOf, emptyContent, formatLabel, withField } from "@/lib/question-content";
import { useAutosave, type SaveState } from "@/lib/use-autosave";
import { NETWORK, useAdd } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Passage = components["schemas"]["PassageOut"];
type Checkpoint = components["schemas"]["PassageCheckpointOut"];
type Children = components["schemas"]["PassageChildList"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";

/**
 * The passage editor (D-14): a title and the shared text, saved by itself a moment after you stop
 * typing; checkpoints that freeze it; and the questions that sit under it. A question is written
 * under one saved checkpoint, so editing the passage later never changes what a question was
 * written with.
 */
export default function PassagePage() {
  // useParams reads the address at request time, so the page needs a boundary to wait behind.
  return (
    <Suspense fallback={<main className="p-8">Loading…</main>}>
      <PassageScreen />
    </Suspense>
  );
}

function PassageScreen() {
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
    <AppShell me={me} current="passages" onSignOut={signOut} onStopActing={stopActing}>
      {shellError && (
        <p role="alert" className={`mb-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <Loader id={id} />
    </AppShell>
  );
}

/** Reads the passage, then hands it to the editor (which owns it from then on). */
function Loader({ id }: { id: string }) {
  const [passage, setPassage] = useState<Passage | null>(null);
  const [problem, setProblem] = useState<"missing" | "failed" | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      let result;
      try {
        result = await api().GET("/api/v1/passages/{passage_id}", {
          params: { path: { passage_id: id } },
        });
      } catch {
        if (!cancelled) setProblem("failed");
        return;
      }
      if (cancelled) return;
      if (result.data) setPassage(result.data);
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
          This passage does not exist, or you may not open it.
        </p>
        <Link href="/passages" className="mt-4 inline-block underline">
          Back to passages
        </Link>
      </div>
    );
  }
  if (problem === "failed") {
    return (
      <div>
        <p role="alert" className={ALERT}>
          The passage could not be loaded.
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
  if (!passage) return <p>Loading…</p>;
  return <Editor key={passage.id} initial={passage} />;
}

const STATE_TEXT: Record<SaveState, string> = {
  saved: "All changes saved",
  dirty: "Unsaved changes…",
  saving: "Saving…",
  failed: "Not saved",
  conflict: "Not saved",
  archived: "Archived",
};

function Editor({ initial }: { initial: Passage }) {
  const save = useAutosave(initial, "passages");
  const [tab, setTab] = useState<"edit" | "preview">("edit");
  const [checkpoint, setCheckpoint] = useState<Checkpoint | null>(initial.latest_checkpoint);
  const [notice, setNotice] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const locked = save.state === "conflict";
  const title = typeof save.content.title === "string" ? save.content.title : "";

  async function saveCheckpoint() {
    if (busy) return;
    setBusy(true);
    setProblem(null);
    setNotice(null);
    try {
      if (!(await save.flush())) {
        setProblem("Your changes could not be saved yet, so nothing else was done.");
        return;
      }
      const { data, error, response } = await api().POST(
        "/api/v1/passages/{passage_id}/checkpoints",
        {
          params: {
            path: { passage_id: initial.id },
            header: { "If-Match": ifMatch(save.revision.current) },
          },
        },
      );
      if (data) {
        save.adopt(data);
        setCheckpoint(data.latest_checkpoint);
        setNotice("Checkpoint saved. Questions can now be added under it.");
      } else if (response.status === 412) {
        save.markConflict();
      } else {
        setProblem(errorMessage(error as never, response.status));
      }
    } catch {
      setProblem(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  async function reload() {
    const result = await api().GET("/api/v1/passages/{passage_id}", {
      params: { path: { passage_id: initial.id } },
    });
    if (result.data) {
      save.adopt(result.data);
      setCheckpoint(result.data.latest_checkpoint);
      setProblem(null);
    } else {
      setProblem(errorMessage(result.error as never, result.response.status));
    }
  }

  const status = save.state === "saved" ? STATE_TEXT.saved : STATE_TEXT[save.state];

  return (
    <div className="grid max-w-5xl gap-6">
      <div>
        <Link
          href="/passages"
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
          Back to passages
        </Link>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">{title || "Untitled passage"}</h1>
          <button
            type="button"
            className={PRIMARY}
            disabled={busy || locked}
            onClick={() => void saveCheckpoint()}
          >
            Save checkpoint
          </button>
        </div>
        <p
          role="status"
          aria-live="polite"
          className="mt-1 text-sm text-zinc-600 dark:text-zinc-400"
        >
          {status} ·{" "}
          {checkpoint ? `newest checkpoint: ${checkpoint.number}` : "no checkpoint saved yet"}
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
        <div className="grid gap-6">
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
              <label className="grid gap-1 text-sm">
                <span className="font-medium">Title</span>
                <input
                  type="text"
                  value={title}
                  maxLength={200}
                  disabled={locked || busy}
                  className={FIELD}
                  onChange={(event) =>
                    save.setContent(withField(save.content, "title", event.target.value))
                  }
                />
              </label>
              <BlocksField
                label="Passage text"
                blocks={blocksOf(save.content.body)}
                disabled={locked || busy}
                onChange={(next) => save.setContent(withField(save.content, "body", next))}
              />
            </div>
          ) : (
            <div
              role="tabpanel"
              id="panel-preview"
              aria-labelledby="tab-preview"
              className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800"
            >
              <div className="qb-question">
                {title && <h2 className="mb-2 text-lg font-medium">{title}</h2>}
                <Blocks blocks={save.content.body} />
              </div>
            </div>
          )}

          <PassageChildren passageId={initial.id} checkpoint={checkpoint} />
        </div>
        <FindingsPanel findings={save.findings} />
      </div>
    </div>
  );
}

/** The questions under the passage, and a way to add one under the newest checkpoint. */
function PassageChildren({
  passageId,
  checkpoint,
}: {
  passageId: string;
  checkpoint: Checkpoint | null;
}) {
  const router = useRouter();
  const [found, setFound] = useState<Children | null>(null);
  const [failed, setFailed] = useState(false);
  const [type, setType] = useState("SCQ");
  const checkpointId = checkpoint?.id;

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const { data } = await api().GET("/api/v1/passages/{passage_id}/children", {
          params: { path: { passage_id: passageId } },
        });
        if (cancelled) return;
        if (data) {
          setFound(data);
          setFailed(false);
        } else {
          setFailed(true);
        }
      } catch {
        if (!cancelled) setFailed(true);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [passageId, checkpointId]);

  const adder = useAdd<components["schemas"]["QuestionOut"]>(
    (body, key) =>
      api().POST("/api/v1/questions", {
        body: body as components["schemas"]["CreateQuestion"],
        params: { header: { "Idempotency-Key": key } },
      }),
    (created) => router.push(`/questions/${created.id}`),
  );

  const children = found?.data ?? [];
  // From the server, which counts every question under the passage, not only the listed ones.
  const nextNumber = found?.next_number ?? 1;

  return (
    <section aria-label="Questions under this passage" className="grid gap-3">
      <h2 className="text-lg font-medium">Questions under this passage</h2>
      {failed && (
        <p role="alert" className={ALERT}>
          The questions could not be loaded.
        </p>
      )}
      {found && children.length === 0 && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">No questions under it yet.</p>
      )}
      {children.length > 0 && (
        <ul className="divide-y divide-zinc-200 rounded-md border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {children.map((child) => (
            <li key={child.question_id}>
              <Link
                href={`/questions/${child.question_id}`}
                className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900"
              >
                <span>
                  {child.ordinal !== null && <span className="font-medium">{child.ordinal}. </span>}
                  <span className="font-mono font-medium">{child.code}</span>{" "}
                  <span className="text-zinc-600 dark:text-zinc-400">
                    {formatLabel(child.question_type)}
                    {child.archived ? " · archived" : ""}
                  </span>
                </span>
                <span className="text-xs text-zinc-600 dark:text-zinc-400">
                  {child.is_current
                    ? `Written with checkpoint ${child.pinned_checkpoint_number}`
                    : `On checkpoint ${child.pinned_checkpoint_number}; newest is ${found?.latest_checkpoint_number}`}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {found && found.hidden_count > 0 && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          {found.hidden_count} more {found.hidden_count === 1 ? "question is" : "questions are"}{" "}
          drafts by other people that you may not open.
        </p>
      )}
      {found?.truncated && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Only the first questions are shown.
        </p>
      )}

      {checkpoint && !found ? (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">Loading…</p>
      ) : checkpoint ? (
        <form
          aria-label="Add a question under this passage"
          className="flex flex-wrap items-end gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            void adder.add({
              content: {
                ...emptyContent(type),
                context: { passage_revision_id: checkpoint.id, ordinal: nextNumber },
              },
            });
          }}
        >
          <label className="grid gap-1 text-sm">
            <span>Format of the new question</span>
            <select
              value={type}
              onChange={(event) => setType(event.target.value)}
              className={FIELD}
            >
              {FORMATS.map((format) => (
                <option key={format.value} value={format.value}>
                  {format.label}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={adder.adding} className={BUTTON}>
            {adder.adding ? "Adding…" : `Add question ${nextNumber}`}
          </button>
        </form>
      ) : (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Save a checkpoint first: a question is written under a saved checkpoint of the passage.
        </p>
      )}
      {adder.addError && (
        <p role="alert" className={ALERT}>
          {adder.addError}
        </p>
      )}
    </section>
  );
}
