import { grantLabel } from "@/lib/grants";

/** The kinds of record the audit log filter offers, with the words the page shows for them. */
export const ENTITY_TYPES = [
  { value: "user", label: "People's accounts" },
  { value: "membership", label: "Memberships and roles" },
  { value: "organization", label: "The coaching" },
] as const;

/** "MEMBER_GRANTS_CHANGED" or "display_name" as a sentence: "Member grants changed". */
export function humanize(code: string): string {
  const words = code.replaceAll("_", " ").toLowerCase();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function entityTypeLabel(type: string): string {
  return ENTITY_TYPES.find((t) => t.value === type)?.label ?? humanize(type);
}

/** A value from an event's before/after as text. Always text: never markup. */
function formatValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) {
    if (value.length === 0) return "none";
    return value.map((item) => formatValue(key, item)).join(", ");
  }
  if (typeof value === "string") {
    if (key === "grants") return grantLabel(value);
    return /^[A-Z][A-Z_]*$/.test(value) ? humanize(value) : value;
  }
  if (typeof value === "boolean") return value ? "yes" : "no";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/**
 * What an event changed, one line per field: "Grants: none → Quality check". A field that only
 * one side has shows "—" on the other. An event with neither side has no lines.
 */
export function changeLines(
  before: Record<string, unknown> | null,
  after: Record<string, unknown> | null,
): string[] {
  const keys = [...new Set([...Object.keys(before ?? {}), ...Object.keys(after ?? {})])];
  return keys.map(
    (key) =>
      `${humanize(key)}: ${formatValue(key, before?.[key])} → ${formatValue(key, after?.[key])}`,
  );
}
