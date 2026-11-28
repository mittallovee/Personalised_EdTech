"use client";

import { useState } from "react";

import { AiKeysSection } from "@/components/ai-keys-section";
import { AiModelsSection } from "@/components/ai-models-section";
import { AiSettingsSection } from "@/components/ai-settings-section";
import { AppShell } from "@/components/app-shell";
import { canManageCatalogues } from "@/lib/syllabus";
import { useMe } from "@/lib/use-me";

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";

/**
 * Admin, AI (M5): the coaching's provider keys, the models faculty may use, the rupee rate and
 * monthly budget, and which model each operation uses. The API decides who may do any of this
 * and what is valid; this page only asks and reports.
 */
export default function AiAdminPage() {
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  // Bumped when a key is saved or removed, so the lists of models are read again.
  const [version, setVersion] = useState(0);

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
    <AppShell me={me} current="ai" onSignOut={signOut} onStopActing={stopActing}>
      <h1 className="text-2xl font-semibold">AI</h1>
      <p className="mt-1 max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
        Set up the AI helpers for your coaching: your provider keys, the models faculty may use, and
        what it may cost. Nothing runs until a key is stored and a model is turned on.
      </p>
      {shellError && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <div className="mt-6 grid max-w-3xl gap-10">
        {canManageCatalogues(me) ? (
          <>
            <AiKeysSection onChanged={() => setVersion((n) => n + 1)} />
            <AiModelsSection version={version} onChanged={() => setVersion((n) => n + 1)} />
            <AiSettingsSection version={version} />
          </>
        ) : (
          <p role="alert" className={ALERT}>
            Only the Owner and admins may set up the AI.
          </p>
        )}
      </div>
    </AppShell>
  );
}
