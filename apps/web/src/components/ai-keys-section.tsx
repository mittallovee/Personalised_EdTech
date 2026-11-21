"use client";

import type { components } from "@qbank/api-client";
import { useEffect, useState } from "react";

import { api, errorMessage } from "@/lib/api";
import { PROVIDERS, PROVIDER_LABEL, type Provider } from "@/lib/ai-admin";
import { NETWORK } from "@/lib/use-catalogue";

type Keys = components["schemas"]["KeysOut"];
type KeyStatus = components["schemas"]["ProviderKeyOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const OK =
  "rounded-md bg-green-50 px-3 py-2 text-sm text-green-800 dark:bg-green-950 dark:text-green-200";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/**
 * The coaching's own API keys for the AI providers (H-02). A key is write-only: it is typed here,
 * sent once and sealed on the server. Only its last four characters are ever shown again, so the
 * box is emptied as soon as it is saved. `onChanged` tells the models section to look again.
 */
export function AiKeysSection({ onChanged }: { onChanged: () => void }) {
  const [keys, setKeys] = useState<Keys | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const { data, error, response } = await api().GET("/api/v1/ai/keys");
        if (cancelled) return;
        if (data) {
          setKeys(data);
          setProblem(null);
        } else {
          setProblem(
            response.status === 403
              ? "Only the Owner and admins may see or change the keys."
              : errorMessage(error as never, response.status),
          );
        }
      } catch {
        if (!cancelled) setProblem(NETWORK);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  return (
    <section aria-label="Provider keys" className="grid gap-3">
      <div>
        <h2 className="text-lg font-medium">Provider keys</h2>
        <p className="max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          Your coaching pays its AI provider directly, with its own key. A key is stored sealed on
          the server and can never be read back: paste it here only, never in a message or a file.
          Replacing a key replaces it for every run from then on.
        </p>
      </div>
      {problem && (
        <p role="alert" className={ALERT}>
          {problem}
        </p>
      )}
      {keys && !keys.encryption_ready && (
        <p role="alert" className={ALERT}>
          This server has no master encryption key yet, so keys cannot be stored. Ask whoever runs
          the server to set <code>AI_KEYS_MASTER_KEY</code> first.
        </p>
      )}
      {!keys && !problem && <p>Loading…</p>}
      {keys && (
        <ul className="grid gap-3">
          {PROVIDERS.map((provider) => (
            <KeyRow
              key={provider}
              provider={provider}
              status={keys.data.find((item) => item.provider === provider)}
              canStore={keys.encryption_ready}
              onChanged={() => {
                setAttempt((n) => n + 1);
                onChanged();
              }}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function KeyRow({
  provider,
  status,
  canStore,
  onChanged,
}: {
  provider: Provider;
  status: KeyStatus | undefined;
  canStore: boolean;
  onChanged: () => void;
}) {
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const label = PROVIDER_LABEL[provider];

  async function save() {
    if (busy || typed.trim() === "") return;
    setBusy(true);
    setMessage(null);
    try {
      const { data, error, response } = await api().PUT("/api/v1/ai/keys/{provider}", {
        params: { path: { provider } },
        body: { key: typed },
      });
      if (data) {
        setTyped(""); // the key is never kept on screen once it is sealed
        setMessage({ ok: true, text: `The ${label} key is saved.` });
        onChanged();
      } else {
        setMessage({ ok: false, text: errorMessage(error as never, response.status) });
      }
    } catch {
      setMessage({ ok: false, text: NETWORK });
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const { error, response } = await api().DELETE("/api/v1/ai/keys/{provider}", {
        params: { path: { provider } },
      });
      if (response.ok) {
        setConfirming(false);
        setMessage({ ok: true, text: `The ${label} key is removed.` });
        onChanged();
      } else {
        setMessage({ ok: false, text: errorMessage(error as never, response.status) });
      }
    } catch {
      setMessage({ ok: false, text: NETWORK });
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="grid gap-2 rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium">{label}</h3>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          {status?.configured ? `Stored, ending ${status.last4 ?? "…"}` : "No key stored"}
        </p>
      </div>
      <form
        aria-label={`${label} key`}
        className="flex flex-wrap items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <label className="grid min-w-64 flex-1 gap-1 text-sm">
          {status?.configured ? "Replace the key" : "Key"}
          <input
            type="password"
            autoComplete="off"
            spellCheck={false}
            value={typed}
            onChange={(event) => setTyped(event.target.value)}
            disabled={busy || !canStore}
            className={FIELD}
          />
        </label>
        <button
          type="submit"
          disabled={busy || !canStore || typed.trim() === ""}
          className={PRIMARY}
        >
          Save key
        </button>
        {status?.configured &&
          (confirming ? (
            <>
              <button
                type="button"
                disabled={busy}
                onClick={() => void remove()}
                className={BUTTON}
              >
                Yes, remove it
              </button>
              <button type="button" onClick={() => setConfirming(false)} className={BUTTON}>
                Keep it
              </button>
            </>
          ) : (
            <button type="button" onClick={() => setConfirming(true)} className={BUTTON}>
              Remove
            </button>
          ))}
      </form>
      {message && (
        <p role={message.ok ? "status" : "alert"} className={message.ok ? OK : ALERT}>
          {message.text}
        </p>
      )}
    </li>
  );
}
