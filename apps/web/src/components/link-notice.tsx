"use client";

import { useState } from "react";

export interface IssuedLink {
  /** Whose link: shown in the heading. */
  who: string;
  kind: "activation" | "reset";
  token: string;
  expiresAt: string;
}

const KIND = {
  activation: "Activation link",
  reset: "Password-reset link",
} as const;

/**
 * A one-time link, shown once. The secret is in the part after `#`, which a browser never sends
 * to a server; an admin copies it and shares it themselves (the app sends no email, B-05).
 */
export function LinkNotice({ link, onDismiss }: { link: IssuedLink; onDismiss: () => void }) {
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const url = `${window.location.origin}/activate#${link.token}`;

  async function copy() {
    setCopyFailed(false);
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      // Clipboard access can be refused (e.g. plain http on another address): select it instead.
      setCopied(false);
      setCopyFailed(true);
    }
  }

  return (
    <section
      role="status"
      aria-label={`${KIND[link.kind]} for ${link.who}`}
      className="mb-6 rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm dark:border-emerald-800 dark:bg-emerald-950"
    >
      <h2 className="font-medium">
        {KIND[link.kind]} for {link.who}
      </h2>
      <p className="mt-1 text-zinc-600 dark:text-zinc-400">
        Send them this link yourself. It works once, until{" "}
        {new Date(link.expiresAt).toLocaleString()}, and it is shown only now.
      </p>
      <div className="mt-3 flex gap-2">
        <input
          readOnly
          aria-label="Link"
          value={url}
          onFocus={(event) => event.currentTarget.select()}
          className="min-w-0 flex-1 rounded-md border border-zinc-300 bg-white px-3 py-2 font-mono text-xs dark:border-zinc-700 dark:bg-zinc-950"
        />
        <button
          type="button"
          onClick={() => void copy()}
          className="rounded-md bg-zinc-900 px-3 py-2 text-white dark:bg-zinc-100 dark:text-zinc-900"
        >
          {copied ? "Copied" : "Copy"}
        </button>
        <button
          type="button"
          onClick={onDismiss}
          className="rounded-md border border-zinc-300 px-3 py-2 dark:border-zinc-700"
        >
          Done
        </button>
      </div>
      {copyFailed && (
        <p className="mt-2 text-zinc-600 dark:text-zinc-400">
          Could not copy automatically. Select the link above and copy it.
        </p>
      )}
    </section>
  );
}
