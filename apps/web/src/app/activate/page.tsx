"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { GoogleButton, OrDivider } from "@/components/google-button";
import { api, errorMessage } from "@/lib/api";
import { goToGoogle, useAuthMethods } from "@/lib/google";

const MIN_LENGTH = 12; // the API enforces it too; this only saves a round trip

const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";

/**
 * Activation and password-reset links look like `/activate#<token>` (ADR-0015). The part after
 * `#` is never sent to a server by the browser; we read it here, remove it from the address bar
 * and history, and send it to the API only in the request body.
 */
export default function ActivatePage() {
  const router = useRouter();
  const [token, setToken] = useState<string | null | undefined>(undefined); // undefined = reading
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [googleBusy, setGoogleBusy] = useState(false);
  const methods = useAuthMethods();

  useEffect(() => {
    const fromLink = window.location.hash.slice(1);
    window.history.replaceState(null, "", window.location.pathname);
    // Reading the address bar is only possible in the browser, after the first render.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setToken(fromLink || null);
  }, []);

  async function continueWithGoogle() {
    if (!token) return;
    setGoogleBusy(true);
    setError(null);
    const message = await goToGoogle(() =>
      api().POST("/api/v1/auth/google/start-activation", {
        body: { return_origin: window.location.origin, link_token: token },
      }),
    );
    if (message) {
      setError(message);
      setGoogleBusy(false);
    }
  }

  async function activate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password"));
    if (password.length < MIN_LENGTH) {
      setError(`Use at least ${MIN_LENGTH} characters.`);
      return;
    }
    if (password !== String(form.get("repeat"))) {
      setError("The two passwords are different.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const { error, response } = await api().POST("/api/v1/auth/links/redeem", {
        body: { token, password },
      });
      if (response.ok) {
        router.replace("/");
        return;
      }
      setError(errorMessage(error, response.status));
    } catch {
      setError("Cannot reach the server. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-4 dark:bg-zinc-950">
      <div className="w-full max-w-sm space-y-5 rounded-xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
        <div>
          <h1 className="text-xl font-semibold">Set your password</h1>
          <p className="text-sm text-zinc-500">
            Choose a password to finish setting up your account.
          </p>
        </div>
        {token === null ? (
          <p role="alert" className="text-sm text-zinc-600 dark:text-zinc-400">
            This page needs the full link your coaching admin sent you. Open that link again, or ask
            for a new one.
          </p>
        ) : (
          <form onSubmit={activate} className="space-y-5">
            <label className="block space-y-1 text-sm font-medium">
              <span>New password</span>
              <input
                name="password"
                type="password"
                autoComplete="new-password"
                required
                className={FIELD}
              />
              <span className="block text-xs font-normal text-zinc-500">
                At least {MIN_LENGTH} characters.
              </span>
            </label>
            <label className="block space-y-1 text-sm font-medium">
              <span>Repeat the password</span>
              <input
                name="repeat"
                type="password"
                autoComplete="new-password"
                required
                className={FIELD}
              />
            </label>
            {error && (
              <p
                role="alert"
                className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
              >
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={busy || !token}
              className="w-full rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {busy ? "Saving…" : "Save and sign in"}
            </button>
            {methods.google && (
              <>
                <OrDivider />
                <GoogleButton
                  label="Continue with Google instead"
                  busy={googleBusy}
                  onClick={() => void continueWithGoogle()}
                />
              </>
            )}
          </form>
        )}
      </div>
    </main>
  );
}
