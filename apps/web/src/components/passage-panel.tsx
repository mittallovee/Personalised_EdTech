"use client";

import { Blocks } from "@qbank/content-renderer";
import Link from "next/link";

import type { PinnedPassage } from "@/lib/use-pinned-passage";

const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";

/**
 * The passage a question sits under, shown read-only above its editor (D-14): its title and text
 * as written at the checkpoint the question was written with. If the passage has a newer
 * checkpoint, the author can move the question to it; nothing moves by itself.
 */
export function PassagePanel({
  passage,
  disabled,
  onMove,
}: {
  passage: PinnedPassage;
  disabled: boolean;
  onMove: (checkpointId: string) => void;
}) {
  if (passage.state === "none") return null;
  if (passage.state === "loading") {
    return <p className="text-sm text-zinc-600 dark:text-zinc-400">Loading the passage…</p>;
  }
  if (passage.state === "failed") {
    return (
      <p
        role="alert"
        className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
      >
        The passage could not be loaded. A question is written under a saved checkpoint of a passage
        in your coaching.
      </p>
    );
  }
  const { revision } = passage;
  const title = typeof revision.content.title === "string" ? revision.content.title : "";
  const newer = revision.newest_number > revision.number;
  return (
    <section
      aria-label="Passage"
      className="grid gap-2 rounded-md border border-zinc-200 p-3 dark:border-zinc-800"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-medium">{title ? `Passage: ${title}` : "Passage"}</h2>
        <span className="text-sm text-zinc-600 dark:text-zinc-400">
          Written with checkpoint {revision.number} ·{" "}
          <Link href={`/passages/${revision.passage_id}`} className="underline">
            Open the passage
          </Link>
        </span>
      </div>
      {newer && (
        <p
          role="status"
          className="flex flex-wrap items-center gap-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-200"
        >
          The passage has a newer checkpoint ({revision.newest_number}).
          <button
            type="button"
            className={BUTTON}
            disabled={disabled}
            onClick={() => onMove(revision.newest_id)}
          >
            Move to checkpoint {revision.newest_number}
          </button>
        </p>
      )}
      <div className="qb-question">
        <Blocks blocks={revision.content.body} />
      </div>
    </section>
  );
}
