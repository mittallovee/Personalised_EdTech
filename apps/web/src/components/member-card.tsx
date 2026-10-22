"use client";

import type { components } from "@qbank/api-client";

import { ConfirmPanel } from "@/components/confirm-panel";
import { GrantsEditor } from "@/components/grants-editor";
import { grantLabel } from "@/lib/grants";

export type Member = components["schemas"]["MemberOut"];

/** The inline panel open under a person. */
export type Panel = "grants" | "role" | "remove" | "transfer";

const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";

function capitalised(word: string): string {
  return word.charAt(0) + word.slice(1).toLowerCase();
}

/**
 * One person: who they are, their grants, and a button for each action the API says the signed-in
 * person may take on them (`member.actions`). The card holds no permission rules.
 */
export function MemberCard({
  member,
  panel,
  busy,
  error,
  onOpen,
  onClose,
  onNewLink,
  onSaveGrants,
  onChangeRole,
  onRemove,
  onTransfer,
}: {
  member: Member;
  panel: Panel | null;
  busy: boolean;
  error: string | null;
  onOpen: (panel: Panel) => void;
  onClose: () => void;
  onNewLink: (kind: "activation" | "reset") => void;
  onSaveGrants: (grants: string[]) => void;
  onChangeRole: () => void;
  onRemove: () => void;
  onTransfer: () => void;
}) {
  const can = (action: string) => member.actions.includes(action);
  const name = member.display_name;
  const promoting = member.role === "FACULTY";

  return (
    <li className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <span className="font-medium">{name}</span>
          <span className="ml-2 text-sm text-zinc-500">{member.email}</span>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="rounded-full bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">
            {capitalised(member.role)}
          </span>
          {member.account_status !== "ACTIVE" && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-950 dark:text-amber-200">
              {member.account_status === "INVITED" ? "Invited" : "Disabled"}
            </span>
          )}
        </div>
      </div>
      <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
        {member.role !== "FACULTY"
          ? "Holds every grant"
          : member.grants.length === 0
            ? "No grants"
            : `Grants: ${member.grants.map(grantLabel).join(", ")}`}
      </p>

      {member.actions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {can("SET_GRANTS") && (
            <button type="button" className={BUTTON} onClick={() => onOpen("grants")}>
              Edit grants
            </button>
          )}
          {can("NEW_ACTIVATION_LINK") && (
            <button
              type="button"
              className={BUTTON}
              disabled={busy}
              onClick={() => onNewLink("activation")}
            >
              New activation link
            </button>
          )}
          {can("NEW_RESET_LINK") && (
            <button
              type="button"
              className={BUTTON}
              disabled={busy}
              onClick={() => onNewLink("reset")}
            >
              Password-reset link
            </button>
          )}
          {can("CHANGE_ROLE") && (
            <button type="button" className={BUTTON} onClick={() => onOpen("role")}>
              {promoting ? "Make admin" : "Make faculty"}
            </button>
          )}
          {can("TRANSFER_OWNERSHIP") && (
            <button type="button" className={BUTTON} onClick={() => onOpen("transfer")}>
              Make owner
            </button>
          )}
          {can("REMOVE") && (
            <button type="button" className={BUTTON} onClick={() => onOpen("remove")}>
              Remove
            </button>
          )}
        </div>
      )}

      {panel === "grants" && (
        <GrantsEditor
          name={name}
          current={member.grants}
          busy={busy}
          onSave={onSaveGrants}
          onCancel={onClose}
        />
      )}
      {panel === "role" && (
        <ConfirmPanel
          question={promoting ? `Make ${name} an admin?` : `Make ${name} faculty?`}
          detail={
            promoting
              ? "Admins hold every grant, so their current grants are cleared. It applies from their next click."
              : "They lose their admin rights and start with no grants. It applies from their next click."
          }
          confirmLabel={promoting ? "Make admin" : "Make faculty"}
          busy={busy}
          onConfirm={onChangeRole}
          onCancel={onClose}
        />
      )}
      {panel === "remove" && (
        <ConfirmPanel
          question={`Remove ${name}?`}
          detail="Their access ends at once and any unused link stops working. Their work and history stay with the coaching."
          confirmLabel="Remove"
          busy={busy}
          onConfirm={onRemove}
          onCancel={onClose}
        />
      )}
      {panel === "transfer" && (
        <ConfirmPanel
          question={`Hand the coaching to ${name}?`}
          detail="They become the Owner and you become an admin. Only the new Owner can undo this."
          confirmLabel="Make owner"
          busy={busy}
          onConfirm={onTransfer}
          onCancel={onClose}
        />
      )}
      {error && (
        <p role="alert" className={`mt-3 ${ALERT}`}>
          {error}
        </p>
      )}
    </li>
  );
}
