"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { api, errorMessage } from "@/lib/api";
import {
  ACCEPT,
  canCancel,
  canRetry,
  errorText,
  isActive,
  sizeProblem,
  stateText,
  type IngestFile,
} from "@/lib/ingest";
import { NETWORK } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const POLL_MS = 4000;

type Sending = { key: number; name: string; status: "sending" | "done" | "failed"; note?: string };

/**
 * Uploads (M6, G-01, G-03): send papers (PDF, Word, pictures), watch them being read, stop or retry
 * them, open one to review the questions found. Sending several files at once is fine: they are sent
 * one after another and you can keep working. The kind of each file is decided by the server from its
 * contents, never from its name.
 */
export default function UploadsPage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const [files, setFiles] = useState<IngestFile[] | null>(null);
  const [more, setMore] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [sending, setSending] = useState<Sending[]>([]);
  const [over, setOver] = useState(false);
  const counter = useRef(0);
  const signedIn = me !== null;

  const load = useCallback(async () => {
    try {
      const { data, error, response } = await api().GET("/api/v1/ingest/files", {
        params: { query: { limit: 50 } },
      });
      if (data) {
        setFiles(data.data);
        setMore(data.page.next_cursor ?? null);
        setProblem(null);
      } else {
        setProblem(errorMessage(error, response.status));
      }
    } catch {
      setProblem(NETWORK);
    }
  }, []);

  useEffect(() => {
    if (!signedIn) return;
    const first = setTimeout(() => void load(), 0); // not inside the effect itself
    return () => clearTimeout(first);
  }, [signedIn, load]);

  const going = files?.some((file) => isActive(file.state)) ?? false;
  useEffect(() => {
    if (!going) return;
    const timer = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(timer);
  }, [going, load]);

  async function showMore() {
    if (!more) return;
    try {
      const { data } = await api().GET("/api/v1/ingest/files", {
        params: { query: { limit: 50, cursor: more } },
      });
      if (data) {
        setFiles((now) => [...(now ?? []), ...data.data]);
        setMore(data.page.next_cursor ?? null);
      }
    } catch {
      setProblem(NETWORK);
    }
  }

  async function sendAll(picked: File[]) {
    for (const file of picked) {
      const key = (counter.current += 1);
      const tooBig = sizeProblem(file);
      if (tooBig) {
        setSending((now) => [...now, { key, name: file.name, status: "failed", note: tooBig }]);
        continue;
      }
      setSending((now) => [...now, { key, name: file.name, status: "sending" }]);
      let status: Sending["status"] = "done";
      let note: string | undefined;
      try {
        const { error, response } = await api().POST("/api/v1/ingest/files", {
          params: { query: { file_name: file.name } },
          // The file itself is the request body, not JSON or a form.
          body: file as unknown as string,
          bodySerializer: (body: unknown) => body as BodyInit,
          headers: { "Content-Type": "application/octet-stream" },
        });
        if (!response.ok) {
          status = "failed";
          note = errorMessage(error, response.status);
        }
      } catch {
        status = "failed";
        note = NETWORK;
      }
      setSending((now) => now.map((item) => (item.key === key ? { ...item, status, note } : item)));
      void load();
    }
  }

  async function act(file: IngestFile, what: "cancel" | "retry") {
    setProblem(null);
    try {
      const { error, response } = await api().POST(
        what === "cancel"
          ? "/api/v1/ingest/files/{file_id}/cancel"
          : "/api/v1/ingest/files/{file_id}/retry",
        { params: { path: { file_id: file.id } } },
      );
      if (!response.ok) setProblem(errorMessage(error, response.status));
    } catch {
      setProblem(NETWORK);
    }
    void load();
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

  return (
    <AppShell me={me} current="uploads" onSignOut={signOut} onStopActing={stopActing}>
      {shellError && (
        <p role="alert" className={`mb-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <div className="grid max-w-4xl gap-6">
        <h1 className="text-2xl font-semibold">Uploads</h1>
        <p className="max-w-2xl text-sm text-zinc-700 dark:text-zinc-300">
          Send question papers (PDF, Word, or photographs) and turn them into questions. Nothing
          becomes a question until you accept it. You can keep working while files are read.
        </p>

        <label
          onDragOver={(event) => {
            event.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={(event) => {
            event.preventDefault();
            setOver(false);
            void sendAll(Array.from(event.dataTransfer.files));
          }}
          className={`grid cursor-pointer gap-1 rounded-md border-2 border-dashed p-8 text-center text-sm ${
            over
              ? "border-sky-500 bg-sky-50 dark:bg-sky-950"
              : "border-zinc-300 dark:border-zinc-700"
          }`}
        >
          <span className="font-medium">Drop files here, or choose them</span>
          <span className="text-zinc-600 dark:text-zinc-400">
            PDF and Word up to 50 MB, pictures up to 10 MB, many at once
          </span>
          <input
            type="file"
            multiple
            accept={ACCEPT}
            className="sr-only"
            aria-label="Choose files to upload"
            onChange={(event) => {
              void sendAll(Array.from(event.target.files ?? []));
              event.target.value = "";
            }}
          />
        </label>

        {sending.length > 0 && (
          <ul aria-label="Files being sent" className="grid gap-1 text-sm">
            {sending.map((item) => (
              <li
                key={item.key}
                className={item.status === "failed" ? "text-red-700 dark:text-red-300" : ""}
              >
                {item.name}:{" "}
                {item.status === "sending"
                  ? "sending…"
                  : item.status === "done"
                    ? "sent"
                    : `not sent. ${item.note ?? ""}`}
              </li>
            ))}
          </ul>
        )}

        {problem && (
          <p role="alert" className={ALERT}>
            {problem}
          </p>
        )}

        <section aria-label="Your documents" className="grid gap-2">
          <h2 className="text-lg font-semibold">Documents</h2>
          {files === null ? (
            <p>Loading…</p>
          ) : files.length === 0 ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Nothing has been uploaded yet.
            </p>
          ) : (
            <ul className="grid gap-2">
              {files.map((file) => (
                <li
                  key={file.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-zinc-200 p-3 text-sm dark:border-zinc-800"
                >
                  <div className="min-w-0">
                    <Link href={`/uploads/${file.id}`} className="font-medium underline">
                      {file.file_name}
                    </Link>
                    <p className="text-zinc-600 dark:text-zinc-400">
                      {file.kind} · {(file.byte_size / 1024 / 1024).toFixed(1)} MB ·{" "}
                      {stateText(file.state)}
                      {file.page_count !== null && ` · ${file.page_count} pages`}
                    </p>
                    {errorText(file.error_code) && (
                      <p className="text-amber-800 dark:text-amber-300">
                        {errorText(file.error_code)}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {canCancel(file.state) && (
                      <button
                        type="button"
                        className={BUTTON}
                        onClick={() => void act(file, "cancel")}
                      >
                        Cancel
                      </button>
                    )}
                    {canRetry(file.state) && (
                      <button
                        type="button"
                        className={BUTTON}
                        onClick={() => void act(file, "retry")}
                      >
                        Try again
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
          {more && (
            <button
              type="button"
              className={`${BUTTON} justify-self-start`}
              onClick={() => void showMore()}
            >
              Show more
            </button>
          )}
        </section>
      </div>
    </AppShell>
  );
}
