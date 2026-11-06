"use client";

import { Blocks, typeset } from "@qbank/content-renderer";

import type { Block } from "@/lib/question-content";

/**
 * How one paragraph or equation will look to a student, shown beneath its box as it is typed. It
 * uses the very renderer the student preview uses, so there is nothing to disagree about. A
 * paragraph with no inline equation looks like its text, so it gets no preview; an equation that
 * cannot be typeset says so instead of showing KaTeX's error style.
 */
export function LivePreview({ block }: { block: Block }) {
  if (block.kind === "paragraph") {
    if (typeof block.text !== "string" || !block.text.includes("\\(")) return null;
  } else if (block.kind === "equation") {
    if (typeof block.source !== "string" || block.source.trim() === "") return null;
    if (!typeset(block.source, true).ok) {
      return (
        <p className="qb-live-preview text-sm text-amber-800 dark:text-amber-300">
          This equation could not be shown yet. Check the LaTeX.
        </p>
      );
    }
  } else {
    return null;
  }
  return (
    <div className="qb-live-preview overflow-x-auto rounded-md bg-zinc-50 px-3 py-2 dark:bg-zinc-900">
      <span className="sr-only">Preview</span>
      <Blocks blocks={[block]} />
    </div>
  );
}
