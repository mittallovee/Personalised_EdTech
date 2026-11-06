"use client";

import { useRef, useState } from "react";

import { EquationVisualEditor } from "@/components/equation-visual-editor";
import { LivePreview } from "@/components/live-preview";
import { insertInlineEquationAt } from "@/lib/inline-equation";
import { paragraph, removeBlock, replaceBlock, type Block } from "@/lib/question-content";

const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";

const KIND_NAMES: Record<string, string> = {
  image: "A picture",
  table: "A table",
  list: "A list",
};

/**
 * The editor for a list of content blocks (the stem, a solution...). Paragraphs and displayed
 * equations (LaTeX) are written here; inside a paragraph an inline equation goes between `\(` and
 * `\)`. Pictures, tables and lists are not edited here yet: they are kept exactly as they are, so
 * opening and saving a question never loses one.
 */
export function BlocksField({
  label,
  blocks,
  onChange,
  disabled = false,
}: {
  label: string;
  blocks: Block[];
  onChange: (next: Block[]) => void;
  disabled?: boolean;
}) {
  // The equation whose visual editor is open (at most one): its place in the list and the source it
  // was opened with. The editor is shown only while the equation still holds that source, so
  // when the content is replaced from outside (a Reload after a conflict) or the source is
  // typed in its own box, the editor closes instead of keeping, and later saving, an old copy.
  // For a paragraph it also holds where in the text the new equation goes.
  const [editing, setEditing] = useState<{
    index: number;
    source: string;
    start: number;
    end: number;
  } | null>(null);
  // The cursor (or selection) last seen in each paragraph box, kept so that a click on a button,
  // which moves focus away, still knows where to put an inline equation.
  const cursor = useRef<{ index: number; start: number; end: number } | null>(null);
  return (
    <fieldset disabled={disabled} className="grid gap-3">
      <legend className="mb-1 text-sm font-medium">{label}</legend>
      {blocks.map((block, index) => {
        const where = `${label}, block ${index + 1}`;
        if (block.kind === "paragraph" || block.kind === "equation") {
          const equation = block.kind === "equation";
          const value = String(equation ? (block.source ?? "") : (block.text ?? ""));
          const session = editing?.index === index && editing.source === value ? editing : null;
          return (
            <div key={index} className="grid gap-1">
              <label className="grid gap-1 text-sm">
                <span className="text-zinc-600 dark:text-zinc-400">
                  {equation ? "Equation (LaTeX)" : "Paragraph"}
                </span>
                <textarea
                  aria-label={`${where}: ${equation ? "equation" : "paragraph"}`}
                  value={value}
                  rows={Math.min(12, Math.max(equation ? 2 : 3, value.split("\n").length))}
                  spellCheck={!equation}
                  className={`${FIELD} ${equation ? "font-mono text-sm" : ""}`}
                  onSelect={(event) => {
                    cursor.current = {
                      index,
                      start: event.currentTarget.selectionStart,
                      end: event.currentTarget.selectionEnd,
                    };
                  }}
                  onChange={(event) =>
                    onChange(
                      replaceBlock(
                        blocks,
                        index,
                        equation
                          ? { kind: "equation", format: "latex", source: event.target.value }
                          : { kind: "paragraph", text: event.target.value },
                      ),
                    )
                  }
                />
              </label>
              <LivePreview block={block} />
              {session && (
                <EquationVisualEditor
                  initial={equation ? value : ""}
                  onCancel={() => setEditing(null)}
                  onUse={(latex) => {
                    if (equation) {
                      onChange(
                        replaceBlock(blocks, index, {
                          kind: "equation",
                          format: "latex",
                          source: latex,
                        }),
                      );
                    } else {
                      const done = insertInlineEquationAt(value, latex, session.start, session.end);
                      // The remembered cursor now sits after the new equation, so a second insert
                      // (without clicking back into the box) goes after it, not into it.
                      cursor.current = { index, start: done.cursor, end: done.cursor };
                      onChange(replaceBlock(blocks, index, { kind: "paragraph", text: done.text }));
                    }
                    setEditing(null);
                  }}
                />
              )}
              <div className="flex gap-4">
                {!session && (
                  <button
                    type="button"
                    className="text-sm underline"
                    aria-label={`${equation ? "Visual editor for" : "Insert equation in"} ${where}`}
                    onClick={() => {
                      const seen = cursor.current?.index === index ? cursor.current : null;
                      setEditing({
                        index,
                        source: value,
                        start: seen?.start ?? value.length,
                        end: seen?.end ?? value.length,
                      });
                    }}
                  >
                    {equation ? "Visual editor" : "Insert equation"}
                  </button>
                )}
                <button
                  type="button"
                  className="justify-self-start text-sm underline"
                  onClick={() => {
                    setEditing(null);
                    onChange(removeBlock(blocks, index));
                  }}
                >
                  Remove {equation ? "equation" : "paragraph"} {index + 1}
                </button>
              </div>
            </div>
          );
        }
        return (
          <div
            key={index}
            className="rounded-md border border-dashed border-zinc-300 px-3 py-2 text-sm dark:border-zinc-700"
          >
            {KIND_NAMES[String(block.kind)] ?? "Other content"} is kept as it is; editing it comes
            in a later update.
          </div>
        );
      })}
      <div className="flex gap-2">
        <button type="button" className={BUTTON} onClick={() => onChange([...blocks, paragraph()])}>
          Add paragraph
        </button>
        <button
          type="button"
          className={BUTTON}
          onClick={() => onChange([...blocks, { kind: "equation", format: "latex", source: "" }])}
        >
          Add equation
        </button>
      </div>
    </fieldset>
  );
}
