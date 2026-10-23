import type { components, Me } from "@qbank/api-client";

export type Node = components["schemas"]["NodeOut"];
export type Kind = Node["kind"];
export type Language = components["schemas"]["LanguageOut"];

/** The kinds from the top of the syllabus down: a class holds subjects, and so on. */
const KINDS: Kind[] = ["CLASS", "SUBJECT", "CHAPTER", "TOPIC", "SUBTOPIC"];

export const KIND_NAME: Record<Kind, string> = {
  CLASS: "class",
  SUBJECT: "subject",
  CHAPTER: "chapter",
  TOPIC: "topic",
  SUBTOPIC: "subtopic",
};

export const KIND_PLURAL: Record<Kind, string> = {
  CLASS: "classes",
  SUBJECT: "subjects",
  CHAPTER: "chapters",
  TOPIC: "topics",
  SUBTOPIC: "subtopics",
};

/** What is added inside an item of this kind (a class inside "all classes" when `null`). */
export function childKind(kind: Kind | null): Kind | null {
  const next = kind === null ? 0 : KINDS.indexOf(kind) + 1;
  return KINDS[next] ?? null;
}

/**
 * Whether to show the controls that change the syllabus. Only a hint for the screen: the API
 * refuses everyone but the Owner, admins and a platform admin acting in the coaching (403).
 */
export function canManageCatalogues(me: Me): boolean {
  const role = me.organization?.role;
  return role === "OWNER" || role === "ADMIN" || me.acting_organization_id !== null;
}
