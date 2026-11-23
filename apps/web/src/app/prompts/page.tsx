"use client";

import type { components } from "@qbank/api-client";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { GlossarySection } from "@/components/glossary-section";
import { PromptCard } from "@/components/prompt-card";
import { PromptEditor } from "@/components/prompt-editor";
import { OPERATIONS, OPERATION_LABEL, type Operation } from "@/lib/ai-admin";
import { api, errorMessage } from "@/lib/api";
import { canEditCoaching, forOperation, inUse, type Template } from "@/lib/prompts";
import { canManageCatalogues } from "@/lib/syllabus";
import { NETWORK } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Locked = components["schemas"]["LockedPartsOut"];
type Language = components["schemas"]["LanguageOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";

/**
 * The Prompt Library (H-13): the instructions each AI operation is given. Everyone can read them
 * and keep prompts of their own; the coaching's prompts are changed by whoever holds the
 * "Manage AI prompts" grant. A saved version never changes; which one is in use is a separate,
 * recorded switch that can be rolled back.
 */
export default function PromptsPage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const [templates, setTemplates] = useState<Template[] | null>(null);
  const [locked, setLocked] = useState<Locked[]>([]);
  const [languages, setLanguages] = useState<Language[]>([]);
  const [problem, setProblem] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [creating, setCreating] = useState<string | null>(null);
  const [seed, setSeed] = useState<{ text: string; temperature: string | null }>({
    text: "",
    temperature: null,
  });
  const signedIn = me !== null;

  useEffect(() => {
    if (!signedIn) return;
    let cancelled = false;
    async function load() {
      try {
        const [list, parts, langs] = await Promise.all([
          api().GET("/api/v1/ai/prompts"),
          api().GET("/api/v1/ai/prompts/locked"),
          api().GET("/api/v1/languages"),
        ]);
        if (cancelled) return;
        if (list.data) {
          setTemplates(list.data.data);
          setProblem(null);
        } else {
          setProblem(errorMessage(list.error as never, list.response.status));
        }
        if (parts.data) setLocked(parts.data.data);
        if (langs.data) setLanguages(langs.data);
      } catch {
        if (!cancelled) setProblem(NETWORK);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [signedIn, attempt]);

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

  const reload = () => setAttempt((n) => n + 1);

  /** Start a new prompt from the text now in use (the platform's default), so nobody begins blank. */
  async function startWriting(scope: "COACHING" | "PERSONAL", operation: Operation) {
    const base = inUse(templates ?? [], operation);
    let text = "";
    let temperature: string | null = null;
    if (base?.active_version) {
      try {
        const { data } = await api().GET("/api/v1/ai/prompts/versions/{version_id}", {
          params: { path: { version_id: base.active_version.id } },
        });
        if (data) {
          text = data.instructions;
          temperature = data.temperature;
        }
      } catch {
        // Starting from an empty box is still fine.
      }
    }
    setSeed({ text, temperature });
    setCreating(`${scope}:${operation}`);
  }
  const mayEditCoaching = canEditCoaching(me);

  return (
    <AppShell me={me} current="prompts" onSignOut={signOut} onStopActing={stopActing}>
      <h1 className="text-2xl font-semibold">Prompt library</h1>
      <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        The instructions each AI operation is given. A run uses your coaching&apos;s prompt if it
        has switched one on, otherwise the platform&apos;s default. You can also keep prompts of
        your own and pick one when you run an operation. The safety rules and the answer format are
        fixed by the system and cannot be edited.
      </p>
      {shellError && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      {problem && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {problem}
        </p>
      )}
      {!templates && !problem && <p className="mt-6">Loading…</p>}
      {templates && (
        <div className="mt-6 grid max-w-3xl gap-10">
          {OPERATIONS.map((operation) => {
            const mine = forOperation(templates, operation);
            const current = inUse(templates, operation);
            const parts = locked.find((item) => item.operation === operation);
            return (
              <section
                key={operation}
                aria-label={OPERATION_LABEL[operation]}
                className="grid gap-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-lg font-medium">{OPERATION_LABEL[operation]}</h2>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                      {current
                        ? `In use: ${current.scope === "COACHING" ? "your coaching's prompt" : "the platform default"}.`
                        : "No prompt is in use yet."}
                    </p>
                  </div>
                  <span className="flex gap-2">
                    {mayEditCoaching &&
                      !mine.some(
                        (item) => item.scope === "COACHING" && item.target_language === null,
                      ) && (
                        <button
                          type="button"
                          className={BUTTON}
                          onClick={() => void startWriting("COACHING", operation)}
                        >
                          Write the coaching&apos;s prompt
                        </button>
                      )}
                    <button
                      type="button"
                      className={BUTTON}
                      onClick={() => void startWriting("PERSONAL", operation)}
                    >
                      Write one of my own
                    </button>
                  </span>
                </div>
                {creating === `COACHING:${operation}` && (
                  <PromptEditor
                    operation={operation}
                    scope="COACHING"
                    template={null}
                    startingText={seed.text}
                    startingTemperature={seed.temperature}
                    locked={parts}
                    languages={languages}
                    onSaved={() => {
                      setCreating(null);
                      reload();
                    }}
                    onCancel={() => setCreating(null)}
                  />
                )}
                {creating === `PERSONAL:${operation}` && (
                  <PromptEditor
                    operation={operation}
                    scope="PERSONAL"
                    template={null}
                    startingText={seed.text}
                    startingTemperature={seed.temperature}
                    locked={parts}
                    languages={languages}
                    onSaved={() => {
                      setCreating(null);
                      reload();
                    }}
                    onCancel={() => setCreating(null)}
                  />
                )}
                <ul className="grid gap-3">
                  {mine.map((template) => (
                    <PromptCard
                      key={`${template.id}-${template.revision}`}
                      template={template}
                      canEdit={
                        template.scope === "PERSONAL" ||
                        (template.scope === "COACHING" && mayEditCoaching)
                      }
                      locked={parts}
                      languages={languages}
                      reload={reload}
                    />
                  ))}
                </ul>
              </section>
            );
          })}
          {canManageCatalogues(me) && <GlossarySection languages={languages} />}
        </div>
      )}
    </AppShell>
  );
}
