"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { components, Me } from "@qbank/api-client";

import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";

type ReadyStatus = components["schemas"]["ReadyStatus"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";

export default function HomePage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [health, setHealth] = useState<ReadyStatus | "unreachable" | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [signOutError, setSignOutError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      let who;
      try {
        who = await api().GET("/api/v1/me");
      } catch {
        if (!cancelled) setLoadError("Cannot reach the server. Check your connection.");
        return;
      }
      if (cancelled) return;
      // Only "not signed in" leads to the sign-in page; any other failure is an outage to report.
      if (who.response.status === 401) {
        router.replace("/login");
        return;
      }
      if (!who.data) {
        setLoadError("The server could not load your account right now.");
        return;
      }
      setMe(who.data);
      try {
        const ready = await api().GET("/health/ready");
        // 200 and 503 both describe the health; anything else (e.g. a 500) means unreachable.
        const status = ready.data ?? (ready.error && "status" in ready.error ? ready.error : null);
        if (!cancelled) setHealth(status ?? "unreachable");
      } catch {
        if (!cancelled) setHealth("unreachable");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [router, attempt]);

  function retry() {
    setLoadError(null);
    setAttempt((n) => n + 1);
  }

  async function signOut() {
    setSignOutError(null);
    try {
      const { response } = await api().POST("/api/v1/auth/logout");
      // 401: the session had already ended (expired or revoked), so the user is signed out anyway.
      if (response.ok || response.status === 401) {
        router.replace("/login");
        return;
      }
    } catch {
      // network failure: fall through
    }
    // Never show the signed-out screen while the server session may still be valid.
    setSignOutError("Could not sign out. You are still signed in; please try again.");
  }

  if (loadError) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-4">
        <p role="alert" className={ALERT}>
          {loadError} Please try again.
        </p>
        <button
          type="button"
          onClick={retry}
          className="rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700"
        >
          Try again
        </button>
      </main>
    );
  }

  if (!me) {
    return <p className="p-8 text-sm text-zinc-500">Loading…</p>;
  }

  const role = me.is_platform_admin
    ? "Platform admin"
    : me.organization
      ? `${me.organization.role.toLowerCase()} in your coaching`
      : "No coaching yet";

  return (
    <AppShell me={me} onSignOut={signOut}>
      {signOutError && (
        <p role="alert" className={`mb-6 max-w-md ${ALERT}`}>
          {signOutError}
        </p>
      )}
      <h1 className="text-2xl font-semibold">Welcome, {me.display_name}</h1>
      <p className="mt-1 text-zinc-600 dark:text-zinc-400">Signed in as {role}.</p>

      <section className="mt-8 max-w-md rounded-lg border border-zinc-200 p-5 dark:border-zinc-800">
        <h2 className="font-medium">System health</h2>
        <dl className="mt-3 grid grid-cols-2 gap-y-1 text-sm">
          <dt className="text-zinc-500">API</dt>
          <dd>
            {health === null
              ? "Checking…"
              : health === "unreachable"
                ? "Unreachable"
                : health.status}
          </dd>
          {health && health !== "unreachable" && (
            <>
              <dt className="text-zinc-500">Database</dt>
              <dd>{health.database}</dd>
              <dt className="text-zinc-500">Migrations</dt>
              <dd>{health.migrations}</dd>
            </>
          )}
        </dl>
      </section>
    </AppShell>
  );
}
