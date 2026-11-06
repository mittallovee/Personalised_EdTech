const OPEN = String.raw`\(`;
const CLOSE = String.raw`\)`;

/**
 * Put an inline equation into a paragraph's text. Inline equations are written between `\(` and
 * `\)` (ADR-0016). `start` and `end` are the cursor, or the selected text, which is replaced; they
 * are kept inside the text. An empty equation, or one holding `\)` (which would close the inline
 * equation early and let the rest be read as text), changes nothing.
 *
 * Also returns where the cursor is afterwards: just after the inserted equation, or at the end of
 * the selection when nothing was inserted. A caller that remembers the cursor must use this, not
 * the old one, which points into text that has changed.
 */
export function insertInlineEquationAt(
  text: string,
  latex: string,
  start: number,
  end: number,
): { text: string; cursor: number } {
  const a = Math.min(Math.max(0, Math.min(start, end)), text.length);
  const b = Math.min(Math.max(0, Math.max(start, end)), text.length);
  const source = latex.trim();
  if (source === "" || source.includes(CLOSE)) return { text, cursor: b };
  const inserted = `${OPEN}${source}${CLOSE}`;
  return { text: `${text.slice(0, a)}${inserted}${text.slice(b)}`, cursor: a + inserted.length };
}

export function insertInlineEquation(
  text: string,
  latex: string,
  start: number,
  end: number,
): string {
  return insertInlineEquationAt(text, latex, start, end).text;
}
