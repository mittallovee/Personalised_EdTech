"use client";

import { AppShell } from "@/components/app-shell";
import { EveryonesUsage, MyUsage } from "@/components/usage-section";
import { canManageCatalogues } from "@/lib/syllabus";
import { useMe } from "@/lib/use-me";

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";

/**
 * AI usage (H-05, H-06): what you have used this month against your budget and, for the Owner and
 * admins, what everyone has used and each person's own budget. The API computes every figure; this
 * page only shows them, and the API decides who may see whose.
 */
export default function UsagePage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();

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
      <h1 className="text-2xl font-semibold">AI usage</h1>
      <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        What the AI has cost this month, in rupees at the rate your admin set. A run that would pass
        your monthly budget is refused before anything is sent.
      </p>
      {shellError && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <div className="mt-6 grid max-w-3xl gap-10">
        <MyUsage />
        {canManageCatalogues(me) && <EveryonesUsage />}
      </div>
    </AppShell>
  );
}
