"use client";

import type { components } from "@qbank/api-client";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { formatInr } from "@/lib/ai-admin";
import { budgetText, percentUsed, type Usage } from "@/lib/ai-run";
import { api, errorMessage } from "@/lib/api";
import { NETWORK } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Everyone = components["schemas"]["UsageListOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";

/** A budget as a bar and a sentence. The server decides what a run may cost; this only shows it. */
function Bar({ usage }: { usage: Usage }) {
  const percent = percentUsed(usage.spent_inr, usage.limit_inr);
  return (
    <div className="grid gap-1">
      {percent !== null && (
        <div
          role="progressbar"
          aria-label="Budget used"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={percent}
          className="h-2 w-full max-w-md rounded bg-zinc-200 dark:bg-zinc-800"
        >
          <div
            className={`h-2 rounded ${usage.state === "REACHED" ? "bg-red-600" : usage.state === "WARNING" ? "bg-amber-500" : "bg-emerald-600"}`}
            style={{ width: `${percent}%` }}
          />
        </div>
      )}
      <p className="text-sm">{budgetText(usage)}</p>
    </div>
  );
}

/**
 * AI usage for this month (H-05): what you have spent against your budget, and, for the Owner and
 * admins, what everyone has. The rupee amounts are the server's exact figures, shown as text.
 */
export default function UsagePage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const [mine, setMine] = useState<Usage | null>(null);
  const [everyone, setEveryone] = useState<Everyone | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const signedIn = me !== null;
  // The people list is for the Owner and admins (the API refuses everyone else); ask only them.
  const sees =
    me !== null &&
    (me.organization?.role === "OWNER" ||
      me.organization?.role === "ADMIN" ||
      me.acting_organization_id !== null);

  useEffect(() => {
    if (!signedIn) return;
    let cancelled = false;
    async function load() {
      try {
        const [own, all] = await Promise.all([
          api().GET("/api/v1/ai/usage/me"),
          sees ? api().GET("/api/v1/ai/usage") : Promise.resolve(null),
        ]);
        if (cancelled) return;
        if (own.data) setMine(own.data);
        else setProblem(errorMessage(own.error as never, own.response.status));
        setEveryone(all?.data ?? null);
      } catch {
        if (!cancelled) setProblem(NETWORK);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [signedIn, sees]);

  if (loadError) {
    return (
      <main className="p-8">
        <p role="alert" className={ALERT}>
          {loadError}
        </p>
        <button type="button" onClick={retry} className="mt-4 underline">
          Try again
        </button>
      </main>
    );
  }
  if (!me) return <main className="p-8">Loading…</main>;

  return (
    <AppShell me={me} current="usage" onSignOut={signOut} onStopActing={stopActing}>
      {shellError && (
        <p role="alert" className={`mb-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <div className="grid max-w-3xl gap-6">
        <h1 className="text-2xl font-semibold">AI usage</h1>
        {problem && (
          <p role="alert" className={ALERT}>
            {problem}
          </p>
        )}
        {mine && (
          <section aria-label="Your usage" className="grid gap-2">
            <h2 className="text-lg font-semibold">You, {mine.period}</h2>
            <Bar usage={mine} />
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Runs still going count at their estimate until they finish.
            </p>
          </section>
        )}
        {everyone && (
          <section aria-label="Everyone's usage" className="grid gap-2">
            <h2 className="text-lg font-semibold">Everyone, {everyone.period}</h2>
            {everyone.data.length === 0 ? (
              <p className="text-sm">Nobody has used AI this month.</p>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 dark:border-zinc-800">
                    <th className="py-2 pr-4 font-medium">Person</th>
                    <th className="py-2 pr-4 font-medium">Spent</th>
                    <th className="py-2 pr-4 font-medium">Budget</th>
                    <th className="py-2 font-medium">State</th>
                  </tr>
                </thead>
                <tbody>
                  {everyone.data.map((person) => (
                    <tr
                      key={person.user_id}
                      className="border-b border-zinc-100 dark:border-zinc-900"
                    >
                      <td className="py-2 pr-4">{person.display_name ?? "A former member"}</td>
                      <td className="py-2 pr-4">{formatInr(person.spent_inr)}</td>
                      <td className="py-2 pr-4">{formatInr(person.limit_inr)}</td>
                      <td className="py-2">{STATE[person.state]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        )}
      </div>
    </AppShell>
  );
}

const STATE: Record<Usage["state"], string> = {
  NO_LIMIT: "No limit",
  OK: "Within budget",
  WARNING: "Close to the limit",
  REACHED: "Limit reached",
  OFF: "Needs a rate (ask an admin)",
};
