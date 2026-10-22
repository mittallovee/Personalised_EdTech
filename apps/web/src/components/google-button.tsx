"use client";

const BUTTON =
  "w-full rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium hover:bg-zinc-50 disabled:opacity-60 dark:border-zinc-700 dark:hover:bg-zinc-800";

/** "Sign in with Google" and its relatives. The page decides when to show it and what it does. */
export function GoogleButton({
  label,
  busy,
  disabled = false,
  onClick,
}: {
  label: string;
  /** This button's own request is under way. */
  busy: boolean;
  /** Another request on the page is under way, so nothing else may be started. */
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button type="button" className={BUTTON} disabled={busy || disabled} onClick={onClick}>
      {busy ? "Going to Google…" : label}
    </button>
  );
}

/** A thin "or" between the password form and the Google button. */
export function OrDivider() {
  return (
    <div className="flex items-center gap-3 text-xs text-zinc-500" aria-hidden="true">
      <span className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
      or
      <span className="h-px flex-1 bg-zinc-200 dark:bg-zinc-800" />
    </div>
  );
}
