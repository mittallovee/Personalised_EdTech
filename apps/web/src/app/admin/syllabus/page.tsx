"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { StatusNotice } from "@/components/status-notice";
import { SyllabusItem, type Panel } from "@/components/syllabus-item";
import { api, errorMessage, ifMatch } from "@/lib/api";
import {
  canManageCatalogues,
  childKind,
  KIND_NAME,
  KIND_PLURAL,
  type Language,
  type Node,
} from "@/lib/syllabus";
import { useMe } from "@/lib/use-me";

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const NETWORK = "Cannot reach the server. Check your connection and try again.";
const STALE = "Someone else changed this. The list was reloaded; please try again.";

/**
 * The syllabus (C-01, C-04): classes, then the subjects of a class, its chapters, topics and
 * subtopics, one level at a time. Owner and admins add, rename, order, translate, retire and
 * restore items. The API decides who may do what; this page only shows the controls.
 */
export default function SyllabusPage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  // Where you are: the items you opened to get here, outermost first. Empty: the classes.
  const [path, setPath] = useState<Node[]>([]);
  const [items, setItems] = useState<Node[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "denied" | "failed">("loading");
  const [listError, setListError] = useState<string | null>(null);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [open, setOpen] = useState<{ id: string; panel: Panel } | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [itemError, setItemError] = useState<{ id: string; message: string } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [newOrder, setNewOrder] = useState("0");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  // A retry of the same addition reuses its Idempotency-Key, so a lost response never means two.
  const addKey = useRef<{ key: string; fingerprint: string } | null>(null);
  const generation = useRef(0);
  // Which level is on screen, counted up each time the person moves. Every request remembers the
  // level it was sent from; an answer for a level that is no longer on screen changes nothing.
  const level = useRef(0);
  // The level that has a "Show more" request on its way, if any.
  const moreInFlight = useRef<number | null>(null);

  const here = path.at(-1) ?? null;
  const addingKind = childKind(here?.kind ?? null);
  const canManage = me ? canManageCatalogues(me) : false;

  const load = useCallback(async (parent: Node | null, cursor: string | null) => {
    const mine = cursor ? generation.current : ++generation.current;
    let result;
    try {
      result = await api().GET("/api/v1/taxonomy/nodes", {
        params: {
          query: {
            limit: 100,
            ...(parent ? { parent_id: parent.id } : { kind: "CLASS" as const }),
            ...(cursor ? { cursor } : {}),
          },
        },
      });
    } catch {
      if (mine === generation.current) {
        setState("failed");
        setListError(NETWORK);
      }
      return;
    }
    if (mine !== generation.current) return;
    if (result.response.status === 403) {
      setState("denied");
      return;
    }
    if (!result.data) {
      setState("failed");
      setListError(errorMessage(result.error, result.response.status));
      return;
    }
    const page = result.data.data;
    // An item already shown is not added twice.
    setItems((current) =>
      cursor ? [...current, ...page.filter((n) => !current.some((c) => c.id === n.id))] : page,
    );
    setNextCursor(result.data.page.next_cursor ?? null);
    setState("ready");
    setListError(null);
  }, []);

  useEffect(() => {
    // `load` sets state only after the network call returns, never during this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(here, null);
  }, [load, here]);

  useEffect(() => {
    void (async () => {
      try {
        const { data } = await api().GET("/api/v1/languages");
        if (data) setLanguages(data);
      } catch {
        // The names in other languages are optional; the rest of the page works without them.
      }
    })();
  }, []);

  /** "Show more": one request at a time per level, so pressing it twice loads the page once. */
  async function showMore() {
    const mine = level.current;
    if (moreInFlight.current === mine || !nextCursor) return;
    moreInFlight.current = mine;
    try {
      await load(here, nextCursor);
    } finally {
      if (moreInFlight.current === mine) moreInFlight.current = null;
    }
  }

  /** Move to another level: everything belonging to the one you leave is dropped. */
  function moveTo(next: (current: Node[]) => Node[]) {
    level.current += 1;
    setPath(next);
    setNextCursor(null);
    setOpen(null);
    setNotice(null);
    setNewName("");
    setNewOrder("0");
    setAddError(null);
    setAdding(false);
    setState("loading");
  }

  function goTo(depth: number) {
    if (depth === path.length) return; // already here
    moveTo((current) => current.slice(0, depth));
  }

  function enter(node: Node) {
    moveTo((current) => [...current, node]);
  }

  const replace = (updated: Node) =>
    setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));

  /** Run one change to an item; a stale revision reloads the list instead of overwriting. */
  async function change(
    node: Node,
    run: () => Promise<{ data?: Node; error?: unknown; response: Response }>,
    done: (updated: Node) => void,
  ) {
    const mine = level.current;
    const parent = here;
    setBusyId(node.id);
    setItemError(null);
    try {
      const result = await run();
      if (level.current !== mine) return; // the person has moved on: the answer is not for this screen
      if (result.data) {
        replace(result.data);
        done(result.data);
      } else if (result.response.status === 412) {
        setItemError({ id: node.id, message: STALE });
        setOpen(null);
        void load(parent, null);
      } else {
        setItemError({
          id: node.id,
          message: errorMessage(result.error as never, result.response.status),
        });
      }
    } catch {
      if (level.current === mine) setItemError({ id: node.id, message: NETWORK });
    } finally {
      setBusyId((current) => (current === node.id ? null : current));
    }
  }

  const save = (
    node: Node,
    changes: { name: string; sort_order: number; labels: Record<string, string> },
  ) =>
    change(
      node,
      () =>
        api().PATCH("/api/v1/taxonomy/nodes/{node_id}", {
          params: { path: { node_id: node.id }, header: { "If-Match": ifMatch(node.revision) } },
          body: changes,
        }),
      (updated) => {
        setOpen(null);
        setNotice(`${updated.name} was saved.`);
        void load(here, null); // a new order or name can move it: the server's order decides
      },
    );

  const setRetired = (node: Node, retire: boolean) =>
    change(
      node,
      () =>
        api().POST(
          retire
            ? "/api/v1/taxonomy/nodes/{node_id}/deprecate"
            : "/api/v1/taxonomy/nodes/{node_id}/restore",
          {
            params: { path: { node_id: node.id }, header: { "If-Match": ifMatch(node.revision) } },
          },
        ),
      (updated) => {
        setOpen(null);
        setNotice(`${updated.name} was ${retire ? "retired" : "restored"}.`);
      },
    );

  async function add(event: React.FormEvent) {
    event.preventDefault();
    if (!addingKind || adding) return;
    const body = {
      kind: addingKind,
      parent_id: here?.id ?? null,
      name: newName.trim(),
      sort_order: Number(newOrder),
    };
    const mine = level.current;
    const parent = here;
    const fingerprint = JSON.stringify(body);
    if (addKey.current?.fingerprint !== fingerprint) {
      addKey.current = { key: crypto.randomUUID(), fingerprint };
    }
    const key = addKey.current.key;
    setAdding(true);
    setAddError(null);
    try {
      const { data, error, response } = await api().POST("/api/v1/taxonomy/nodes", {
        body,
        params: { header: { "Idempotency-Key": key } },
      });
      if (data && addKey.current?.key === key) addKey.current = null;
      if (level.current !== mine) return; // moved on: the answer is not for this screen
      if (data) {
        setNotice(`${data.name} was added.`);
        void load(parent, null); // the server's order decides where the new item shows
        setNewName("");
        setNewOrder(String(data.sort_order + 1));
      } else {
        setAddError(errorMessage(error, response.status));
      }
    } catch {
      if (level.current === mine) setAddError(NETWORK);
    } finally {
      if (level.current === mine) setAdding(false);
    }
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

  const title = here ? here.name : "All classes";
  return (
    <AppShell me={me} current="syllabus" onSignOut={signOut} onStopActing={stopActing}>
      <h1 className="text-2xl font-semibold">Syllabus</h1>
      <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        Classes, subjects, chapters, topics and subtopics. Questions are filed under them. Nothing
        is ever deleted: a retired item stays on old questions but cannot be chosen for new ones.
      </p>
      {shellError && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}

      <nav aria-label="Where you are" className="mt-6 flex flex-wrap items-center gap-1 text-sm">
        {path.length === 0 ? (
          <span aria-current="page" className="font-medium">
            All classes
          </span>
        ) : (
          <button type="button" onClick={() => goTo(0)} className="underline">
            All classes
          </button>
        )}
        {path.map((node, index) => (
          <span key={node.id} className="flex items-center gap-1">
            <span aria-hidden>›</span>
            {index === path.length - 1 ? (
              <span aria-current="page" className="font-medium">
                {node.name}
              </span>
            ) : (
              <button type="button" onClick={() => goTo(index + 1)} className="underline">
                {node.name}
              </button>
            )}
          </span>
        ))}
      </nav>

      <h2 className="mt-4 text-lg font-medium">{title}</h2>
      <div className="mt-4 max-w-2xl space-y-4">
        {notice && <StatusNotice>{notice}</StatusNotice>}
        {state === "denied" && (
          <p role="alert" className={ALERT}>
            You don&apos;t have access to the syllabus.
          </p>
        )}
        {state === "failed" && (
          <>
            <p role="alert" className={ALERT}>
              {listError}
            </p>
            <button
              type="button"
              onClick={() => {
                setState("loading");
                void load(here, null);
              }}
              className="underline"
            >
              Try again
            </button>
          </>
        )}
        {state === "loading" && <p>Loading…</p>}
        {state === "ready" && items.length === 0 && (
          <p className="text-zinc-600 dark:text-zinc-400">
            {addingKind ? `No ${KIND_PLURAL[addingKind]} yet.` : "Nothing here."}
          </p>
        )}
        {state === "ready" && items.length > 0 && (
          <ul aria-label="Syllabus items" className="space-y-3">
            {items.map((node) => (
              <SyllabusItem
                key={node.id}
                node={node}
                languages={languages}
                canManage={canManage}
                panel={open?.id === node.id ? open.panel : null}
                busy={busyId === node.id}
                error={itemError?.id === node.id ? itemError.message : null}
                onOpenPanel={(panel) => {
                  setItemError(null);
                  setOpen(panel ? { id: node.id, panel } : null);
                }}
                onSave={(changes) => void save(node, changes)}
                onRetire={() => void setRetired(node, true)}
                onRestore={() => void setRetired(node, false)}
                onOpen={childKind(node.kind) ? () => enter(node) : null}
              />
            ))}
          </ul>
        )}
        {nextCursor && state === "ready" && (
          <button
            type="button"
            onClick={() => void showMore()}
            className="rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700"
          >
            Show more
          </button>
        )}

        {canManage && addingKind && state === "ready" && here?.state === "DEPRECATED" && (
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            {here.name} is retired. Restore it to add {KIND_PLURAL[addingKind]} under it.
          </p>
        )}
        {canManage && addingKind && state === "ready" && here?.state !== "DEPRECATED" && (
          <form
            onSubmit={add}
            aria-label={`Add a ${KIND_NAME[addingKind]}`}
            className="space-y-3 rounded-lg border border-dashed border-zinc-300 p-4 dark:border-zinc-700"
          >
            <h3 className="font-medium">Add a {KIND_NAME[addingKind]}</h3>
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
              Order (smaller comes first)
              <input
                name="sort_order"
                type="number"
                min={0}
                max={100000}
                value={newOrder}
                onChange={(e) => setNewOrder(e.target.value)}
                required
                className={`${FIELD} mt-1`}
              />
            </label>
            {addError && (
              <p role="alert" className={ALERT}>
                {addError}
              </p>
            )}
            <button
              type="submit"
              disabled={adding}
              className="rounded-md bg-zinc-900 px-3 py-1 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {adding ? "Adding…" : `Add ${KIND_NAME[addingKind]}`}
            </button>
          </form>
        )}
      </div>
    </AppShell>
  );
}
