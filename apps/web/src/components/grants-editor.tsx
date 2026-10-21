"use client";

import { useState } from "react";

import { GRANTS } from "@/lib/grants";

/** Tick the grants a faculty member should have; "Save" sends the whole set. */
export function GrantsEditor({
  name,
  current,
  busy,
  onSave,
  onCancel,
}: {
  name: string;
  current: string[];
  busy: boolean;
  onSave: (grants: string[]) => void;
  onCancel: () => void;
}) {
  const [chosen, setChosen] = useState(() => new Set(current));

  function toggle(grant: string) {
    const next = new Set(chosen);
    if (!next.delete(grant)) next.add(grant);
    setChosen(next);
  }

  return (
    <fieldset className="mt-3 rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
      <legend className="px-1 text-sm font-medium">Grants for {name}</legend>
      <ul className="space-y-1 text-sm">
        {GRANTS.map((grant) => (
          <li key={grant.name}>
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={chosen.has(grant.name)}
                onChange={() => toggle(grant.name)}
                className="mt-1"
              />
              <span>
                {grant.label}
                <span className="block text-xs text-zinc-500">{grant.help}</span>
              </span>
            </label>
          </li>
        ))}
      </ul>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => onSave(GRANTS.map((g) => g.name).filter((n) => chosen.has(n)))}
          className="rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {busy ? "Saving…" : "Save grants"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700"
        >
          Cancel
        </button>
      </div>
    </fieldset>
  );
}
