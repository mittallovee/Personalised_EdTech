"use client";

import { useEffect, useRef, useState } from "react";

import type { Answer, Page } from "@/lib/use-catalogue";

type Loaded<T> = { key: string; items: T[]; failed: boolean };

/**
 * Read every page of a list. A page that cannot be read, or a cursor that comes back a second
 * time (the server would never finish), makes the whole read a failure: a partly read list is
 * never passed off as complete, because an entry beyond the cut could not then be chosen.
 */
export async function readAllPages<T>(
  fetchPage: (cursor: string | null) => Promise<Answer<Page<T>>>,
): Promise<{ items: T[]; failed: boolean }> {
  const items: T[] = [];
  const seen = new Set<string>();
  let cursor: string | null = null;
  try {
    do {
      const result = await fetchPage(cursor);
      if (!result.data) return { items: [], failed: true };
      items.push(...result.data.data);
      cursor = result.data.page.next_cursor ?? null;
      if (cursor !== null) {
        if (seen.has(cursor)) return { items: [], failed: true };
        seen.add(cursor);
      }
    } while (cursor !== null);
  } catch {
    return { items: [], failed: true };
  }
  return { items, failed: false };
}

/**
 * Every item of a list, read page by page, for a pick-list. The list is read again when `key`
 * changes (it names what is asked for) and is empty while `key` is `null`. An answer that arrives
 * after `key` changed is ignored. A failure is reported, never thrown, so one list that cannot be
 * read leaves the rest of the editor working.
 */
export function useAll<T>(
  key: string | null,
  fetchPage: (cursor: string | null) => Promise<Answer<Page<T>>>,
) {
  const [loaded, setLoaded] = useState<Loaded<T> | null>(null);
  const latest = useRef(fetchPage);
  useEffect(() => {
    latest.current = fetchPage;
  }, [fetchPage]);

  useEffect(() => {
    if (key === null) return;
    let stale = false;
    void readAllPages((cursor) => latest.current(cursor)).then(({ items, failed }) => {
      if (!stale) setLoaded({ key, items, failed });
    });
    return () => {
      stale = true;
    };
  }, [key]);

  const ready = key !== null && loaded?.key === key;
  return {
    items: ready ? loaded.items : [],
    loading: key !== null && !ready,
    failed: ready && loaded.failed,
  };
}
