"use client";

import type { components } from "@qbank/api-client";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

type Revision = components["schemas"]["PassageRevisionOut"];

export type PinnedPassage =
  | { state: "none" }
  | { state: "loading" }
  | { state: "failed" }
  | { state: "ready"; revision: Revision };

/**
 * The passage checkpoint a question is written under (D-14), read from the server: its text, and
 * which checkpoint of that passage is the newest. Follows the question when it is moved to another
 * checkpoint. Any member of the coaching may read a checkpoint, so this works for a question whose
 * passage draft the author cannot open.
 */
export function usePinnedPassage(pin: string | null): PinnedPassage {
  // The answer for one checkpoint; `revision` is null when it could not be read.
  const [loaded, setLoaded] = useState<{ pin: string; revision: Revision | null } | null>(null);

  useEffect(() => {
    if (!pin) return;
    let cancelled = false;
    async function load(revisionId: string) {
      let revision: Revision | null = null;
      try {
        const { data } = await api().GET("/api/v1/passage-revisions/{revision_id}", {
          params: { path: { revision_id: revisionId } },
        });
        revision = data ?? null;
      } catch {
        revision = null;
      }
      if (!cancelled) setLoaded({ pin: revisionId, revision });
    }
    void load(pin);
    return () => {
      cancelled = true;
    };
  }, [pin]);

  if (!pin) return { state: "none" };
  if (loaded?.pin !== pin) return { state: "loading" };
  return loaded.revision ? { state: "ready", revision: loaded.revision } : { state: "failed" };
}
