"use client";

import { BlocksField } from "@/components/blocks-field";
import {
  correctIds,
  optionsOf,
  setCorrect,
  setOptionContent,
  type Content,
} from "@/lib/question-content";

const LETTERS = "ABCDEFGHIJ";

/**
 * The four options of a single-correct or multiple-correct question, each written as content
 * blocks, with the control that marks the correct one(s). Options are labelled A to D by position,
 * as a student sees them; their stable ids (which the answer refers to) are never shown or changed.
 * Marking changes `answer` (`{option_id}` or `{option_ids}`); with nothing marked there is none.
 */
export function OptionsField({
  content,
  onChange,
  disabled = false,
}: {
  content: Content;
  onChange: (next: Content) => void;
  disabled?: boolean;
}) {
  const options = optionsOf(content);
  const correct = new Set(correctIds(content));
  const multiple = content.question_type === "MULTI_CORRECT";

  return (
    <fieldset disabled={disabled} className="grid gap-4">
      <legend className="mb-1 text-sm font-medium">
        Options {multiple ? "(mark every correct one)" : "(mark the correct one)"}
      </legend>
      {options.map((option, index) => {
        const letter = LETTERS[index] ?? String(index + 1);
        return (
          <div
            key={option.id}
            className="grid gap-3 rounded-md border border-zinc-200 p-3 dark:border-zinc-800"
          >
            <label className="flex items-center gap-2 text-sm font-medium">
              <input
                type={multiple ? "checkbox" : "radio"}
                name="correct-option"
                aria-label={`Option ${letter} is correct`}
                checked={correct.has(option.id)}
                onChange={(event) => onChange(setCorrect(content, option.id, event.target.checked))}
              />
              Option {letter}
              <span className="font-normal text-zinc-600 dark:text-zinc-400">
                {correct.has(option.id) ? "· correct" : ""}
              </span>
            </label>
            <BlocksField
              label={`Option ${letter}`}
              blocks={option.content}
              onChange={(next) => onChange(setOptionContent(content, option.id, next))}
            />
          </div>
        );
      })}
    </fieldset>
  );
}
