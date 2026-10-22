"use client";

import { useState, type FormEvent } from "react";

import type { components } from "@qbank/api-client";

import { ConfirmPanel } from "@/components/confirm-panel";

export type Coaching = components["schemas"]["OrganizationOut"];

/** The inline panel open under a coaching. */
export type CoachingPanel = "edit" | "suspend";

const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";

/**
 * One coaching on the platform admin's list: its name, time zone and status, and the things the
 * platform admin does with it. The API refuses anyone who is not a platform admin (403).
 */
export function CoachingCard({
  coaching,
  panel,
  busy,
  error,
  onOpen,
  onClose,
  onSave,
  onSuspend,
  onReactivate,
  onActIn,
}: {
  coaching: Coaching;
  panel: CoachingPanel | null;
  busy: boolean;
  error: string | null;
  onOpen: (panel: CoachingPanel) => void;
  onClose: () => void;
  onSave: (changes: { display_name: string; timezone: string }) => void;
  onSuspend: () => void;
  onReactivate: () => void;
  onActIn: () => void;
}) {
  const [formKey, setFormKey] = useState(0); // a fresh form each time the editor is opened
  const suspended = coaching.status === "SUSPENDED";

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onSave({
      display_name: String(form.get("display_name")),
      timezone: String(form.get("timezone")),
    });
  }

  return (
    <li className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <span className="font-medium">{coaching.display_name}</span>
          <span className="ml-2 text-sm text-zinc-500">{coaching.timezone}</span>
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-xs ${
            suspended
              ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200"
              : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
          }`}
        >
          {suspended ? "Suspended" : "Active"}
        </span>
      </div>
      <p className="mt-1 text-xs text-zinc-500">
        Created {new Date(coaching.created_at).toLocaleDateString()}
      </p>

      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" className={BUTTON} disabled={busy} onClick={onActIn}>
          Act in
        </button>
        <button
          type="button"
          className={BUTTON}
          onClick={() => {
            setFormKey((n) => n + 1);
            onOpen("edit");
          }}
        >
          Rename or change time zone
        </button>
        {suspended ? (
          <button type="button" className={BUTTON} disabled={busy} onClick={onReactivate}>
            Reactivate
          </button>
        ) : (
          <button type="button" className={BUTTON} onClick={() => onOpen("suspend")}>
            Suspend
          </button>
        )}
      </div>

      {panel === "edit" && (
        <form
          key={formKey}
          onSubmit={save}
          aria-label={`Edit ${coaching.display_name}`}
          className="mt-3 space-y-3 rounded-md border border-zinc-200 p-3 dark:border-zinc-800"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block space-y-1 text-sm font-medium">
              <span>Name</span>
              <input
                name="display_name"
                defaultValue={coaching.display_name}
                required
                maxLength={200}
                className={FIELD}
              />
            </label>
            <label className="block space-y-1 text-sm font-medium">
              <span>Time zone</span>
              <input
                name="timezone"
                defaultValue={coaching.timezone}
                required
                maxLength={64}
                className={FIELD}
              />
            </label>
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {busy ? "Saving…" : "Save"}
            </button>
            <button type="button" className={BUTTON} onClick={onClose}>
              Cancel
            </button>
          </div>
        </form>
      )}
      {panel === "suspend" && (
        <ConfirmPanel
          question={`Suspend ${coaching.display_name}?`}
          detail="Everyone in it is signed out and cannot sign in until you reactivate it. Nothing is deleted."
          confirmLabel="Suspend"
          busy={busy}
          onConfirm={onSuspend}
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
