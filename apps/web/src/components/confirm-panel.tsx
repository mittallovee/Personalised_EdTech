"use client";

/**
 * A question under a person's name before something that is hard to undo: what will happen, and
 * a button to go ahead. Nothing is sent until the person presses it.
 */
export function ConfirmPanel({
  question,
  detail,
  confirmLabel,
  busy,
  onConfirm,
  onCancel,
}: {
  question: string;
  detail: string;
  confirmLabel: string;
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <section
      aria-label={question}
      className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm dark:border-amber-800 dark:bg-amber-950"
    >
      <p className="font-medium">{question}</p>
      <p className="mt-1 text-zinc-700 dark:text-zinc-300">{detail}</p>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={onConfirm}
          className="rounded-md bg-zinc-900 px-3 py-1 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {busy ? "Working…" : confirmLabel}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-zinc-300 px-3 py-1 dark:border-zinc-700"
        >
          Cancel
        </button>
      </div>
    </section>
  );
}
