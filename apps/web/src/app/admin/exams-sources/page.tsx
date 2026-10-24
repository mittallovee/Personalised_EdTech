"use client";

import type { components } from "@qbank/api-client";
import { useCallback, useState, type ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { ConfirmPanel } from "@/components/confirm-panel";
import { StatusNotice } from "@/components/status-notice";
import { api, ifMatch } from "@/lib/api";
import { canManageCatalogues } from "@/lib/syllabus";
import { useAdd, useCatalogueList, useChanges, STALE } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Exam = components["schemas"]["ExamOut"];
type Source = components["schemas"]["SourceOut"];
type SourceKind = Source["kind"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

const SOURCE_KINDS: { value: SourceKind; label: string }[] = [
  { value: "BOOK", label: "Book" },
  { value: "MODULE", label: "Module" },
  { value: "TEST_SERIES", label: "Test series" },
  { value: "PYQ_PAPER", label: "Previous-year paper" },
  { value: "OTHER", label: "Other" },
];
const kindLabel = (kind: SourceKind) => SOURCE_KINDS.find((k) => k.value === kind)?.label ?? kind;

/**
 * Exams and sources (C-11, C-13): the exams questions were asked in ("JEE Main") and the sources
 * they came from (books, modules, test series, previous-year papers). Owner and admins add,
 * rename, retire and restore. The API decides who may do what.
 */
export default function ExamsAndSourcesPage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const canManage = me ? canManageCatalogues(me) : false;

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
    <AppShell me={me} current="exams-sources" onSignOut={signOut} onStopActing={stopActing}>
      <h1 className="text-2xl font-semibold">Exams &amp; sources</h1>
      <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        Nothing is ever deleted: a retired exam or source stays on old questions but cannot be
        chosen for new ones.
      </p>
      {shellError && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <div className="mt-8 grid max-w-2xl gap-12">
        <ExamsSection canManage={canManage} />
        <SourcesSection canManage={canManage} />
      </div>
    </AppShell>
  );
}

/** What the two sections share: a name, retired or not, and the buttons to change it. */
function Row({
  name,
  detail,
  retired,
  canManage,
  panel,
  busy,
  locked,
  error,
  noun,
  onOpenPanel,
  onRetire,
  onRestore,
  edit,
}: {
  name: string;
  detail: string;
  retired: boolean;
  canManage: boolean;
  panel: "edit" | "retire" | null;
  busy: boolean;
  locked: boolean;
  error: string | null;
  noun: string;
  onOpenPanel: (panel: "edit" | "retire" | null) => void;
  onRetire: () => void;
  onRestore: () => void;
  edit: ReactNode;
}) {
  return (
    <li className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <span className={`font-medium ${retired ? "text-zinc-500 line-through" : ""}`}>
            {name}
          </span>
          {retired && (
            <span className="ml-2 rounded bg-zinc-200 px-2 py-0.5 text-xs dark:bg-zinc-800">
              Retired
            </span>
          )}
          {detail && <p className="text-sm text-zinc-600 dark:text-zinc-400">{detail}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          {canManage && !retired && panel !== "edit" && (
            <button type="button" onClick={() => onOpenPanel("edit")} className={BUTTON}>
              Edit
            </button>
          )}
          {canManage && !retired && panel !== "retire" && (
            <button type="button" onClick={() => onOpenPanel("retire")} className={BUTTON}>
              Retire
            </button>
          )}
          {canManage && retired && (
            <button type="button" disabled={busy || locked} onClick={onRestore} className={BUTTON}>
              Restore
            </button>
          )}
        </div>
      </div>
      {panel === "edit" && edit}
      {panel === "retire" && (
        <ConfirmPanel
          question={`Retire ${name}?`}
          detail={`It can no longer be chosen for new questions, and nothing is deleted: questions that already use this ${noun} keep it, and you can restore it any time.`}
          confirmLabel="Retire"
          busy={busy || locked}
          onConfirm={onRetire}
          onCancel={() => onOpenPanel(null)}
        />
      )}
      {error && (
        <p role="alert" className={`mt-3 ${ALERT}`}>
          {error}
        </p>
      )}
    </li>
  );
}

function Status({
  state,
  error,
  denied,
  empty,
  onRetry,
  stale,
}: {
  state: "loading" | "ready" | "denied" | "failed";
  error: string | null;
  denied: string;
  empty: string | null;
  onRetry: () => void;
  stale: boolean;
}) {
  return (
    <>
      {stale && (
        <p role="alert" className={ALERT}>
          {STALE}
        </p>
      )}
      {state === "denied" && (
        <p role="alert" className={ALERT}>
          {denied}
        </p>
      )}
      {state === "failed" && (
        <>
          <p role="alert" className={ALERT}>
            {error}
          </p>
          <button type="button" onClick={onRetry} className="underline">
            Try again
          </button>
        </>
      )}
      {state === "loading" && <p>Loading…</p>}
      {empty && <p className="text-zinc-600 dark:text-zinc-400">{empty}</p>}
    </>
  );
}

function ExamsSection({ canManage }: { canManage: boolean }) {
  const [open, setOpen] = useState<{ id: string; panel: "edit" | "retire" } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newCode, setNewCode] = useState("");

  const fetchPage = useCallback(
    (cursor: string | null) =>
      api().GET("/api/v1/exams", {
        params: { query: { limit: 100, ...(cursor ? { cursor } : {}) } },
      }),
    [],
  );
  const list = useCatalogueList<Exam>(fetchPage);
  const changes = useChanges<Exam>(list.replace, list.reload);
  const adder = useAdd<Exam>(
    (body, key) =>
      api().POST("/api/v1/exams", {
        body: body as components["schemas"]["CreateExam"],
        params: { header: { "Idempotency-Key": key } },
      }),
    (created) => {
      setNotice(`${created.name} was added.`);
      setNewName("");
      setNewCode("");
      void list.reload();
    },
  );
  const closePanelOf = (id: string) => setOpen((current) => (current?.id === id ? null : current));

  const save = (exam: Exam, body: components["schemas"]["UpdateExam"]) =>
    changes.change(
      exam,
      () =>
        api().PATCH("/api/v1/exams/{exam_id}", {
          params: { path: { exam_id: exam.id }, header: { "If-Match": ifMatch(exam.revision) } },
          body,
        }),
      (updated) => {
        closePanelOf(updated.id);
        setNotice(`${updated.name} was saved.`);
        void list.reload();
      },
      () => closePanelOf(exam.id),
    );
  const setRetired = (exam: Exam, retire: boolean) =>
    changes.change(
      exam,
      () =>
        api().POST(
          retire ? "/api/v1/exams/{exam_id}/deprecate" : "/api/v1/exams/{exam_id}/restore",
          {
            params: { path: { exam_id: exam.id }, header: { "If-Match": ifMatch(exam.revision) } },
          },
        ),
      (updated) => {
        closePanelOf(updated.id);
        setNotice(`${updated.name} was ${retire ? "retired" : "restored"}.`);
      },
      () => closePanelOf(exam.id),
    );

  return (
    <section aria-labelledby="exams-heading" className="space-y-4">
      <h2 id="exams-heading" className="text-lg font-medium">
        Exams
      </h2>
      {notice && <StatusNotice>{notice}</StatusNotice>}
      <Status
        state={list.state}
        error={list.listError}
        denied="You don't have access to the exams."
        empty={list.state === "ready" && list.items.length === 0 ? "No exams yet." : null}
        onRetry={list.retry}
        stale={changes.stale}
      />
      {list.state === "ready" && list.items.length > 0 && (
        <ul aria-label="Exams" className="space-y-3">
          {list.items.map((exam) => (
            <Row
              key={exam.id}
              name={exam.name}
              detail={exam.short_code ? `Short code ${exam.short_code}` : ""}
              retired={exam.state === "DEPRECATED"}
              canManage={canManage}
              noun="exam"
              panel={open?.id === exam.id ? open.panel : null}
              busy={changes.busyId === exam.id}
              locked={changes.busyId !== null && changes.busyId !== exam.id}
              error={changes.itemError?.id === exam.id ? changes.itemError.message : null}
              onOpenPanel={(panel) => {
                changes.setItemError(null);
                setOpen(panel ? { id: exam.id, panel } : null);
              }}
              onRetire={() => void setRetired(exam, true)}
              onRestore={() => void setRetired(exam, false)}
              edit={
                <ExamEditForm
                  key={`${exam.id}-${exam.revision}`}
                  exam={exam}
                  busy={changes.busyId === exam.id}
                  locked={changes.busyId !== null && changes.busyId !== exam.id}
                  onSave={(body) => void save(exam, body)}
                  onCancel={() => setOpen(null)}
                />
              }
            />
          ))}
        </ul>
      )}
      {list.nextCursor && list.state === "ready" && (
        <button type="button" onClick={() => void list.showMore()} className={BUTTON}>
          Show more exams
        </button>
      )}
      {canManage && list.state === "ready" && (
        <form
          aria-label="Add an exam"
          onSubmit={(e) => {
            e.preventDefault();
            const code = newCode.trim();
            void adder.add({ name: newName.trim(), ...(code ? { short_code: code } : {}) });
          }}
          className="space-y-3 rounded-lg border border-dashed border-zinc-300 p-4 dark:border-zinc-700"
        >
          <h3 className="font-medium">Add an exam</h3>
          <label className="block text-sm font-medium">
            Name
            <input
              name="name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              required
              maxLength={200}
              className={`${FIELD} mt-1`}
            />
          </label>
          <label className="block text-sm font-medium">
            Short code (optional)
            <input
              name="short_code"
              value={newCode}
              onChange={(e) => setNewCode(e.target.value)}
              maxLength={20}
              className={`${FIELD} mt-1`}
            />
          </label>
          {adder.addError && (
            <p role="alert" className={ALERT}>
              {adder.addError}
            </p>
          )}
          <button type="submit" disabled={adder.adding} className={PRIMARY}>
            {adder.adding ? "Adding…" : "Add exam"}
          </button>
        </form>
      )}
    </section>
  );
}

function ExamEditForm({
  exam,
  busy,
  locked,
  onSave,
  onCancel,
}: {
  exam: Exam;
  busy: boolean;
  locked: boolean;
  onSave: (body: components["schemas"]["UpdateExam"]) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(exam.name);
  const [code, setCode] = useState(exam.short_code ?? "");
  return (
    <form
      aria-label={`Edit ${exam.name}`}
      className="mt-3 space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        // An empty code removes it (null); sending nothing would keep it.
        onSave({ name: name.trim(), short_code: code.trim() || null });
      }}
    >
      <label className="block text-sm font-medium">
        Name
        <input
          name="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={200}
          className={`${FIELD} mt-1`}
        />
      </label>
      <label className="block text-sm font-medium">
        Short code (optional)
        <input
          name="short_code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          maxLength={20}
          className={`${FIELD} mt-1`}
        />
      </label>
      <div className="flex gap-2">
        <button type="submit" disabled={busy || locked} className={PRIMARY}>
          {busy ? "Saving…" : "Save"}
        </button>
        <button type="button" onClick={onCancel} className={BUTTON}>
          Cancel
        </button>
      </div>
    </form>
  );
}

