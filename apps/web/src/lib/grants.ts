import type { components } from "@qbank/api-client";

type Grant = components["schemas"]["SetGrants"]["grants"][number];

/** The grants a faculty member can be given, with the words the screens show for them. */
export const GRANTS = [
  { name: "QC", label: "Quality check", help: "Check questions and record findings" },
  { name: "APPROVE", label: "Approve", help: "Approve checked questions" },
  { name: "PUBLISH", label: "Publish", help: "Publish approved questions" },
  { name: "EDIT_OTHERS", label: "Edit others' questions", help: "Change questions others wrote" },
  { name: "MANAGE_AI_PROMPTS", label: "Manage AI prompts", help: "Save and share AI prompts" },
] as const satisfies readonly { name: Grant; label: string; help: string }[];

// A grant added to or removed from the API contract makes this line fail to compile, so the
// list above can never drift from what the API accepts.
const _listIsComplete: Exclude<Grant, (typeof GRANTS)[number]["name"]> extends never
  ? true
  : never = true;
void _listIsComplete;

export function grantLabel(name: string): string {
  return GRANTS.find((grant) => grant.name === name)?.label ?? name;
}
