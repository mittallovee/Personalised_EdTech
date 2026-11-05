"use client";

import { useState } from "react";

import {
  numericalAnswer,
  setNumericalAnswer,
  setWholeNumberAnswer,
  wholeNumberText,
  type Content,
  type NumericalAnswer,
} from "@/lib/question-content";

const FIELD =
  "w-40 rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";

/**
 * The answer of an integer, single-digit or numerical question: the number a student will type.
 * What is written is kept as written (a number is never rounded or reformatted); whether it is
 * allowed (a whole number in range, two decimal places) is the server's finding, shown beside it.
 */
export function TypedAnswerField({
  content,
  onChange,
  disabled = false,
}: {
  content: Content;
  onChange: (next: Content) => void;
  disabled?: boolean;
}) {
  const type = content.question_type;
  return (
    <fieldset disabled={disabled} className="grid gap-3">
      <legend className="mb-1 text-sm font-medium">Correct answer</legend>
      {type === "NUMERICAL" ? (
        <Numerical content={content} onChange={onChange} />
      ) : (
        <label className="grid gap-1 text-sm">
          <span className="text-zinc-600 dark:text-zinc-400">
            {type === "SINGLE_DIGIT" ? "A whole number from 0 to 9" : "A whole number"}
          </span>
          <input
            type="text"
            inputMode="numeric"
            autoComplete="off"
            aria-label="Correct answer"
            className={FIELD}
            value={wholeNumberText(content)}
            onChange={(event) => onChange(setWholeNumberAnswer(content, event.target.value))}
          />
        </label>
      )}
    </fieldset>
  );
}

function Numerical({ content, onChange }: { content: Content; onChange: (next: Content) => void }) {
  const answer = numericalAnswer(content);
  // The kind comes from the answer when there is one, so a question read again from the server
  // (after a conflict) shows what it now holds. Only while nothing is written is it remembered
  // here, because then there is no answer to read it from.
  const [chosen, setMode] = useState(answer.mode);
  const mode = content.answer ? answer.mode : chosen;
  const change = (patch: Partial<NumericalAnswer>) =>
    onChange(setNumericalAnswer(content, { ...answer, ...patch, mode }));

  return (
    <>
      <div role="radiogroup" aria-label="Kind of answer" className="flex gap-4 text-sm">
        {(["exact", "range"] as const).map((kind) => (
          <label key={kind} className="flex items-center gap-2">
            <input
              type="radio"
              name="numerical-mode"
              checked={mode === kind}
              onChange={() => {
                setMode(kind);
                onChange(setNumericalAnswer(content, { ...answer, mode: kind }));
              }}
            />
            {kind === "exact" ? "An exact value" : "A range"}
          </label>
        ))}
      </div>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        Write it with two decimal places, like 9.81. A range includes both ends.
      </p>
      {mode === "exact" ? (
        <NumberBox label="Value" value={answer.value} onChange={(value) => change({ value })} />
      ) : (
        <div className="flex flex-wrap gap-4">
          <NumberBox label="From" value={answer.lower} onChange={(lower) => change({ lower })} />
          <NumberBox label="To" value={answer.upper} onChange={(upper) => change({ upper })} />
        </div>
      )}
    </>
  );
}

function NumberBox({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1 text-sm">
      <span className="text-zinc-600 dark:text-zinc-400">{label}</span>
      <input
        type="text"
        inputMode="decimal"
        autoComplete="off"
        aria-label={label}
        className={FIELD}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
