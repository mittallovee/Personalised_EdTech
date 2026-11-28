"use client";

import type { components } from "@qbank/api-client";
import { useState } from "react";

import { OPERATION_LABEL } from "@/lib/ai-admin";
import {
  budgetText,
  firstMode,
  firstModel,
  modelPrice,
  runButtonLabel,
  whyNot,
  type RunOptions,
  type Usage,
} from "@/lib/ai-run";

type Operation = components["schemas"]["Operation"];
type StartRun = components["schemas"]["StartRun"];
type Language = components["schemas"]["LanguageOut"];
type Template = components["schemas"]["TemplateOut"];

const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";
const FIELD =
  "rounded-md border border-zinc-300 bg-transparent px-2 py-1 text-sm dark:border-zinc-700";

type PromptChoice = "DEFAULT" | "PERSONAL" | "ONE_OFF";

/**
 * The dialog of the prompt library spec (4a), inline: which prompt, extra instructions, which
 * model and mode, what it may cost, and what is left of the budget. It only collects choices; the
 * server decides whether the run is allowed and says why when it is not.
 */
export function RunForm({
  operation,
  options,
  usage,
  personal,
  languages,
  sourceLanguage,
  editable,
  busy,
  onRun,
  onCancel,
}: {
  operation: Operation;
  options: RunOptions;
  usage: Usage | null;
  /** The person's own prompts for this operation. */
  personal: Template[];
  languages: Language[];
  /** The question's own language, left out of the translation choices. */
  sourceLanguage: string | null;
  editable: boolean;
  busy: boolean;
  onRun: (body: StartRun) => void;
  onCancel: () => void;
}) {
  const start = firstModel(options, operation) ?? options.models[0] ?? null;
  const [prompt, setPrompt] = useState<PromptChoice>("DEFAULT");
  const [personalId, setPersonalId] = useState(personal[0]?.id ?? "");
  const [oneOff, setOneOff] = useState("");
  const [extra, setExtra] = useState("");
  const [modelId, setModelId] = useState(start?.id ?? "");
  const [mode, setMode] = useState(firstMode(options, operation, start));
  const [language, setLanguage] = useState("");
  const [test, setTest] = useState(false);

  const model = options.models.find((entry) => entry.id === modelId) ?? null;
  const blocked = whyNot(operation, editable, test);
  const missing =
    model === null
      ? "No model is available. An admin enables one under Admin, AI."
      : operation === "TRANSLATE" && language === ""
        ? "Choose the language to translate into."
        : prompt === "PERSONAL" && personalId === ""
          ? "Choose one of your prompts."
          : prompt === "ONE_OFF" && oneOff.trim() === ""
            ? "Write the prompt for this run."
            : null;

  function submit() {
    if (model === null || blocked !== null || missing !== null) return;
    const body: StartRun = {
      operation,
      model_id: model.id,
      mode: model.economy ? mode : "NOW",
      test,
    };
    if (extra.trim() !== "") body.extra_instructions = extra.trim();
    if (prompt === "PERSONAL") body.personal_prompt_id = personalId;
    if (prompt === "ONE_OFF") body.prompt = oneOff;
    if (operation === "TRANSLATE") body.target_language = language;
    onRun(body);
  }

  return (
    <form
      aria-label={OPERATION_LABEL[operation]}
      className="grid gap-4 rounded-md border border-zinc-200 p-4 dark:border-zinc-800"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <h3 className="text-base font-semibold">{OPERATION_LABEL[operation]}</h3>

      {operation === "TRANSLATE" && (
        <label className="grid gap-1 text-sm">
          Translate into
          <select
            className={FIELD}
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
          >
            <option value="">Choose a language</option>
            {languages
              .filter((entry) => entry.tag !== sourceLanguage)
              .map((entry) => (
                <option key={entry.tag} value={entry.tag}>
                  {entry.english_name} ({entry.native_name})
                </option>
              ))}
          </select>
        </label>
      )}

      <fieldset className="grid gap-2 text-sm">
        <legend className="font-medium">Prompt</legend>
        <label className="flex items-center gap-2">
          <input
            type="radio"
            name="prompt"
            checked={prompt === "DEFAULT"}
            onChange={() => setPrompt("DEFAULT")}
          />
          Coaching default
        </label>
        <label className="flex items-center gap-2">
          <input
            type="radio"
            name="prompt"
            checked={prompt === "PERSONAL"}
            disabled={personal.length === 0}
            onChange={() => setPrompt("PERSONAL")}
          />
          My prompts
          {personal.length === 0 && (
            <span className="text-zinc-600 dark:text-zinc-400">(none saved yet)</span>
          )}
        </label>
        {prompt === "PERSONAL" && (
          <select
            aria-label="My prompt"
            className={FIELD}
            value={personalId}
            onChange={(event) => setPersonalId(event.target.value)}
          >
            {personal.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entry.name}
              </option>
            ))}
          </select>
        )}
        <label className="flex items-center gap-2">
          <input
            type="radio"
            name="prompt"
            checked={prompt === "ONE_OFF"}
            onChange={() => setPrompt("ONE_OFF")}
          />
          Custom for this run
        </label>
        {prompt === "ONE_OFF" && (
          <textarea
            aria-label="Prompt for this run"
            className={`${FIELD} min-h-24`}
            maxLength={8000}
            value={oneOff}
            onChange={(event) => setOneOff(event.target.value)}
          />
        )}
      </fieldset>

      <label className="grid gap-1 text-sm">
        Extra instructions (optional)
        <input
          className={FIELD}
          maxLength={1000}
          value={extra}
          onChange={(event) => setExtra(event.target.value)}
        />
      </label>

      <label className="grid gap-1 text-sm">
        Model
        <select
          className={FIELD}
          value={modelId}
          onChange={(event) => {
            setModelId(event.target.value);
            const next = options.models.find((entry) => entry.id === event.target.value);
            if (!next?.economy) setMode("NOW");
          }}
        >
          {options.models.length === 0 && <option value="">No model is available</option>}
          {options.models.map((entry) => (
            <option key={entry.id} value={entry.id}>
              {entry.display_name}
            </option>
          ))}
        </select>
        {model && <span className="text-zinc-600 dark:text-zinc-400">{modelPrice(model)}</span>}
      </label>

      {model?.economy && (
        <fieldset className="grid gap-1 text-sm">
          <legend className="font-medium">How fast</legend>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="mode"
              checked={mode === "NOW"}
              onChange={() => setMode("NOW")}
            />
            Now (normal price, answered at once)
          </label>
          <label className="flex items-center gap-2">
            <input
              type="radio"
              name="mode"
              checked={mode === "ECONOMY"}
              onChange={() => setMode("ECONOMY")}
            />
            Economy (about half price, done within 24 hours, you are notified)
          </label>
        </fieldset>
      )}

      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={test} onChange={(event) => setTest(event.target.checked)} />
        Test run (the same call and cost, but nothing is ever written to the question)
      </label>

      <p className="text-sm text-zinc-700 dark:text-zinc-300">
        The cost is worked out when the run starts, from the question and the prompt.
        {usage && ` ${budgetText(usage)}`}
      </p>

      {(blocked ?? missing) && (
        <p role="note" className="text-sm text-amber-800 dark:text-amber-300">
          {blocked ?? missing}
        </p>
      )}

      <div className="flex gap-2">
        <button
          type="submit"
          className={PRIMARY}
          disabled={busy || blocked !== null || missing !== null}
        >
          {busy ? "Working…" : runButtonLabel(operation)}
        </button>
        <button type="button" className={BUTTON} disabled={busy} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
