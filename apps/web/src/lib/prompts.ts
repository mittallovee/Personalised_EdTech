import type { components, Me } from "@qbank/api-client";

export type Template = components["schemas"]["TemplateOut"];
export type VersionSummary = components["schemas"]["VersionSummary"];
export type Scope = components["schemas"]["Scope"];
type Operation = components["schemas"]["Operation"];

export const SCOPE_LABEL: Record<Scope, string> = {
  PLATFORM: "Platform default",
  COACHING: "Your coaching's prompt",
  PERSONAL: "Your own prompt",
};

/**
 * Whether the coaching's prompts may be changed by this person: the `MANAGE_AI_PROMPTS` grant
 * (the Owner and admins hold every grant) or a platform admin acting in the coaching. Only a hint
 * for what to show: the API refuses everyone else (403) whatever the page shows.
 */
export function canEditCoaching(me: Me): boolean {
  if (me.acting_organization_id !== null) return true;
  return me.organization?.grants.includes("MANAGE_AI_PROMPTS") ?? false;
}

/** The templates of one operation in the order a person reads them: theirs, the coaching's, the platform's. */
export function forOperation(templates: Template[], operation: Operation): Template[] {
  const rank: Record<Scope, number> = { PERSONAL: 0, COACHING: 1, PLATFORM: 2 };
  return templates
    .filter((template) => template.operation === operation)
    .sort(
      (a, b) =>
        rank[a.scope] - rank[b.scope] ||
        (a.target_language ?? "").localeCompare(b.target_language ?? "") ||
        a.name.localeCompare(b.name),
    );
}

/** Which prompt a run will use by default, in words: the coaching's if it has an active one, else the platform's. */
export function inUse(templates: Template[], operation: Operation): Template | null {
  const mine = forOperation(templates, operation).filter(
    (template) => template.scope !== "PERSONAL" && template.active_version !== null,
  );
  return mine.find((template) => template.scope === "COACHING") ?? mine[0] ?? null;
}

export type DiffLine = components["schemas"]["PromptDiffLineOut"];

/** The mark and colour of one line of a version comparison. */
export function lineStyle(line: DiffLine): { mark: string; className: string } {
  if (line.op === "added")
    return {
      mark: "+",
      className: "bg-green-50 text-green-900 dark:bg-green-950 dark:text-green-200",
    };
  if (line.op === "removed")
    return { mark: "−", className: "bg-red-50 text-red-900 dark:bg-red-950 dark:text-red-200" };
  return { mark: " ", className: "" };
}

/** A temperature typed by a person: empty means "the provider's default"; otherwise 0 to 2. */
export function parseTemperature(
  text: string,
): { ok: true; value: string | null } | { ok: false; message: string } {
  const typed = text.trim();
  if (typed === "") return { ok: true, value: null };
  if (!/^\d(\.\d{1,2})?$/.test(typed) || Number(typed) > 2) {
    return { ok: false, message: "Use a number from 0 to 2, like 0.2, or leave it empty." };
  }
  return { ok: true, value: typed };
}
