"use client";

import type { components } from "@qbank/api-client";
import { useEffect, useState } from "react";

import { api, errorMessage, ifMatch } from "@/lib/api";
import { NETWORK } from "@/lib/use-catalogue";

type Entry = components["schemas"]["GlossaryEntryOut"];
type Language = components["schemas"]["LanguageOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/**
 * The translation glossary (H-14): terms the coaching wants translated one fixed way, per target
 * language. A translation is given only the entries whose source term appears in the question.
 * Owner and admins only; the API refuses everyone else.
 */
export function GlossarySection({ languages }: { languages: Language[] }) {
  const [entries, setEntries] = useState<Entry[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [language, setLanguage] = useState("");
  const [form, setForm] = useState({ source: "", target: "", note: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const {
          data,
          error: failure,
          response,
        } = await api().GET("/api/v1/ai/glossary", {
          params: { query: { language: language || undefined } },
        });
        if (cancelled) return;
        if (data) {
          setEntries(data.data);
          setProblem(null);
        } else {
          setProblem(
            response.status === 403
              ? "Only the Owner and admins may see or change the glossary."
              : errorMessage(failure as never, response.status),
          );
        }
      } catch {
        if (!cancelled) setProblem(NETWORK);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [language, attempt]);

  async function add() {
    if (busy) return;
    setError(null);
    if (language === "") {
      setError("Choose the language first.");
      return;
    }
    if (form.source.trim() === "" || form.target.trim() === "") {
      setError("Both terms are needed.");
      return;
    }
    setBusy(true);
    try {
      const {
        data,
        error: failure,
        response,
      } = await api().POST("/api/v1/ai/glossary", {
        body: {
          language,
          source_term: form.source,
          target_term: form.target,
          note: form.note.trim() === "" ? null : form.note,
        },
      });
      if (data) {
        setForm({ source: "", target: "", note: "" });
        setAttempt((n) => n + 1);
      } else {
        setError(errorMessage(failure as never, response.status));
      }
    } catch {
      setError(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  async function remove(entry: Entry) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const { error: failure, response } = await api().DELETE("/api/v1/ai/glossary/{entry_id}", {
        params: { path: { entry_id: entry.id }, header: { "If-Match": ifMatch(entry.revision) } },
      });
      if (response.ok || response.status === 412) setAttempt((n) => n + 1);
      else setError(errorMessage(failure as never, response.status));
    } catch {
      setError(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  const nameOf = (tag: string) => languages.find((item) => item.tag === tag)?.english_name ?? tag;

  return (
    <section aria-label="Translation glossary" className="grid gap-3">
      <div>
        <h2 className="text-lg font-medium">Translation glossary</h2>
        <p className="max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          Terms your coaching wants translated one fixed way, such as &quot;work done&quot; into
          your Hindi term. A translation is given only the entries whose source term appears in the
          question.
        </p>
      </div>
      {problem && (
        <p role="alert" className={ALERT}>
          {problem}
        </p>
      )}
      {!problem && (
        <>
          <label className="grid max-w-xs gap-1 text-sm">
            Language
            <select
              value={language}
              onChange={(event) => {
                setEntries(null);
                setLanguage(event.target.value);
              }}
              className={FIELD}
            >
              <option value="">All languages</option>
              {languages.map((item) => (
                <option key={item.tag} value={item.tag}>
                  {item.english_name}
                </option>
              ))}
            </select>
          </label>
          <form
            aria-label="Add a glossary term"
            className="grid gap-3 sm:grid-cols-3"
            onSubmit={(event) => {
              event.preventDefault();
              void add();
            }}
          >
            <label className="grid gap-1 text-sm">
              In the question
              <input
                value={form.source}
                onChange={(event) => setForm({ ...form, source: event.target.value })}
                className={FIELD}
              />
            </label>
            <label className="grid gap-1 text-sm">
              Must become
              <input
                value={form.target}
                onChange={(event) => setForm({ ...form, target: event.target.value })}
                className={FIELD}
              />
            </label>
            <label className="grid gap-1 text-sm">
              Note (optional)
              <input
                value={form.note}
                onChange={(event) => setForm({ ...form, note: event.target.value })}
                className={FIELD}
              />
            </label>
            <div className="sm:col-span-3">
              <button type="submit" disabled={busy} className={PRIMARY}>
                Add the term
              </button>
            </div>
          </form>
          {error && (
            <p role="alert" className={ALERT}>
              {error}
            </p>
          )}
          {!entries && <p>Loading…</p>}
          {entries && entries.length === 0 && <p className="text-sm">No terms yet.</p>}
          {entries && entries.length > 0 && (
            <ul className="grid gap-2">
              {entries.map((entry) => (
                <li
                  key={entry.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800"
                >
                  <span>
                    <strong>{nameOf(entry.language)}:</strong> {entry.source_term} →{" "}
                    {entry.target_term}
                    {entry.note && (
                      <span className="text-zinc-600 dark:text-zinc-400"> ({entry.note})</span>
                    )}
                  </span>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void remove(entry)}
                    className={BUTTON}
                    aria-label={`Remove ${entry.source_term}`}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
