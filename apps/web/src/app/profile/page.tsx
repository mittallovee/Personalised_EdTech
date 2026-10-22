"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import type { components } from "@qbank/api-client";

import { AppShell } from "@/components/app-shell";
import { ConfirmPanel } from "@/components/confirm-panel";
import { StatusNotice } from "@/components/status-notice";
import { api, errorMessage } from "@/lib/api";
import { goToGoogle, useAuthMethods, useGoogleResult } from "@/lib/google";
import { useMe } from "@/lib/use-me";

type LoginMethods = components["schemas"]["LoginMethods"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
const NETWORK = "Cannot reach the server. Check your connection and try again.";

/**
 * The signed-in person's own account: how they sign in. A Google account is linked here by typing
 * the password again (the API insists on it), and can be unlinked while a password remains.
 */
export default function ProfilePage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const server = useAuthMethods();
  const googleResult = useGoogleResult();
  const [methods, setMethods] = useState<LoginMethods | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmingUnlink, setConfirmingUnlink] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api().GET("/api/v1/me/login-methods");
      if (data) {
        setMethods(data);
        setLoadFailed(false);
        return;
      }
    } catch {
      // fall through
    }
    setLoadFailed(true);
  }, []);

  useEffect(() => {
    // `load` sets state only after the network call returns, never during this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  async function link(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const password = String(new FormData(event.currentTarget).get("password"));
    setBusy(true);
    setError(null);
    setNotice(null);
    const message = await goToGoogle(() =>
      api().POST("/api/v1/auth/google/start-link", {
        body: { return_origin: window.location.origin, password },
      }),
    );
    if (message) {
      setError(message);
      setBusy(false);
    }
  }

  async function unlink() {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const { error: failure, response } = await api().POST("/api/v1/auth/google/unlink");
      if (response.ok) {
        setConfirmingUnlink(false);
        setNotice("Your Google account is unlinked. You sign in with your password.");
        // The unlink went through, so show that now; the reload below only confirms it, and a
        // failed reload must not bring the old "linked" state back.
        setMethods((current) => current && { ...current, google: { linked: false, email: null } });
        await load();
      } else {
        setConfirmingUnlink(false);
        setError(errorMessage(failure, response.status));
      }
    } catch {
      setError(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  if (loadError) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-4">
        <p role="alert" className={ALERT}>
          {loadError} Please try again.
        </p>
        <button type="button" onClick={retry} className={BUTTON}>
          Try again
        </button>
      </main>
    );
  }
  if (!me) return <p className="p-8 text-sm text-zinc-500">Loading…</p>;

  return (
    <AppShell me={me} current="profile" onSignOut={signOut} onStopActing={stopActing}>
      {shellError && (
        <p role="alert" className={`mb-6 max-w-md ${ALERT}`}>
          {shellError}
        </p>
      )}
      <h1 className="text-2xl font-semibold">Profile</h1>
      <p className="mt-1 mb-6 text-zinc-600 dark:text-zinc-400">
        {me.display_name}
        {me.organization ? `, in ${me.organization.display_name}` : ""}
      </p>

      {googleResult === "linked" && <StatusNotice>Your Google account is linked.</StatusNotice>}
      {googleResult === "failed" && (
        <p role="alert" className={`mb-6 max-w-2xl ${ALERT}`}>
          We could not link your Google account. Nothing was changed. Try again, and if it keeps
          failing, check that this Google account is not already linked to someone else.
        </p>
      )}
      {notice && <StatusNotice>{notice}</StatusNotice>}

      <h2 className="mb-3 font-medium">How you sign in</h2>
      {loadFailed && (
        <div className="max-w-md space-y-3">
          <p role="alert" className={ALERT}>
            Could not load your sign-in methods.
          </p>
          <button type="button" className={BUTTON} onClick={() => void load()}>
            Try again
          </button>
        </div>
      )}
      {!methods && !loadFailed && <p className="text-sm text-zinc-500">Loading…</p>}

      {methods && (
        <ul aria-label="Sign-in methods" className="max-w-2xl space-y-3">
          <li className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
            <span className="font-medium">Password</span>
            <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
              {methods.password
                ? "Set. Ask your coaching admin for a reset link if you forget it."
                : "Not set. You sign in with Google."}
            </p>
          </li>
          <li className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
            <span className="font-medium">Google</span>
            {methods.google.linked ? (
              <>
                <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                  Linked
                  {methods.google.email ? ` (${methods.google.email} when it was linked)` : ""}.
                </p>
                {methods.password ? (
                  confirmingUnlink ? (
                    <ConfirmPanel
                      question="Unlink your Google account?"
                      detail="You will sign in with your password. You can link a Google account again later."
                      confirmLabel="Unlink Google"
                      busy={busy}
                      onConfirm={() => void unlink()}
                      onCancel={() => setConfirmingUnlink(false)}
                    />
                  ) : (
                    <button
                      type="button"
                      className={`mt-3 ${BUTTON}`}
                      onClick={() => setConfirmingUnlink(true)}
                    >
                      Unlink Google
                    </button>
                  )
                ) : (
                  <p className="mt-2 text-xs text-zinc-500">
                    Google is your only way in, so it cannot be unlinked. Ask your coaching admin
                    for a password-reset link if you want a password too.
                  </p>
                )}
              </>
            ) : server.status === "loading" ? (
              <p className="mt-1 text-sm text-zinc-500">Checking whether Google is available…</p>
            ) : server.status === "failed" ? (
              <div className="mt-1 space-y-2">
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                  Could not check whether Google sign-in is available.
                </p>
                <button type="button" className={BUTTON} onClick={server.retry}>
                  Try again
                </button>
              </div>
            ) : !server.google ? (
              <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                Signing in with Google is not set up on this server.
              </p>
            ) : methods.password ? (
              <form onSubmit={link} aria-label="Link a Google account" className="mt-2 space-y-3">
                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                  Not linked. To link a Google account, type your password, then choose the account
                  at Google.
                </p>
                <label className="block max-w-xs space-y-1 text-sm font-medium">
                  <span>Your password</span>
                  <input
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    className={FIELD}
                  />
                </label>
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
                >
                  {busy ? "Going to Google…" : "Link Google account"}
                </button>
              </form>
            ) : null}
            {error && (
              <p role="alert" className={`mt-3 ${ALERT}`}>
                {error}
              </p>
            )}
          </li>
        </ul>
      )}
    </AppShell>
  );
}
