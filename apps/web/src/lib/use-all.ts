"use client";

import { useEffect, useRef, useState } from "react";

import type { Answer, Page } from "@/lib/use-catalogue";

/** Pages read at most (100 items each): a pick-list longer than this is searched, not scrolled. */
const MAX_PAGES = 10;

type Loaded<T> = { key: string; items: T[]; failed: boolean };

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
    void (async () => {
      const items: T[] = [];
      let failed = false;
      let cursor: string | null = null;
      try {
        for (let page = 0; page < MAX_PAGES; page++) {
          const result = await latest.current(cursor);
          if (!result.data) {
            failed = true;
            break;
          }
          items.push(...result.data.data);
          cursor = result.data.page.next_cursor ?? null;
          if (!cursor) break;
        }
      } catch {
        failed = true;
      }
      if (!stale) setLoaded({ key, items, failed });
    })();
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
