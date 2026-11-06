"use client";

import { ItemsField } from "@/components/items-field";
import { correctIds, optionsOf, setCorrect, type Content } from "@/lib/question-content";
import { itemsOf, mappingOf, setMapping } from "@/lib/question-parts";

const LETTERS = "ABCDEFGHIJ";
// As the student preview shows them: List I items are P, Q, R...; List II items are 1, 2, 3...
const LEFT_LABELS = "PQRSTUVWXY";
const leftName = (index: number) => LEFT_LABELS[index] ?? String(index + 1);
const rightName = (index: number) => String(index + 1);

/**
 * The editor of a matching question: List I and List II, then four options. Each option says, for
 * every item of List I, which items of List II it matches (one or more), and one option is marked
 * correct. Items carry the names the student preview gives them; the stable ids behind them are
 * never shown. Whether the marked option is allowed (a List II item under two List I items, in the
 * correct option) is the server's finding.
 */
export function MatchingField({
  content,
  onChange,
  disabled = false,
}: {
  content: Content;
  onChange: (next: Content) => void;
  disabled?: boolean;
}) {
  const left = itemsOf(content, "left");
  const right = itemsOf(content, "right");
  const options = optionsOf(content);
  const correct = new Set(correctIds(content));

  return (
    <div className="grid gap-6">
      <ItemsField
        content={content}
        onChange={onChange}
        field="left"
        prefix="L"
        legend="List I"
        nameOf={(index) => `List I item ${leftName(index)}`}
        addLabel="Add List I item"
        disabled={disabled}
      />
      <ItemsField
        content={content}
        onChange={onChange}
        field="right"
        prefix="R"
        legend="List II"
        nameOf={(index) => `List II item ${rightName(index)}`}
        addLabel="Add List II item"
        disabled={disabled}
      />
      <fieldset disabled={disabled} className="grid gap-4">
        <legend className="mb-1 text-sm font-medium">
          Options (say what each one matches, and mark the correct one)
        </legend>
        {options.map((option, index) => {
          const letter = LETTERS[index] ?? String(index + 1);
          const mapping = mappingOf(content, option.id);
          return (
            <div
              key={option.id}
              className="grid gap-3 rounded-md border border-zinc-200 p-3 dark:border-zinc-800"
            >
              <label className="flex items-center gap-2 text-sm font-medium">
                <input
                  type="radio"
                  name="correct-option"
                  aria-label={`Option ${letter} is correct`}
                  checked={correct.has(option.id)}
                  onChange={(event) =>
                    onChange(setCorrect(content, option.id, event.target.checked))
                  }
                />
                Option {letter}
                <span className="font-normal text-zinc-600 dark:text-zinc-400">
                  {correct.has(option.id) ? "· correct" : ""}
                </span>
              </label>
              {left.map((from, row) => (
                <div key={from.id} className="flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span aria-hidden="true" className="w-16 text-sm font-medium">
                    {leftName(row)} →
                  </span>
                  {right.map((to, column) => (
                    <label key={to.id} className="flex items-center gap-1 text-sm">
                      <input
                        type="checkbox"
                        aria-label={`Option ${letter}: ${leftName(row)} matches ${rightName(column)}`}
                        checked={(mapping[from.id] ?? []).includes(to.id)}
                        onChange={(event) =>
                          onChange(
                            setMapping(content, option.id, from.id, to.id, event.target.checked),
                          )
                        }
                      />
                      {rightName(column)}
                    </label>
                  ))}
                </div>
              ))}
            </div>
          );
        })}
      </fieldset>
    </div>
  );
}
