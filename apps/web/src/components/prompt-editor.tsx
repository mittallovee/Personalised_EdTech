"use client";

import type { components } from "@qbank/api-client";
import { useState } from "react";

import { api, errorMessage } from "@/lib/api";
import { OPERATION_LABEL, type Operation } from "@/lib/ai-admin";
import { parseTemperature, type Scope, type Template } from "@/lib/prompts";
import { NETWORK } from "@/lib/use-catalogue";

type Locked = components["schemas"]["LockedPartsOut"];
type Problem = components["schemas"]["ProblemOut"];
type Language = components["schemas"]["LanguageOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const OK =
  "rounded-md bg-green-50 px-3 py-2 text-sm text-green-800 dark:bg-green-950 dark:text-green-200";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/**
 * Write a new version of a prompt (PL-03 to PL-05). A saved version never changes; this makes the
 * next one. The wording is only the instructions: the safety preamble and the output format are
 * fixed on the server and shown here read-only. "Check" asks the server what is wrong with the
 * text, all at once; saving asks again.
 */
export function PromptEditor({
  operation,
  scope,
  template,
  startingText,
  startingTemperature,
  locked,
  languages,
  onSaved,
  onCancel,
}: {
  operation: Operation;
  scope: Scope;
  template: Template | null;
  startingText: string;
  startingTemperature: string | null;
  locked: Locked | undefined;
  languages: Language[];
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [text, setText] = useState(startingText);
  const [temperature, setTemperature] = useState(startingTemperature ?? "");
  const [note, setNote] = useState("");
  const [name, setName] = useState(template?.name ?? "");
  const [language, setLanguage] = useState(template?.target_language ?? "");
  const [problems, setProblems] = useState<Problem[]>([]);
  const [fieldProblem, setFieldProblem] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const isNew = template === null;
  const needsName = scope === "PERSONAL" && isNew;

  async function check() {
    setBusy(true);
    setMessage(null);
    try {
      const { data, error, response } = await api().POST("/api/v1/ai/prompts/validate", {
        body: { operation, instructions: text },
      });
      if (data) {
        setProblems(data.problems);
        if (data.ok) setMessage({ ok: true, text: "This text can be used." });
      } else {
        setMessage({ ok: false, text: errorMessage(error as never, response.status) });
      }
    } catch {
      setMessage({ ok: false, text: NETWORK });
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (busy) return;
    const found: Record<string, string> = {};
    const parsed = parseTemperature(temperature);
    if (!parsed.ok) found.temperature = parsed.message;
    if (note.trim() === "") found.note = "Say what you changed and why.";
    if (needsName && name.trim() === "") found.name = "Give the prompt a name.";
    setFieldProblem(found);
    setMessage(null);
    if (!parsed.ok || Object.keys(found).length > 0) return;
    setBusy(true);
    try {
      const { data, error, response } = await api().POST("/api/v1/ai/prompts/versions", {
        body: {
          scope,
          operation,
          template_id: template?.id ?? null,
          name: isNew ? name.trim() || null : null,
          target_language: isNew && operation === "TRANSLATE" && language ? language : null,
          instructions: text,
          temperature: parsed.value,
          change_note: note.trim(),
        },
      });
      if (data) {
        onSaved();
      } else if (response.status === 422) {
        const listed = (error as { error?: { details?: { problems?: Problem[] } } } | undefined)
          ?.error?.details?.problems;
        setProblems(Array.isArray(listed) ? listed : []);
        setMessage({ ok: false, text: errorMessage(error as never, response.status) });
      } else {
        setMessage({ ok: false, text: errorMessage(error as never, response.status) });
      }
    } catch {
      setMessage({ ok: false, text: NETWORK });
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      aria-label={`New version of the ${OPERATION_LABEL[operation]} prompt`}
      className="grid gap-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      {locked && (
        <div className="grid gap-1 rounded-md bg-zinc-50 p-3 text-sm dark:bg-zinc-900">
          <p className="font-medium">Fixed by the system (you cannot change this)</p>
          <p>{locked.safety_preamble}</p>
          <p>
            Required places for data:{" "}
            {locked.required_placeholders.map((name) => `{{${name}}}`).join(", ") || "none"}.
            {locked.optional_placeholders.length > 0 &&
              ` Optional: ${locked.optional_placeholders.map((name) => `{{${name}}}`).join(", ")}.`}{" "}
            At most {locked.max_instruction_chars} characters. The answer format is fixed too.
          </p>
        </div>
      )}
      {needsName && (
        <label className="grid gap-1 text-sm">
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} className={FIELD} />
          {fieldProblem.name && <Field text={fieldProblem.name} />}
        </label>
      )}
      {isNew && operation === "TRANSLATE" && (
        <label className="grid gap-1 text-sm">
          Only for translations into (optional)
          <select
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
            className={FIELD}
          >
            <option value="">Every language</option>
            {languages.map((item) => (
              <option key={item.tag} value={item.tag}>
                {item.english_name}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="grid gap-1 text-sm">
        Instructions
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={14}
          spellCheck={false}
          className={`${FIELD} font-mono text-sm`}
        />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1 text-sm">
          Temperature (0 to 2, optional)
          <input
            inputMode="decimal"
            value={temperature}
            onChange={(event) => setTemperature(event.target.value)}
            className={FIELD}
          />
          {fieldProblem.temperature && <Field text={fieldProblem.temperature} />}
        </label>
        <label className="grid gap-1 text-sm">
          What did you change?
          <input value={note} onChange={(event) => setNote(event.target.value)} className={FIELD} />
          {fieldProblem.note && <Field text={fieldProblem.note} />}
        </label>
      </div>
      {problems.length > 0 && (
        <ul role="alert" className={`${ALERT} grid list-disc gap-1 pl-6`}>
          {problems.map((problem) => (
            <li key={`${problem.code}-${problem.message}`}>{problem.message}</li>
          ))}
        </ul>
      )}
      {message && (
        <p role={message.ok ? "status" : "alert"} className={message.ok ? OK : ALERT}>
          {message.text}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={busy} onClick={() => void check()} className={BUTTON}>
          Check
        </button>
        <button type="submit" disabled={busy} className={PRIMARY}>
          Save as a new version
        </button>
        <button type="button" onClick={onCancel} className={BUTTON}>
          Cancel
        </button>
      </div>
      <p className="text-xs text-zinc-600 dark:text-zinc-400">
        Saving does not switch anything on. Switch the version on afterwards.
      </p>
    </form>
  );
}

function Field({ text }: { text: string }) {
  return (
    <span role="alert" className="text-red-700 dark:text-red-300">
      {text}
    </span>
  );
}
