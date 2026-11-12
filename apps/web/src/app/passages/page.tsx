"use client";

import type { components } from "@qbank/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";
import { useAdd, useCatalogueList } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Summary = components["schemas"]["PassageSummary"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/**
 * Passages (D-14): shared text that several questions sit under. The ones you may open, newest
 * first, and a way to start a new one. A passage has no code of its own: it is only context.
 */
export default function PassagesPage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();

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
      <h1 className="text-2xl font-semibold">Passages</h1>
      <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        A passage is text that several questions share. Write it here, save a checkpoint, then add
        the questions that go under it.
      </p>
      {shellError && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <div className="mt-6 grid max-w-3xl gap-10">
        <NewPassage />
        <PassageList />
      </div>
    </AppShell>
  );
}

function NewPassage() {
  const router = useRouter();
  const adder = useAdd<components["schemas"]["PassageOut"]>(
    (body, key) =>
      api().POST("/api/v1/passages", {
        body: body as components["schemas"]["CreatePassage"],
        params: { header: { "Idempotency-Key": key } },
      }),
    (created) => router.push(`/passages/${created.id}`),
  );
  return (
    <div className="grid gap-3">
      {adder.addError && (
        <p role="alert" className={ALERT}>
          {adder.addError}
        </p>
      )}
      <div>
        <button
          type="button"
          disabled={adder.adding}
          className={PRIMARY}
          onClick={() => void adder.add({})}
        >
          {adder.adding ? "Starting…" : "Start a passage"}
        </button>
      </div>
    </div>
  );
}

function PassageList() {
  const [mine, setMine] = useState(false);
  const fetchPage = useCallback(
    (cursor: string | null) =>
      api().GET("/api/v1/passages", {
        params: { query: { mine, limit: 25, cursor: cursor ?? undefined } },
      }),
    [mine],
  );
  const list = useCatalogueList<Summary>(fetchPage);

  return (
    <section aria-label="Your passages" className="grid gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-medium">Passages</h2>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={mine} onChange={(e) => setMine(e.target.checked)} />
          Only mine
        </label>
      </div>
      {list.state === "loading" && <p className="text-sm">Loading…</p>}
      {list.state === "denied" && (
        <p role="alert" className={ALERT}>
          Your role may not open passages.
        </p>
      )}
      {list.state === "failed" && (
        <p role="alert" className={ALERT}>
          {list.listError}{" "}
          <button type="button" className="underline" onClick={() => void list.reload()}>
            Try again
          </button>
        </p>
      )}
      {list.state === "ready" && list.items.length === 0 && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          No passages yet. Start one above.
        </p>
      )}
      {list.items.length > 0 && (
        <ul className="divide-y divide-zinc-200 rounded-md border border-zinc-200 dark:divide-zinc-800 dark:border-zinc-800">
          {list.items.map((passage) => (
            <li key={passage.id}>
              <Link
                href={`/passages/${passage.id}`}
                className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-900"
              >
                <span className="font-medium">{passage.title || "Untitled passage"}</span>
                <span className="text-xs text-zinc-600 dark:text-zinc-400">
                  {passage.latest_checkpoint_number === null
                    ? "No checkpoint yet"
                    : `Checkpoint ${passage.latest_checkpoint_number}`}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {list.nextCursor && (
        <div>
          <button
            type="button"
            className="rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700"
            onClick={() => void list.showMore()}
          >
            Show more
          </button>
        </div>
      )}
    </section>
  );
}
