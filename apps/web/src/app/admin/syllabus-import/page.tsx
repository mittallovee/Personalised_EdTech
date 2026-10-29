"use client";

import type { components } from "@qbank/api-client";
import { useCallback, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { ConfirmPanel } from "@/components/confirm-panel";
import { StatusNotice } from "@/components/status-notice";
import { api, errorMessage } from "@/lib/api";
import { canManageCatalogues } from "@/lib/syllabus";
import { NETWORK, useCatalogueList } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Import = components["schemas"]["ImportOut"];
type ImportRow = components["schemas"]["ImportRowOut"];
type RowStatus = ImportRow["status"];
type Row = ImportRow & { id: string };

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/** The API refuses bigger files; checking here saves sending 5 MB just to be told so. */
const MAX_BYTES = 5 * 1024 * 1024;

const STATUS_LABEL: Record<RowStatus, string> = {
  NEW: "New",
  CHANGED: "Changed",
  UNCHANGED: "Unchanged",
  ERROR: "Error",
};

/**
 * Import a syllabus from Excel or CSV (C-03): download the template, upload a filled-in file, read
 * the preview (every row new, changed, unchanged or an error), then apply it. Nothing in the
 * syllabus changes until "Apply". Owner and admins only; the API decides, this page only hides the
 * controls.
 */
export default function SyllabusImportPage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [preview, setPreview] = useState<Import | null>(null);
  const [inputKey, setInputKey] = useState(0);
  // A retry of the same upload reuses its Idempotency-Key, so a lost answer never means two previews.
  const uploadKey = useRef<{ key: string; fingerprint: string } | null>(null);

  async function upload(event: React.FormEvent) {
    event.preventDefault();
    if (!file || uploading) return;
    const fingerprint = `${file.name}|${file.size}|${file.lastModified}`;
    if (uploadKey.current?.fingerprint !== fingerprint) {
      uploadKey.current = { key: crypto.randomUUID(), fingerprint };
    }
    const key = uploadKey.current.key;
    setUploading(true);
    setUploadError(null);
    try {
      const { data, error, response } = await api().POST("/api/v1/taxonomy/imports", {
        params: { query: { file_name: file.name }, header: { "Idempotency-Key": key } },
        // The file itself is the request body, not JSON.
        body: file as unknown as string,
        bodySerializer: (body: unknown) => body as BodyInit,
        headers: { "Content-Type": "application/octet-stream" },
      });
      if (data) {
        uploadKey.current = null;
        setPreview(data);
      } else {
        setUploadError(errorMessage(error, response.status));
      }
    } catch {
      setUploadError(NETWORK);
    } finally {
      setUploading(false);
    }
  }

  function chooseFile(chosen: File | null) {
    setUploadError(null);
    if (chosen && chosen.size > MAX_BYTES) {
      setFile(null);
      setFileError("That file is bigger than 5 MB. Split it into smaller files.");
      return;
    }
    setFileError(null);
    setFile(chosen);
  }

  function startOver() {
    setPreview(null);
    setFile(null);
    setFileError(null);
    setUploadError(null);
    setInputKey((n) => n + 1); // a fresh file box: the old file is forgotten
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

  const canManage = canManageCatalogues(me);
  return (
    <AppShell me={me} current="import" onSignOut={signOut} onStopActing={stopActing}>
      <h1 className="text-2xl font-semibold">Import syllabus</h1>
      <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        Add many syllabus items and concepts at once from an Excel (.xlsx) or CSV file. You see what
        the file would do first, and nothing changes until you apply it. An import only adds items
        and fills in names; it never deletes, renames or retires anything.
      </p>
      {shellError && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}

      {!canManage && (
        <p role="alert" className={`mt-6 max-w-2xl ${ALERT}`}>
          Only the Owner and admins can import a syllabus.
        </p>
      )}

      {canManage && !preview && (
        <div className="mt-6 max-w-2xl space-y-6">
          <section aria-labelledby="template-heading" className="space-y-2">
            <h2 id="template-heading" className="text-lg font-medium">
              1. Get the template
            </h2>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              One row per item: its kind (class, subject, chapter, topic, subtopic or concept), its
              path such as <code>Class 11 &gt; Physics &gt; Kinematics</code>, and optionally its
              order, aliases and names in other languages. Open it in Excel, fill it in, and upload
              it as CSV or saved as .xlsx. Formulas are not accepted: paste cells as values.
            </p>
            <a
              href="/api/v1/taxonomy/import-template"
              download="syllabus-template.csv"
              className={`${BUTTON} inline-block`}
            >
              Download the template
            </a>
          </section>

          <form onSubmit={upload} aria-label="Upload a file" className="space-y-3">
            <h2 className="text-lg font-medium">2. Upload your file</h2>
            <label className="block text-sm font-medium">
              File (.xlsx or .csv, up to 5 MB)
              <input
                key={inputKey}
                name="file"
                type="file"
                accept=".xlsx,.csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                onChange={(e) => chooseFile(e.target.files?.[0] ?? null)}
                className={`${FIELD} mt-1`}
              />
            </label>
            {fileError && (
              <p role="alert" className={ALERT}>
                {fileError}
              </p>
            )}
            {uploadError && (
              <p role="alert" className={ALERT}>
                {uploadError}
              </p>
            )}
            <button type="submit" disabled={!file || uploading} className={PRIMARY}>
              {uploading ? "Checking the file…" : "Check the file"}
            </button>
            {uploading && (
              <p role="status" className="text-sm text-zinc-600 dark:text-zinc-400">
                Reading {file?.name}. This can take a little while for a big file.
              </p>
            )}
          </form>
        </div>
      )}

      {canManage && preview && (
        <PreviewPanel
          key={preview.id}
          preview={preview}
          onApplied={setPreview}
          onStartOver={startOver}
        />
      )}
    </AppShell>
  );
}

function PreviewPanel({
  preview,
  onApplied,
  onStartOver,
}: {
  preview: Import;
  onApplied: (applied: Import) => void;
  onStartOver: () => void;
}) {
  const [filter, setFilter] = useState<RowStatus | "">("");
  const [confirming, setConfirming] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [expired, setExpired] = useState(false);
  const applied = preview.state === "APPLIED";

  const fetchPage = useCallback(
    async (cursor: string | null) => {
      const result = await api().GET("/api/v1/taxonomy/imports/{import_id}/rows", {
        params: {
          path: { import_id: preview.id },
          query: {
            limit: 100,
            ...(filter ? { status: filter } : {}),
            ...(cursor ? { cursor } : {}),
          },
        },
      });
      if (result.response.status === 410) setExpired(true);
      return {
        data: result.data && {
          data: result.data.data.map((r): Row => ({ ...r, id: String(r.number) })),
          page: result.data.page,
        },
        error: result.error,
        response: result.response,
      };
    },
    [preview.id, filter],
  );
  const list = useCatalogueList<Row>(fetchPage);

  async function apply() {
    if (applying) return;
    setApplying(true);
    setApplyError(null);
    try {
      const { data, error, response } = await api().POST(
        "/api/v1/taxonomy/imports/{import_id}/apply",
        { params: { path: { import_id: preview.id } } },
      );
      if (data) {
        setConfirming(false);
        onApplied(data);
      } else if (response.status === 409) {
        setConfirming(false);
        setApplyError(
          "The syllabus changed after this preview was made, so it is out of date. Nothing was imported. Upload the file again.",
        );
      } else if (response.status === 410) {
        setConfirming(false);
        setExpired(true);
      } else {
        setConfirming(false);
        setApplyError(errorMessage(error, response.status));
      }
    } catch {
      setApplyError(NETWORK);
    } finally {
      setApplying(false);
    }
  }

  const { counts } = preview;
  const changes = counts.new + counts.changed;
  return (
    <div className="mt-6 space-y-4">
      <h2 className="text-lg font-medium">
        {applied ? "Imported" : "3. Check the preview"}: {preview.file_name}
      </h2>
      {applied && (
        <StatusNotice>{`The import was applied: ${counts.new} added, ${counts.changed} filled in.`}</StatusNotice>
      )}
      <dl aria-label="Totals" className="grid max-w-2xl grid-cols-2 gap-3 sm:grid-cols-4">
        {(
          [
            ["New", counts.new],
            ["Changed", counts.changed],
            ["Unchanged", counts.unchanged],
            ["Errors", counts.error],
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
            <dt className="text-sm text-zinc-600 dark:text-zinc-400">{label}</dt>
            <dd className="text-2xl font-semibold">{value}</dd>
          </div>
        ))}
      </dl>

      {!applied && counts.error > 0 && (
        <p role="alert" className={`max-w-2xl ${ALERT}`}>
          {counts.error === 1 ? "1 row has an error" : `${counts.error} rows have errors`}, so this
          file cannot be applied. Fix them in your file and upload it again.
        </p>
      )}
      {!applied && counts.error === 0 && changes === 0 && (
        <p className="max-w-2xl text-zinc-600 dark:text-zinc-400">
          Everything in this file is already in the syllabus. There is nothing to apply.
        </p>
      )}
      {expired && (
        <p role="alert" className={`max-w-2xl ${ALERT}`}>
          This preview was kept too long and is gone. Upload the file again.
        </p>
      )}
      {applyError && (
        <p role="alert" className={`max-w-2xl ${ALERT}`}>
          {applyError}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-3">
        {!applied && preview.can_apply && !confirming && !expired && (
          <button type="button" onClick={() => setConfirming(true)} className={PRIMARY}>
            Apply the import
          </button>
        )}
        <button type="button" onClick={onStartOver} className={BUTTON}>
          {applied ? "Import another file" : "Upload a different file"}
        </button>
      </div>
      {confirming && (
        <div className="max-w-2xl">
          <ConfirmPanel
            question="Apply this import?"
            detail={`${counts.new} item${counts.new === 1 ? "" : "s"} will be added and ${counts.changed} filled in, all at once or not at all. Nothing is removed, renamed or retired.`}
            confirmLabel="Apply"
            busy={applying}
            onConfirm={() => void apply()}
            onCancel={() => setConfirming(false)}
          />
        </div>
      )}

      {!expired && (
        <section aria-labelledby="rows-heading" className="space-y-3">
          <h3 id="rows-heading" className="font-medium">
            Rows
          </h3>
          <label className="block max-w-xs text-sm font-medium">
            Show
            <select
              name="status_filter"
              value={filter}
              onChange={(e) => setFilter(e.target.value as RowStatus | "")}
              className={`${FIELD} mt-1`}
            >
              <option value="">All rows</option>
              {(Object.keys(STATUS_LABEL) as RowStatus[]).map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]} only
                </option>
              ))}
            </select>
          </label>
          {list.state === "loading" && <p>Loading…</p>}
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
          {list.state === "denied" && (
            <p role="alert" className={ALERT}>
              You don&apos;t have access to this import.
            </p>
          )}
          {list.state === "ready" && list.items.length === 0 && (
            <p className="text-zinc-600 dark:text-zinc-400">No rows to show.</p>
          )}
          {list.state === "ready" && list.items.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full max-w-4xl text-left text-sm">
                <caption className="sr-only">Rows of the file and what each would do</caption>
                <thead>
                  <tr className="border-b border-zinc-300 dark:border-zinc-700">
                    <th scope="col" className="py-2 pr-3">
                      Row
                    </th>
                    <th scope="col" className="py-2 pr-3">
                      Kind
                    </th>
                    <th scope="col" className="py-2 pr-3">
                      Path
                    </th>
                    <th scope="col" className="py-2 pr-3">
                      Result
                    </th>
                    <th scope="col" className="py-2">
                      Details
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {list.items.map((row) => (
                    <tr key={row.id} className="border-b border-zinc-200 dark:border-zinc-800">
                      <td className="py-2 pr-3">{row.number}</td>
                      <td className="py-2 pr-3">{row.kind}</td>
                      <td className="py-2 pr-3">{row.path}</td>
                      <td className="py-2 pr-3 font-medium">{STATUS_LABEL[row.status]}</td>
                      <td className="py-2">{rowDetails(row)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {list.nextCursor && list.state === "ready" && (
            <button type="button" onClick={() => void list.showMore()} className={BUTTON}>
              Show more rows
            </button>
          )}
        </section>
      )}
    </div>
  );
}

/** What a row says besides its result: the reason for an error, else what it sets. */
function rowDetails(row: ImportRow): string {
  if (row.message) return row.message;
  const parts: string[] = [];
  if (row.sort_order !== null) parts.push(`Order ${row.sort_order}`);
  for (const [tag, label] of Object.entries(row.labels)) parts.push(`${tag}: ${label}`);
  if (row.aliases.length > 0) parts.push(`Also called: ${row.aliases.join(" · ")}`);
  return parts.join(" · ");
}
