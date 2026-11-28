"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { api, errorMessage } from "@/lib/api";
import {
  canCancel,
  canRead,
  canRetry,
  errorText,
  isActive,
  stateText,
  tally,
  type Candidate,
  type IngestFile,
  type IngestPage,
  type IngestRun,
} from "@/lib/ingest";
import { NETWORK } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";
const POLL_MS = 4000;

export default function UploadDetail() {
  return (
    <Suspense fallback={<main className="p-8">Loading…</main>}>
      <Screen />
    </Suspense>
  );
}

function Screen() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const { id } = useParams<{ id: string }>();
  const [file, setFile] = useState<IngestFile | null>(null);
  const [pages, setPages] = useState<IngestPage[]>([]);
  const [runs, setRuns] = useState<IngestRun[]>([]);
  const [found, setFound] = useState<Candidate[]>([]);
  const [problem, setProblem] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);
  const [busy, setBusy] = useState(false);
  const signedIn = me !== null;

  const load = useCallback(async () => {
    try {
      const [one, pageList, runList, candidates] = await Promise.all([
        api().GET("/api/v1/ingest/files/{file_id}", { params: { path: { file_id: id } } }),
        api().GET("/api/v1/ingest/files/{file_id}/pages", { params: { path: { file_id: id } } }),
        api().GET("/api/v1/ingest/files/{file_id}/runs", { params: { path: { file_id: id } } }),
        api().GET("/api/v1/ingest/files/{file_id}/candidates", {
          params: { path: { file_id: id } },
        }),
      ]);
      if (one.response.status === 404) {
        setMissing(true);
        return;
      }
      if (one.data) setFile(one.data);
      else setProblem(errorMessage(one.error, one.response.status));
      if (pageList.data) setPages(pageList.data.data);
      if (runList.data) setRuns(runList.data.data);
      if (candidates.data) setFound(candidates.data.data);
    } catch {
      setProblem(NETWORK);
    }
  }, [id]);

  useEffect(() => {
    if (!signedIn) return;
    const first = setTimeout(() => void load(), 0);
    return () => clearTimeout(first);
  }, [signedIn, load]);

  const going = file !== null && isActive(file.state);
  useEffect(() => {
    if (!going) return;
    const timer = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(timer);
  }, [going, load]);

  async function post(path: "extract" | "cancel" | "retry") {
    setBusy(true);
    setProblem(null);
    try {
      const url =
        path === "extract"
          ? "/api/v1/ingest/files/{file_id}/extract"
          : path === "cancel"
            ? "/api/v1/ingest/files/{file_id}/cancel"
            : "/api/v1/ingest/files/{file_id}/retry";
      const { error, response } = await api().POST(url, { params: { path: { file_id: id } } });
      if (!response.ok) setProblem(errorMessage(error, response.status));
    } catch {
      setProblem(NETWORK);
    } finally {
      setBusy(false);
      void load();
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
  const counts = tally(found);

  return (
    <AppShell me={me} current="uploads" onSignOut={signOut} onStopActing={stopActing}>
      {shellError && (
        <p role="alert" className={`mb-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <div className="grid max-w-5xl gap-6">
        <Link href="/uploads" className="text-sm underline">
          Back to uploads
        </Link>
        {missing ? (
          <p role="alert" className={ALERT}>
            This document does not exist, or you may not open it.
          </p>
        ) : !file ? (
          <p>Loading…</p>
        ) : (
          <>
            <div>
              <h1 className="text-2xl font-semibold">{file.file_name}</h1>
              <p className="mt-1 text-sm text-zinc-700 dark:text-zinc-300">
                {file.kind} · {(file.byte_size / 1024 / 1024).toFixed(1)} MB ·{" "}
                <span role="status">{stateText(file.state)}</span>
                {file.page_count !== null && ` · ${file.page_count} pages`}
              </p>
              {errorText(file.error_code) && (
                <p className="mt-1 text-sm text-amber-800 dark:text-amber-300">
                  {errorText(file.error_code)}
                </p>
              )}
              {file.duplicate_of && (
                <p className="mt-1 text-sm">
                  The same bytes were uploaded before.{" "}
                  <Link className="underline" href={`/uploads/${file.duplicate_of}`}>
                    Open the earlier one
                  </Link>
                  .
                </p>
              )}
            </div>

            {problem && (
              <p role="alert" className={ALERT}>
                {problem}{" "}
                {problem.includes("chooses one") && me.organization?.role !== "FACULTY" && (
                  <Link href="/admin/ai" className="underline">
                    Open Admin, AI
                  </Link>
                )}
              </p>
            )}

            <div className="flex flex-wrap gap-2">
              {canRead(file.state) && pages.some((p) => p.state === "READY") && (
                <button
                  type="button"
                  className={PRIMARY}
                  disabled={busy}
                  onClick={() => void post("extract")}
                >
                  {found.length > 0 ? "Read the questions again" : "Read the questions"}
                </button>
              )}
              {canCancel(file.state) && (
                <button
                  type="button"
                  className={BUTTON}
                  disabled={busy}
                  onClick={() => void post("cancel")}
                >
                  Cancel
                </button>
              )}
              {canRetry(file.state) && (
                <button
                  type="button"
                  className={BUTTON}
                  disabled={busy}
                  onClick={() => void post("retry")}
                >
                  Try again
                </button>
              )}
              <a className={BUTTON} href={`/api/v1/ingest/files/${file.id}/original`}>
                Download the original
              </a>
            </div>

            <section aria-label="Questions found" className="grid gap-2">
              <h2 className="text-lg font-semibold">Questions found</h2>
              {found.length === 0 ? (
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                  {file.state === "EXTRACTING"
                    ? "Reading the questions… you can keep working."
                    : "None yet. Press “Read the questions” once the pages are ready."}
                </p>
              ) : (
                <>
                  <p className="text-sm">
                    {found.length} found: {counts.NEW} waiting, {counts.ACCEPTED} made into
                    questions, {counts.DUPLICATE} already in the bank, {counts.REJECTED} rejected.
                  </p>
                  <Link
                    href={`/uploads/${file.id}/review`}
                    className={`${PRIMARY} justify-self-start`}
                  >
                    Review the questions
                  </Link>
                </>
              )}
              {runs[0] && (
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                  Last reading: {runs[0].pages_done} of {runs[0].pages_total} pages
                  {runs[0].pages_failed > 0 && `, ${runs[0].pages_failed} not read`}
                  {runs[0].state === "RUNNING" && " (still going)"}
                  {errorText(runs[0].error_code) && `. ${errorText(runs[0].error_code)}`}
                </p>
              )}
            </section>

            <section aria-label="Pages" className="grid gap-2">
              <h2 className="text-lg font-semibold">Pages</h2>
              {pages.length === 0 ? (
                <p className="text-sm text-zinc-600 dark:text-zinc-400">No pages yet.</p>
              ) : (
                <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {pages.map((page) => (
                    <li
                      key={page.page_no}
                      className="rounded-md border border-zinc-200 p-2 text-sm dark:border-zinc-800"
                    >
                      {page.has_picture ? (
                        // eslint-disable-next-line @next/next/no-img-element -- our own re-encoded page picture behind the sign-in
                        <img
                          src={`/api/v1/ingest/files/${file.id}/pages/${page.page_no}/image?size=thumb`}
                          alt={`Page ${page.page_no}`}
                          className="w-full rounded"
                          loading="lazy"
                        />
                      ) : (
                        <p className="line-clamp-6 text-zinc-700 dark:text-zinc-300">
                          {page.text ?? "(no text)"}
                        </p>
                      )}
                      <p className="mt-1">
                        Page {page.page_no}
                        {page.state === "FAILED" && ` · ${errorText(page.error_code)}`}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}
