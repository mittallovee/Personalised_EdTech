import katex from "katex";

/** The same limit as the server's (questions/rules.py): longer sources are not typeset. */
export const MAX_EQUATION_CHARS = 2000;

/**
 * KaTeX settings (ADR-0016). `trust: false` turns off everything that could make a link, an image
 * or an attribute out of a formula (\href, \url, \includegraphics, \html*); `maxSize` and
 * `maxExpand` stop a formula from drawing something huge or expanding a macro forever;
 * `throwOnError: false` shows a broken formula's source in an error style instead of failing.
 * No `macros` object is shared, so one formula cannot define a macro for the next.
 */
const OPTIONS = {
  trust: false,
  throwOnError: false,
  strict: "ignore",
  maxSize: 10,
  maxExpand: 1000,
  output: "htmlAndMathml",
} as const;

const TOO_LONG = '<span class="qb-math-error">[equation too long to show]</span>';

export type Typeset = { html: string; ok: boolean };

/**
 * KaTeX's HTML for one formula, and whether it typeset. When it did not, the HTML shows the
 * formula's source in an error style instead (KaTeX's `throwOnError: false` look).
 */
export function typeset(source: string, display: boolean): Typeset {
  if (source.length > MAX_EQUATION_CHARS) return { html: TOO_LONG, ok: false };
  const options = { ...OPTIONS, displayMode: display };
  try {
    return { html: katex.renderToString(source, { ...options, throwOnError: true }), ok: true };
  } catch {
    // A formula KaTeX cannot read (a parse error, an unknown command, a macro that expands
    // forever): show its source in the error style rather than fail.
    return { html: katex.renderToString(source, options), ok: false };
  }
}

/**
 * A formula. This is the only place in the package where HTML is put on the page, and the HTML is
 * KaTeX's output for the settings above, never question text; tests/math.test.ts feeds it hostile
 * input and tests/blocks.test.tsx checks that no other file uses raw HTML.
 */
export function Math({ source, display }: { source: string; display: boolean }) {
  const { html } = typeset(source, display);
  const Tag = display ? "div" : "span";
  // nosemgrep: qbank-no-raw-html -- KaTeX output with trust:false, see the comment above (ADR-0016)
  return <Tag className="qb-math" dangerouslySetInnerHTML={{ __html: html }} />;
}
