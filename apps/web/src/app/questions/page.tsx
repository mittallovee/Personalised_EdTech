"use client";

import type { components } from "@qbank/api-client";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AppShell } from "@/components/app-shell";
import { BankList } from "@/components/bank-list";
import { api } from "@/lib/api";
import { FORMATS, emptyContent } from "@/lib/question-content";
import { useAdd } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/**
 * Questions (D-11, F-01 to F-03): start a new one, and the bank of every question you may open,
 * with filters, a count, a search and a code box. Every question gets its permanent code when it
 * is started. The API decides who sees what: your own drafts and every submitted question, or all
 * drafts too for admins and people who may edit others' drafts.
 */
export default function QuestionsPage() {
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
    <AppShell me={me} current="questions" onSignOut={signOut} onStopActing={stopActing}>
      <h1 className="text-2xl font-semibold">Questions</h1>
      {shellError && (
        <p role="alert" className={`mt-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <div className="mt-6 grid max-w-5xl gap-10">
        <NewQuestion />
        <BankList myId={me.id} />
      </div>
    </AppShell>
  );
}

function NewQuestion() {
  const router = useRouter();
  const [type, setType] = useState("SCQ");
  const adder = useAdd<components["schemas"]["QuestionOut"]>(
    (body, key) =>
      api().POST("/api/v1/questions", {
        body: body as components["schemas"]["CreateQuestion"],
        params: { header: { "Idempotency-Key": key } },
      }),
    (created) => router.push(`/questions/${created.id}`),
  );

  return (
    <form
      aria-label="Start a question"
      className="grid gap-3"
      onSubmit={(event) => {
        event.preventDefault();
        void adder.add({ content: emptyContent(type) });
      }}
    >
      <fieldset className="grid gap-2">
        <legend className="mb-1 text-lg font-medium">Start a new question</legend>
        {FORMATS.map((format) => (
          <label key={format.value} className="flex items-start gap-2 text-sm">
            <input
              type="radio"
              name="format"
              value={format.value}
              checked={type === format.value}
              onChange={() => setType(format.value)}
              className="mt-1"
            />
            <span>
              <span className="font-medium">{format.label}</span>
              <span className="block text-zinc-600 dark:text-zinc-400">{format.hint}</span>
            </span>
          </label>
        ))}
      </fieldset>
      {adder.addError && (
        <p role="alert" className={ALERT}>
          {adder.addError}
        </p>
      )}
      <div>
        <button type="submit" disabled={adder.adding} className={PRIMARY}>
          {adder.adding ? "Starting…" : "Start question"}
        </button>
      </div>
    </form>
  );
}
