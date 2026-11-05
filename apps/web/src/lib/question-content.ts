/**
 * Helpers for a question's content (schema version 1, ADR-0016) as the editor changes it. They
 * only build and change the JSON; what is wrong with it is decided by the server's findings.
 */

export type Block = Record<string, unknown> & { kind?: unknown };
export type Content = Record<string, unknown>;

export type Format = { value: string; label: string; hint: string };

/** The eight formats an author can start (the ninth, passage-based, is shared context: 3h). */
export const FORMATS: Format[] = [
  { value: "SCQ", label: "Single correct", hint: "Four options, one is right" },
  { value: "MULTI_CORRECT", label: "Multiple correct", hint: "Four options, one or more are right" },
  { value: "INTEGER", label: "Integer", hint: "A whole number from 0 to 999" },
  { value: "SINGLE_DIGIT", label: "Single digit", hint: "A whole number from 0 to 9" },
  { value: "NUMERICAL", label: "Numerical", hint: "A value or a range, two decimal places" },
  { value: "MATCHING", label: "Matching", hint: "Match List I to List II, four options" },
  { value: "ASSERTION_REASON", label: "Assertion–reason", hint: "An assertion, a reason, four options" },
  { value: "MULTIPLE_STATEMENT", label: "Multiple statement", hint: "Statements, four options" },
];

export const formatLabel = (type: unknown): string =>
  FORMATS.find((format) => format.value === type)?.label ?? "Unknown format";

export const paragraph = (text = ""): Block => ({ kind: "paragraph", text });

const OPTION_IDS = ["A", "B", "C", "D"];
const textOptions = (): Block[] => OPTION_IDS.map((id) => ({ id, content: [paragraph()] }));

/**
 * The content of a new question of ``type``: an empty stem and the parts its format needs, so
 * the findings say at once what is still to be written. Nothing here is an answer.
 */
export function emptyContent(type: string, language = "en"): Content {
  const content: Content = {
    schema_version: 1,
    question_type: type,
    language,
    stem: [paragraph()],
  };
  switch (type) {
    case "SCQ":
    case "MULTI_CORRECT":
      content.options = textOptions();
      break;
    case "ASSERTION_REASON":
      content.assertion = [paragraph()];
      content.reason = [paragraph()];
      content.options = textOptions();
      break;
    case "MULTIPLE_STATEMENT":
      content.statements = ["S1", "S2"].map((id) => ({ id, content: [paragraph()] }));
      content.options = textOptions();
      break;
    case "MATCHING":
      content.left = ["L1", "L2"].map((id) => ({ id, content: [paragraph()] }));
      content.right = ["R1", "R2"].map((id) => ({ id, content: [paragraph()] }));
      content.options = OPTION_IDS.map((id) => ({ id, mapping: {} }));
      break;
    default:
      break; // integer, single digit and numerical have no parts besides the answer
  }
  return content;
}

/** A list of blocks with the block at ``index`` replaced; the list is returned unchanged if
 *  ``index`` is outside it. */
export function replaceBlock(blocks: Block[], index: number, block: Block): Block[] {
  if (index < 0 || index >= blocks.length) return blocks;
  return blocks.map((existing, i) => (i === index ? block : existing));
}

export function removeBlock(blocks: Block[], index: number): Block[] {
  return blocks.filter((_, i) => i !== index);
}

/** The blocks of a field, or an empty list when it is missing or not a list. */
export function blocksOf(value: unknown): Block[] {
  return Array.isArray(value)
    ? value.filter((b): b is Block => typeof b === "object" && b !== null && !Array.isArray(b))
    : [];
}

/** A copy of ``content`` with one field set (the original is not changed). */
export function withField(content: Content, field: string, value: unknown): Content {
  return { ...content, [field]: value };
}

/** "Saved 10:42" in the person's own time zone. */
export function savedLabel(at: Date): string {
  return `Saved ${at.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
}
