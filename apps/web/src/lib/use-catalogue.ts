"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { errorMessage } from "@/lib/api";

export const NETWORK = "Cannot reach the server. Check your connection and try again.";
export const STALE = "Someone else changed this. The list was reloaded; please try again.";

/** What an openapi-fetch call returns, as far as these hooks need it. */
type Answer<D> = { data?: D; error?: unknown; response: Response };
type Page<T> = { data: T[]; page: { next_cursor?: string | null } };

/**
 * A list read page by page ("Show more"), for the catalogue screens. `fetchPage` must keep the same
 * identity while the list's filters are the same: a new one starts the list over. An answer that
 * arrives after the list was started again is ignored.
 */
export function useCatalogueList<T extends { id: string }>(
  fetchPage: (cursor: string | null) => Promise<Answer<Page<T>>>,
) {
  const [items, setItems] = useState<T[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "denied" | "failed">("loading");
  const [listError, setListError] = useState<string | null>(null);
  const generation = useRef(0);
  const moreInFlight = useRef<number | null>(null);
  // The newest `fetchPage`. A reload started by a change that finishes late must read the filters
  // on screen now, not the ones the change was sent under.
  const latestFetch = useRef(fetchPage);
  useEffect(() => {
    latestFetch.current = fetchPage;
  }, [fetchPage]);

  const load = useCallback(async (cursor: string | null) => {
    const mine = cursor ? generation.current : ++generation.current;
    if (!cursor) setNextCursor(null);
    let result;
    try {
      result = await latestFetch.current(cursor);
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
      setListError(errorMessage(result.error as never, result.response.status));
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

  // New filters start the list over.
  useEffect(() => {
    // `load` sets state only after the network call returns, never during this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(null);
  }, [load, fetchPage]);

  const reload = useCallback(() => load(null), [load]);

  /** "Show more": one request at a time per list, so pressing it twice loads the page once. */
  async function showMore() {
    const mine = generation.current;
    if (moreInFlight.current === mine || !nextCursor) return;
    moreInFlight.current = mine;
    try {
      await load(nextCursor);
    } finally {
      if (moreInFlight.current === mine) moreInFlight.current = null;
    }
  }

  function retry() {
    setState("loading");
    void load(null);
  }

  const replace = (updated: T) =>
    setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));

  return { items, nextCursor, state, listError, reload, showMore, retry, replace };
}

/**
 * Changes to the items of a list, one at a time: a second change sent before the first answered
 * would carry a stale revision. A 412 (someone else changed it) reloads the list.
 */
export function useChanges<T extends { id: string }>(
  replace: (updated: T) => void,
  reload: () => Promise<void>,
) {
  const [busyId, setBusyId] = useState<string | null>(null);
  const [itemError, setItemError] = useState<{ id: string; message: string } | null>(null);
  const [stale, setStale] = useState(false);
  const changing = useRef(false);

  async function change(
    item: T,
    run: () => Promise<Answer<T>>,
    done: (updated: T) => void,
    onStale: () => void,
  ) {
    if (changing.current) return;
    changing.current = true;
    setBusyId(item.id);
    setItemError(null);
    setStale(false);
    try {
      const result = await run();
      if (result.data) {
        replace(result.data);
        done(result.data);
      } else if (result.response.status === 412) {
        setStale(true);
        onStale();
        void reload();
      } else {
        setItemError({
          id: item.id,
          message: errorMessage(result.error as never, result.response.status),
        });
      }
    } catch {
      setItemError({ id: item.id, message: NETWORK });
    } finally {
      changing.current = false;
      setBusyId(null);
    }
  }

  return { busyId, itemError, setItemError, stale, setStale, change };
}

/**
 * Adding an item. A retry of the same addition reuses its Idempotency-Key, so a lost response
 * never means two items.
 */
export function useAdd<T>(
  send: (body: unknown, key: string) => Promise<Answer<T>>,
  onAdded: (created: T) => void,
) {
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);
  const addKey = useRef<{ key: string; fingerprint: string } | null>(null);

  async function add(body: unknown): Promise<boolean> {
    if (adding) return false;
    const fingerprint = JSON.stringify(body);
    if (addKey.current?.fingerprint !== fingerprint) {
      addKey.current = { key: crypto.randomUUID(), fingerprint };
    }
    const key = addKey.current.key;
    setAdding(true);
    setAddError(null);
    try {
      const { data, error, response } = await send(body, key);
      if (data) {
        if (addKey.current?.key === key) addKey.current = null;
        onAdded(data);
        return true;
      }
      setAddError(errorMessage(error as never, response.status));
      return false;
    } catch {
      setAddError(NETWORK);
      return false;
    } finally {
      setAdding(false);
    }
  }

  return { adding, addError, setAddError, add };
}
