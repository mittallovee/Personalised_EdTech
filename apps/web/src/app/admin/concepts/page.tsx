"use client";

import type { components } from "@qbank/api-client";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { ConfirmPanel } from "@/components/confirm-panel";
import { StatusNotice } from "@/components/status-notice";
import { api, ifMatch } from "@/lib/api";
import { canManageCatalogues, type Language, type Node } from "@/lib/syllabus";
import { useAdd, useCatalogueList, useChanges, STALE } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Concept = components["schemas"]["ConceptOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/** One alias per line in the box; blank lines and repeats are dropped. */
function parseAliases(text: string): string[] {
  const seen = new Set<string>();
  for (const line of text.split("\n")) {
    const alias = line.trim();
    if (alias) seen.add(alias);
  }
  return [...seen];
}

type Subject = { id: string; label: string };

/** One page of the items of one kind. */
async function nodePage(
  kind: "CLASS" | "SUBJECT",
  cursor: string | null,
): Promise<{ items: Node[]; next: string | null }> {
  const result = await api().GET("/api/v1/taxonomy/nodes", {
    params: { query: { kind, limit: 100, ...(cursor ? { cursor } : {}) } },
  });
  if (!result.data) throw new Error("could not list the syllabus");
  return { items: result.data.data, next: result.data.page.next_cursor ?? null };
}

/** Every item of one kind, page by page. */
async function listNodes(kind: "CLASS" | "SUBJECT"): Promise<Node[]> {
  const all: Node[] = [];
  let cursor: string | null = null;
  do {
    const page: { items: Node[]; next: string | null } = await nodePage(kind, cursor);
    all.push(...page.items);
    cursor = page.next;
  } while (cursor);
  return all;
}

/**
 * Concepts (C-02, C-03): the ideas questions are tagged with ("Newton's second law"), kept per
 * subject, each with a name, names in other languages and aliases (other ways people search for
 * it). Owner and admins add, edit, retire and restore. The API decides who may do what.
 */
export default function ConceptsPage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const [subjects, setSubjects] = useState<Subject[] | null>(null);
  const [subjectsError, setSubjectsError] = useState<string | null>(null);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [subjectId, setSubjectId] = useState("");
  const canManage = me ? canManageCatalogues(me) : false;

  // The subjects to choose from, each named with its class ("Class 11 › Physics").
  useEffect(() => {
    void (async () => {
      try {
        const classes = new Map((await listNodes("CLASS")).map((c) => [c.id, c.name]));
        const found: Subject[] = (await listNodes("SUBJECT"))
          .filter((s) => s.state === "ACTIVE")
          .map((s) => ({
            id: s.id,
            label: `${classes.get(s.parent_id ?? "") ?? "Class"} › ${s.name}`,
          }));
        setSubjects(found);
      } catch {
        setSubjectsError("Could not load the subjects. Check your connection and reload.");
      }
    })();
    void (async () => {
      try {
        const { data } = await api().GET("/api/v1/languages");
        if (data) setLanguages(data);
      } catch {
        // Names in other languages are optional; the page works without them.
      }
    })();
  }, []);

  function chooseSubject(id: string) {
    setSubjectId(id);
  }

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

  const subjectLabel = subjects?.find((s) => s.id === subjectId)?.label;
  return (
    <AppShell me={me} current="concepts" onSignOut={signOut} onStopActing={stopActing}>
      <h1 className="text-2xl font-semibold">Concepts</h1>
      <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        The ideas questions are tagged with, kept per subject. An alias is another way people write
        or search for the same idea. Nothing is ever deleted: a retired concept stays on old
        questions but cannot be chosen for new ones.
      </p>
      {shellError && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}

      <div className="mt-6 max-w-2xl space-y-4">
        {subjectsError && (
          <p role="alert" className={ALERT}>
            {subjectsError}
          </p>
        )}
        {!subjects && !subjectsError && <p>Loading…</p>}
        {subjects && subjects.length === 0 && (
          <p className="text-zinc-600 dark:text-zinc-400">
            There are no subjects yet. Add a subject in the Syllabus first.
          </p>
        )}
        {subjects && subjects.length > 0 && (
          <label className="block text-sm font-medium">
            Subject
            <select
              name="subject"
              value={subjectId}
              onChange={(e) => chooseSubject(e.target.value)}
              className={`${FIELD} mt-1`}
            >
              <option value="">Choose a subject…</option>
              {subjects.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        )}

        {subjectId && (
          <SubjectConcepts
            key={subjectId}
            subjectId={subjectId}
            title={subjectLabel ?? ""}
            languages={languages}
            canManage={canManage}
          />
        )}
      </div>
    </AppShell>
  );
}

/** The concepts of one subject: search, list, add, edit, retire and restore. */
function SubjectConcepts({
  subjectId,
  title,
  languages,
  canManage,
}: {
  subjectId: string;
  title: string;
  languages: Language[];
  canManage: boolean;
}) {
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<{ id: string; panel: "edit" | "retire" } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newAliases, setNewAliases] = useState("");

  const fetchPage = useCallback(
    (cursor: string | null) =>
      api().GET("/api/v1/taxonomy/concepts", {
        params: {
          query: {
            subject_id: subjectId,
            limit: 100,
            ...(query ? { q: query } : {}),
            ...(cursor ? { cursor } : {}),
          },
        },
      }),
    [subjectId, query],
  );
  const list = useCatalogueList<Concept>(fetchPage);
  const changes = useChanges<Concept>(list.replace, list.reload);
  const adder = useAdd<Concept>(
    (body, key) =>
      api().POST("/api/v1/taxonomy/concepts", {
        body: body as components["schemas"]["CreateConcept"],
        params: { header: { "Idempotency-Key": key } },
      }),
    (created) => {
      setNotice(`${created.name} was added.`);
      setNewName("");
      setNewAliases("");
      void list.reload();
    },
  );

  const closePanelOf = (id: string) => setOpen((current) => (current?.id === id ? null : current));

  const save = (concept: Concept, body: components["schemas"]["UpdateConcept"]) =>
    changes.change(
      concept,
      () =>
        api().PATCH("/api/v1/taxonomy/concepts/{concept_id}", {
          params: {
            path: { concept_id: concept.id },
            header: { "If-Match": ifMatch(concept.revision) },
          },
          body,
        }),
      (updated) => {
        closePanelOf(updated.id);
        setNotice(`${updated.name} was saved.`);
        void list.reload();
      },
      () => closePanelOf(concept.id),
    );

  const setRetired = (concept: Concept, retire: boolean) =>
    changes.change(
      concept,
      () =>
        api().POST(
          retire
            ? "/api/v1/taxonomy/concepts/{concept_id}/deprecate"
            : "/api/v1/taxonomy/concepts/{concept_id}/restore",
          {
            params: {
              path: { concept_id: concept.id },
              header: { "If-Match": ifMatch(concept.revision) },
            },
          },
        ),
      (updated) => {
        closePanelOf(updated.id);
        setNotice(`${updated.name} was ${retire ? "retired" : "restored"}.`);
      },
      () => closePanelOf(concept.id),
    );

  return (
    <>
      <h2 className="text-lg font-medium">{title}</h2>
      <form
        role="search"
        aria-label="Search concepts"
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(search.trim());
        }}
        className="flex gap-2"
      >
        <label className="flex-1 text-sm font-medium">
          Search names and aliases
          <input
            name="q"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            maxLength={200}
            className={`${FIELD} mt-1`}
          />
        </label>
        <button type="submit" className={`${BUTTON} self-end`}>
          Search
        </button>
      </form>

      {notice && <StatusNotice>{notice}</StatusNotice>}
      {changes.stale && (
        <p role="alert" className={ALERT}>
          {STALE}
        </p>
      )}
      {list.state === "denied" && (
        <p role="alert" className={ALERT}>
          You don&apos;t have access to the concepts.
        </p>
      )}
      {list.state === "failed" && (
        <>
          <p role="alert" className={ALERT}>
            {list.listError}
          </p>
          <button type="button" onClick={list.retry} className="underline">
            Try again
          </button>
        </>
      )}
      {list.state === "loading" && <p>Loading…</p>}
      {list.state === "ready" && list.items.length === 0 && (
        <p className="text-zinc-600 dark:text-zinc-400">
          {query ? "No concept matches that search." : "No concepts yet."}
        </p>
      )}
      {list.state === "ready" && list.items.length > 0 && (
        <ul aria-label="Concepts" className="space-y-3">
          {list.items.map((concept) => (
            <ConceptItem
              key={concept.id}
              concept={concept}
              languages={languages}
              canManage={canManage}
              panel={open?.id === concept.id ? open.panel : null}
              busy={changes.busyId === concept.id}
              locked={changes.busyId !== null && changes.busyId !== concept.id}
              error={changes.itemError?.id === concept.id ? changes.itemError.message : null}
              onOpenPanel={(panel) => {
                changes.setItemError(null);
                setOpen(panel ? { id: concept.id, panel } : null);
              }}
              onSave={(body) => void save(concept, body)}
              onRetire={() => void setRetired(concept, true)}
              onRestore={() => void setRetired(concept, false)}
            />
          ))}
        </ul>
      )}
      {list.nextCursor && list.state === "ready" && (
        <button type="button" onClick={() => void list.showMore()} className={BUTTON}>
          Show more
        </button>
      )}

      {canManage && list.state === "ready" && (
        <form
          aria-label="Add a concept"
          onSubmit={(e) => {
            e.preventDefault();
            void adder.add({
              subject_id: subjectId,
              name: newName.trim(),
              aliases: parseAliases(newAliases),
            });
          }}
          className="space-y-3 rounded-lg border border-dashed border-zinc-300 p-4 dark:border-zinc-700"
        >
          <h3 className="font-medium">Add a concept</h3>
          <label className="block text-sm font-medium">
            Name (English)
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
            Aliases (one per line, optional)
            <textarea
              name="aliases"
              value={newAliases}
              onChange={(e) => setNewAliases(e.target.value)}
              rows={3}
              className={`${FIELD} mt-1`}
            />
          </label>
          {adder.addError && (
            <p role="alert" className={ALERT}>
              {adder.addError}
            </p>
          )}
          <button type="submit" disabled={adder.adding} className={PRIMARY}>
            {adder.adding ? "Adding…" : "Add concept"}
          </button>
        </form>
      )}
    </>
  );
}

