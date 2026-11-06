"use client";

import { BlocksField } from "@/components/blocks-field";
import type { Content } from "@/lib/question-content";
import {
  MAX_ITEMS,
  MIN_ITEMS,
  addItem,
  itemsOf,
  removeItem,
  setItemContent,
} from "@/lib/question-parts";

const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";

/**
 * A list of items each written as content blocks: the statements of a multiple-statement question,
 * or the List I / List II columns of a matching one. Items are named by position as a student sees
 * them; their stable ids, which options and answers refer to, are never shown or changed. The list
 * holds from 2 to 10 items.
 */
export function ItemsField({
  content,
  onChange,
  field,
  prefix,
  legend,
  nameOf,
  addLabel,
  disabled = false,
}: {
  content: Content;
  onChange: (next: Content) => void;
  /** The content field that holds the list: `statements`, `left` or `right`. */
  field: string;
  /** The start of a new item's id: `S`, `L` or `R`. */
  prefix: string;
  legend: string;
  /** What the item at a position is called on screen, like "Statement 2" or "List I item Q". */
  nameOf: (index: number) => string;
  /** The text of the add button, like "Add statement". */
  addLabel: string;
  disabled?: boolean;
}) {
  const items = itemsOf(content, field);
  return (
    <fieldset disabled={disabled} className="grid gap-4">
      <legend className="mb-1 text-sm font-medium">{legend}</legend>
      {items.map((item, index) => (
        <div
          key={item.id}
          className="grid gap-3 rounded-md border border-zinc-200 p-3 dark:border-zinc-800"
        >
          <BlocksField
            label={nameOf(index)}
            blocks={item.content}
            onChange={(next) => onChange(setItemContent(content, field, item.id, next))}
          />
          <button
            type="button"
            className="justify-self-start text-sm underline disabled:opacity-50 disabled:no-underline"
            disabled={items.length <= MIN_ITEMS}
            onClick={() => onChange(removeItem(content, field, item.id))}
          >
            Remove {nameOf(index)}
          </button>
        </div>
      ))}
      <div className="flex items-center gap-3">
        <button
          type="button"
          className={BUTTON}
          disabled={items.length >= MAX_ITEMS}
          onClick={() => onChange(addItem(content, field, prefix))}
        >
          {addLabel}
        </button>
        <span className="text-sm text-zinc-600 dark:text-zinc-400">
          {items.length} of {MAX_ITEMS} (at least {MIN_ITEMS})
        </span>
      </div>
    </fieldset>
  );
}
