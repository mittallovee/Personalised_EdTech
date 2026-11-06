/**
 * Changing the labels of a question (`content.metadata`: class to topic, concepts, difficulty,
 * Bloom, past-year details). Like the other editor helpers these only build the JSON; whether an
 * id exists in this coaching's catalogue, whether a concept belongs to the subject and so on is
 * decided by the server and shown as findings. Nothing here changes the content it is given.
 */
import type { Content } from "@/lib/question-content";

export type Metadata = Record<string, unknown>;

/** The syllabus levels a question is placed in, from the class down. */
export const LADDER = ["class_id", "subject_id", "chapter_id", "topic_id", "subtopic_id"] as const;
export type Level = (typeof LADDER)[number];

const EXAM_FIELDS = ["exam_id", "exam_year", "exam_date", "exam_shift", "paper_code"];

/** The labels, or an empty object when there are none yet (or they are not an object). */
export function metadataOf(content: Content): Metadata {
  const value = content.metadata;
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Metadata)
    : {};
}

/** A copy of ``content`` whose labels have ``patch`` applied; a patched value of ``undefined`` removes the label. */
function patched(content: Content, patch: Metadata): Content {
  const next: Metadata = { ...metadataOf(content), ...patch };
  for (const key of Object.keys(next)) if (next[key] === undefined) delete next[key];
  return { ...content, metadata: next };
}

/**
 * Pick a place in the syllabus (an empty id clears it). Everything below it is cleared, because it
 * belonged to the old choice; a new subject also clears the concepts, which belong to one subject.
 * Picking what is already picked returns the same content.
 */
export function setPickedLevel(content: Content, level: Level, id: string): Content {
  const meta = metadataOf(content);
  const value = id === "" ? undefined : id;
  if (meta[level] === value) return content;
  const patch: Metadata = { [level]: value };
  for (const below of LADDER.slice(LADDER.indexOf(level) + 1)) patch[below] = undefined;
  if (level === "subject_id" || level === "class_id") {
    patch.primary_concept_id = undefined;
    patch.secondary_concept_ids = undefined;
  }
  return patched(content, patch);
}

const others = (meta: Metadata): string[] =>
  Array.isArray(meta.secondary_concept_ids)
    ? meta.secondary_concept_ids.filter((id): id is string => typeof id === "string")
    : [];

/** The main concept; if it was one of the other concepts it leaves that list. */
export function setMainConcept(content: Content, id: string): Content {
  const remaining = others(metadataOf(content)).filter((other) => other !== id);
  return patched(content, {
    primary_concept_id: id === "" ? undefined : id,
    secondary_concept_ids: remaining.length > 0 ? remaining : undefined,
  });
}

/** Another concept, added once; the main concept is not added again. */
export function addOtherConcept(content: Content, id: string): Content {
  const meta = metadataOf(content);
  const list = others(meta);
  if (id === "" || id === meta.primary_concept_id || list.includes(id)) return content;
  return patched(content, { secondary_concept_ids: [...list, id] });
}

export function removeOtherConcept(content: Content, id: string): Content {
  const list = others(metadataOf(content));
  if (!list.includes(id)) return content;
  const remaining = list.filter((other) => other !== id);
  return patched(content, { secondary_concept_ids: remaining.length > 0 ? remaining : undefined });
}

/** The difficulty from the chooser: a whole number from 1 to 10, or none. */
export function setDifficulty(content: Content, chosen: string): Content {
  return patched(content, { difficulty: /^\d+$/.test(chosen) ? Number(chosen) : undefined });
}

/** A text label (Bloom level, an id from a list, a note), kept exactly as typed; empty removes it. */
export function setPlainText(content: Content, field: string, text: string): Content {
  return patched(content, { [field]: text === "" ? undefined : text });
}

/**
 * The year of a past-year exam. Digits become a number; anything else is kept as typed (and a
 * number too large to be exact is not rounded) so the server's finding can say what is wrong.
 */
export function setYear(content: Content, typed: string): Content {
  if (typed === "") return patched(content, { exam_year: undefined });
  const exact = /^\d+$/.test(typed) && Number.isSafeInteger(Number(typed));
  return patched(content, { exam_year: exact ? Number(typed) : typed });
}

/** Mark the question as a past-year one or not. Turning it off clears the exam details. */
export function setPastYear(content: Content, on: boolean): Content {
  const patch: Metadata = { is_pyq: on };
  if (!on) for (const field of EXAM_FIELDS) patch[field] = undefined;
  return patched(content, patch);
}
