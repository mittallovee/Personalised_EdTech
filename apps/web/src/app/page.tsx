"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { components, Me } from "@qbank/api-client";

import { AppShell } from "@/components/app-shell";
import { api } from "@/lib/api";

type ReadyStatus = components["schemas"]["ReadyStatus"];

export default function HomePage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [health, setHealth] = useState<ReadyStatus | "unreachable" | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      const who = await api().GET("/api/v1/me");
      if (cancelled) return;
      if (who.response.status === 401 || !who.data) {
        router.replace("/login");
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
    load().catch(() => router.replace("/login"));
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function signOut() {
    await api().POST("/api/v1/auth/logout");
    router.replace("/login");
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
