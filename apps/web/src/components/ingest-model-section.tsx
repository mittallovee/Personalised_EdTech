"use client";

import { useEffect, useState } from "react";

import { api, errorMessage, ifMatch } from "@/lib/api";
import { NETWORK } from "@/lib/use-catalogue";

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const OK =
  "rounded-md bg-green-50 px-3 py-2 text-sm text-green-800 dark:bg-green-950 dark:text-green-200";
const FIELD =
  "rounded-md border border-zinc-300 bg-transparent px-2 py-1 text-sm dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

type Choice = { id: string; label: string };

/**
 * The model uploaded documents are read with (M6): one of the models turned on above that can read
 * pictures. A model the provider does not say reads pictures can be marked as doing so under
 * "Prices and Economy" first. The server refuses a model that cannot be used.
 */
export function IngestModelSection({ version }: { version: number }) {
  const [choices, setChoices] = useState<Choice[]>([]);
  const [model, setModel] = useState("");
  const [revision, setRevision] = useState(0);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [settings, models] = await Promise.all([
          api().GET("/api/v1/ingest/settings"),
          api().GET("/api/v1/ai/models", { params: { query: { enabled: true, available: true } } }),
        ]);
        if (cancelled) return;
        if (settings.data) {
          setModel(settings.data.model_id ?? "");
          setRevision(settings.data.revision);
        }
        if (models.data) {
          setChoices(
            models.data.data
              .filter((m) => m.supports_vision === true)
              .map((m) => ({ id: m.id, label: `${m.display_name} (${m.provider})` })),
          );
        }
      } catch {
        if (!cancelled) setMessage({ ok: false, text: NETWORK });
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [version]);

  async function save() {
    setBusy(true);
    setMessage(null);
    try {
      const { data, error, response } = await api().PUT("/api/v1/ingest/settings", {
        params: { header: { "If-Match": ifMatch(revision) } },
        body: { model_id: model === "" ? null : model },
      });
      if (data) {
        setRevision(data.revision);
        setMessage({ ok: true, text: "Saved. Documents are read with this model from now on." });
      } else {
        setMessage({ ok: false, text: errorMessage(error, response.status) });
      }
    } catch {
      setMessage({ ok: false, text: NETWORK });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Reading documents" className="grid gap-3">
      <div>
        <h2 className="text-lg font-medium">Reading uploaded documents</h2>
        <p className="mt-1 max-w-2xl text-sm text-zinc-700 dark:text-zinc-300">
          The model that reads the pages of uploaded papers. It must be turned on above and be able
          to read pictures. Each page costs against the budget of the person who asked for it.
        </p>
      </div>
      <form
        aria-label="Reading documents"
        className="flex flex-wrap items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <label className="grid min-w-64 gap-1 text-sm">
          Model
          <select
            className={FIELD}
            value={model}
            onChange={(event) => setModel(event.target.value)}
          >
            <option value="">None chosen</option>
            {choices.map((choice) => (
              <option key={choice.id} value={choice.id}>
                {choice.label}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={busy} className={PRIMARY}>
          Save
        </button>
      </form>
      {choices.length === 0 && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          No turned-on model is known to read pictures yet. Turn one on above, and under “Prices and
          Economy” record that it reads pictures if the provider does not say so.
        </p>
      )}
      {message && (
        <p role={message.ok ? "status" : "alert"} className={message.ok ? OK : ALERT}>
          {message.text}
        </p>
      )}
    </section>
  );
}