function ConceptItem({
  concept,
  languages,
  canManage,
  panel,
  busy,
  locked,
  error,
  onOpenPanel,
  onSave,
  onRetire,
  onRestore,
}: {
  concept: Concept;
  languages: Language[];
  canManage: boolean;
  panel: "edit" | "retire" | null;
  busy: boolean;
  locked: boolean;
  error: string | null;
  onOpenPanel: (panel: "edit" | "retire" | null) => void;
  onSave: (body: components["schemas"]["UpdateConcept"]) => void;
  onRetire: () => void;
  onRestore: () => void;
}) {
  const retired = concept.state === "DEPRECATED";
  const shown = Object.entries(concept.labels)
    .map(([tag, label]) => `${languages.find((l) => l.tag === tag)?.english_name ?? tag}: ${label}`)
    .join(" · ");
  return (
    <li className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <span className={`font-medium ${retired ? "text-zinc-500 line-through" : ""}`}>
            {concept.name}
          </span>
          {retired && (
            <span className="ml-2 rounded bg-zinc-200 px-2 py-0.5 text-xs dark:bg-zinc-800">
              Retired
            </span>
          )}
          {shown && <p className="text-sm text-zinc-600 dark:text-zinc-400">{shown}</p>}
          {concept.aliases.length > 0 && (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Also called: {concept.aliases.join(" · ")}
            </p>
          )}
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

      {panel === "edit" && (
        <ConceptEditForm
          key={`${concept.id}-${concept.revision}`}
          concept={concept}
          languages={languages}
          busy={busy}
          locked={locked}
          onSave={onSave}
          onCancel={() => onOpenPanel(null)}
        />
      )}
      {panel === "retire" && (
        <ConfirmPanel
          question={`Retire ${concept.name}?`}
          detail="It can no longer be chosen for new questions, and nothing is deleted: questions that already use this concept keep it, and you can restore it any time."
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

function ConceptEditForm({
  concept,
  languages,
  busy,
  locked,
  onSave,
  onCancel,
}: {
  concept: Concept;
  languages: Language[];
  busy: boolean;
  locked: boolean;
  onSave: (body: components["schemas"]["UpdateConcept"]) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(concept.name);
  const [aliases, setAliases] = useState(concept.aliases.join("\n"));
  const [labels, setLabels] = useState<Record<string, string>>({ ...concept.labels });
  const others = languages.filter((language) => language.tag !== "en");

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const filled = Object.fromEntries(
      Object.entries(labels)
        .map(([tag, label]) => [tag, label.trim()] as const)
        .filter(([, label]) => label !== ""),
    );
    onSave({ name: name.trim(), labels: filled, aliases: parseAliases(aliases) });
  }

  return (
    <form onSubmit={submit} aria-label={`Edit ${concept.name}`} className="mt-3 space-y-3">
      <label className="block text-sm font-medium">
        Name (English)
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
        Aliases (one per line)
        <textarea
          name="aliases"
          value={aliases}
          onChange={(e) => setAliases(e.target.value)}
          rows={3}
          className={`${FIELD} mt-1`}
        />
      </label>
      <fieldset className="grid gap-3 sm:grid-cols-2">
        <legend className="text-sm font-medium">Names in other languages</legend>
        {others.map((language) => (
          <label key={language.tag} className="block text-sm">
            {language.english_name} ({language.native_name})
            <input
              name={`label_${language.tag}`}
              value={labels[language.tag] ?? ""}
              onChange={(e) => setLabels({ ...labels, [language.tag]: e.target.value })}
              maxLength={200}
              className={`${FIELD} mt-1`}
            />
          </label>
        ))}
      </fieldset>
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
