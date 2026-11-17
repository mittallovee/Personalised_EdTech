"use client";

import { useState } from "react";

import { NOTE_MAX, NOTE_MIN, RETURN_REASONS, returnReady, type ReturnReason } from "@/lib/workflow";

/**
 * Sending a question back to its author (E-06): one or more of the fixed reasons, and a note
 * saying what to fix. The note is plain text; the author reads it as written.
 */
export function ReturnForm({
  busy,
  onSend,
  onCancel,
}: {
  busy: boolean;
  onSend: (reasons: ReturnReason[], note: string) => void;
  onCancel: () => void;
}) {
  const [reasons, setReasons] = useState<ReturnReason[]>([]);
  const [note, setNote] = useState("");
  const ready = returnReady(reasons, note);

  function toggle(code: ReturnReason, on: boolean) {
    setReasons((now) => (on ? [...now, code] : now.filter((r) => r !== code)));
  }

  return (
    <form
      aria-label="Return to the author"
      className="grid gap-3 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-800 dark:bg-amber-950"
      onSubmit={(event) => {
        event.preventDefault();
        if (ready && !busy) onSend(reasons, note.trim());
      }}
    >
      <fieldset className="grid gap-1">
        <legend className="font-medium">Why is it going back?</legend>
        {RETURN_REASONS.map(({ code, label }) => (
          <label key={code} className="flex items-start gap-2">
            <input
              type="checkbox"
              className="mt-1"
              checked={reasons.includes(code)}
              onChange={(event) => toggle(code, event.target.checked)}
            />
            {label}
          </label>
        ))}
      </fieldset>
      <label className="grid gap-1">
        <span className="font-medium">What should the author fix?</span>
        <textarea
          rows={3}
          maxLength={NOTE_MAX}
          value={note}
          onChange={(event) => setNote(event.target.value)}
          className="rounded-md border border-zinc-300 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
        />
        <span className="text-xs text-zinc-600 dark:text-zinc-400">
          At least {NOTE_MIN} characters. Choose at least one reason.
        </span>
      </label>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={!ready || busy}
          className="rounded-md bg-zinc-900 px-3 py-1 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {busy ? "Working…" : "Return to the author"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-zinc-300 px-3 py-1 dark:border-zinc-700"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
