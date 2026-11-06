const OPEN = String.raw`\(`;
const CLOSE = String.raw`\)`;

/**
 * Put an inline equation into a paragraph's text. Inline equations are written between `\(` and
 * `\)` (ADR-0016). `start` and `end` are the cursor, or the selected text, which is replaced; they
 * are kept inside the text. An empty equation, or one holding `\)` (which would close the inline
 * equation early and let the rest be read as text), changes nothing.
 */
export function insertInlineEquation(
  text: string,
  latex: string,
  start: number,
  end: number,
): string {
  const source = latex.trim();
  if (source === "" || source.includes(CLOSE)) return text;
  const a = Math.min(Math.max(0, Math.min(start, end)), text.length);
  const b = Math.min(Math.max(0, Math.max(start, end)), text.length);
  return `${text.slice(0, a)}${OPEN}${source}${CLOSE}${text.slice(b)}`;
}