function SourcesSection({ canManage }: { canManage: boolean }) {
  const [open, setOpen] = useState<{ id: string; panel: "edit" | "retire" } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [kindFilter, setKindFilter] = useState<SourceKind | "">("");
  const [newKind, setNewKind] = useState<SourceKind>("BOOK");
  const [newName, setNewName] = useState("");

  const fetchPage = useCallback(
    (cursor: string | null) =>
      api().GET("/api/v1/sources", {
        params: {
          query: {
            limit: 100,
            ...(kindFilter ? { kind: kindFilter } : {}),
            ...(cursor ? { cursor } : {}),
          },
        },
      }),
    [kindFilter],
  );
  const list = useCatalogueList<Source>(fetchPage);
  const changes = useChanges<Source>(list.replace, list.reload);
  const adder = useAdd<Source>(
    (body, key) =>
      api().POST("/api/v1/sources", {
        body: body as components["schemas"]["CreateSource"],
        params: { header: { "Idempotency-Key": key } },
      }),
    (created) => {
      setNotice(`${created.name} was added.`);
      setNewName("");
      void list.reload();
    },
  );
  const closePanelOf = (id: string) => setOpen((current) => (current?.id === id ? null : current));

  const save = (source: Source, name: string) =>
    changes.change(
      source,
      () =>
        api().PATCH("/api/v1/sources/{source_id}", {
          params: {
            path: { source_id: source.id },
            header: { "If-Match": ifMatch(source.revision) },
          },
          body: { name },
        }),
      (updated) => {
        closePanelOf(updated.id);
        setNotice(`${updated.name} was saved.`);
        void list.reload();
      },
      () => closePanelOf(source.id),
    );
  const setRetired = (source: Source, retire: boolean) =>
    changes.change(
      source,
      () =>
        api().POST(
          retire ? "/api/v1/sources/{source_id}/deprecate" : "/api/v1/sources/{source_id}/restore",
          {
            params: {
              path: { source_id: source.id },
              header: { "If-Match": ifMatch(source.revision) },
            },
          },
        ),
      (updated) => {
        closePanelOf(updated.id);
        setNotice(`${updated.name} was ${retire ? "retired" : "restored"}.`);
      },
      () => closePanelOf(source.id),
    );

  return (
    <section aria-labelledby="sources-heading" className="space-y-4">
      <h2 id="sources-heading" className="text-lg font-medium">
        Sources
      </h2>
      <label className="block text-sm font-medium">
        Show
        <select
          name="kind_filter"
          value={kindFilter}
          onChange={(e) => {
            setKindFilter(e.target.value as SourceKind | "");
            setOpen(null);
            setNotice(null);
          }}
          className={`${FIELD} mt-1`}
        >
          <option value="">All kinds of source</option>
          {SOURCE_KINDS.map((k) => (
            <option key={k.value} value={k.value}>
              {k.label}
            </option>
          ))}
        </select>
      </label>
      {notice && <StatusNotice>{notice}</StatusNotice>}
      <Status
        state={list.state}
        error={list.listError}
        denied="You don't have access to the sources."
        empty={list.state === "ready" && list.items.length === 0 ? "No sources yet." : null}
        onRetry={list.retry}
        stale={changes.stale}
      />
      {list.state === "ready" && list.items.length > 0 && (
        <ul aria-label="Sources" className="space-y-3">
          {list.items.map((source) => (
            <Row
              key={source.id}
              name={source.name}
              detail={kindLabel(source.kind)}
              retired={source.state === "DEPRECATED"}
              canManage={canManage}
              noun="source"
              panel={open?.id === source.id ? open.panel : null}
              busy={changes.busyId === source.id}
              locked={changes.busyId !== null && changes.busyId !== source.id}
              error={changes.itemError?.id === source.id ? changes.itemError.message : null}
              onOpenPanel={(panel) => {
                changes.setItemError(null);
                setOpen(panel ? { id: source.id, panel } : null);
              }}
              onRetire={() => void setRetired(source, true)}
              onRestore={() => void setRetired(source, false)}
              edit={
                <SourceEditForm
                  key={`${source.id}-${source.revision}`}
                  source={source}
                  busy={changes.busyId === source.id}
                  locked={changes.busyId !== null && changes.busyId !== source.id}
                  onSave={(name) => void save(source, name)}
                  onCancel={() => setOpen(null)}
                />
              }
            />
          ))}
        </ul>
      )}
      {list.nextCursor && list.state === "ready" && (
        <button type="button" onClick={() => void list.showMore()} className={BUTTON}>
          Show more sources
        </button>
      )}
      {canManage && list.state === "ready" && (
        <form
          aria-label="Add a source"
          onSubmit={(e) => {
            e.preventDefault();
            void adder.add({ kind: newKind, name: newName.trim() });
          }}
          className="space-y-3 rounded-lg border border-dashed border-zinc-300 p-4 dark:border-zinc-700"
        >
          <h3 className="font-medium">Add a source</h3>
          <label className="block text-sm font-medium">
            Kind
            <select
              name="kind"
              value={newKind}
              onChange={(e) => setNewKind(e.target.value as SourceKind)}
              className={`${FIELD} mt-1`}
            >
              {SOURCE_KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium">
            Name
            <input
              name="name"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              required
              maxLength={200}
              className={`${FIELD} mt-1`}
            />
          </label>
          {adder.addError && (
            <p role="alert" className={ALERT}>
              {adder.addError}
            </p>
          )}
          <button type="submit" disabled={adder.adding} className={PRIMARY}>
            {adder.adding ? "Adding…" : "Add source"}
          </button>
        </form>
      )}
    </section>
  );
}

function SourceEditForm({
  source,
  busy,
  locked,
  onSave,
  onCancel,
}: {
  source: Source;
  busy: boolean;
  locked: boolean;
  onSave: (name: string) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(source.name);
  return (
    <form
      aria-label={`Edit ${source.name}`}
      className="mt-3 space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        onSave(name.trim());
      }}
    >
      <label className="block text-sm font-medium">
        Name (the kind, {kindLabel(source.kind).toLowerCase()}, never changes)
        <input
          name="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={200}
          className={`${FIELD} mt-1`}
        />
      </label>
      <div className="flex gap-2">
        <button type="submit" disabled={busy || locked} className={PRIMARY}>
          {busy ? "Saving…" : "Save"}
        </button>
        <button type="button" onClick={onCancel} className={BUTTON}>
          Cancel
        </button>
      </div>
    </form>
  );
}
