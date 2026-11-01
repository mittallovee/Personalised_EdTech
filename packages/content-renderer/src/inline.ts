/**
 * Splits a paragraph's text into plain text and inline equations (ADR-0016).
 *
 * Inline equations sit between `\(` and `\)`. Outside an equation a doubled backslash is one
 * literal backslash, so `\\(` shows `\(` as text. Inside an equation the source is LaTeX and is
 * kept exactly as written (`\\` there is a line break). This follows the server's own check
 * (questions/blocks.py), but is forgiving: an equation that is never closed, or a stray closing
 * mark, is shown as the text it is, and nothing here throws.
 */

export type InlineSegment = { type: "text"; text: string } | { type: "math"; source: string };

export function splitInline(text: string): InlineSegment[] {
  const segments: InlineSegment[] = [];
  let plain = "";
  const flush = () => {
    if (plain) segments.push({ type: "text", text: plain });
    plain = "";
  };

  let i = 0;
  while (i < text.length) {
    const here = text[i];
    const next = text[i + 1];
    if (here === "\\" && next === "\\") {
      plain += "\\";
      i += 2;
    } else if (here === "\\" && next === "(") {
      const end = text.indexOf("\\)", i + 2);
      if (end === -1) {
        plain += text.slice(i); // never closed: it is just text
        break;
      }
      const source = text.slice(i + 2, end);
      if (source.trim()) {
        flush();
        segments.push({ type: "math", source });
      }
      i = end + 2;
    } else {
      plain += here;
      i += 1;
    }
  }
  flush();
  return segments;
}
