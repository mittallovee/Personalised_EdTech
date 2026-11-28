"use client";

import type { components } from "@qbank/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { notificationsChanged } from "@/components/notification-bell";
import { api, errorMessage } from "@/lib/api";
import { describe } from "@/lib/review";
import { NETWORK } from "@/lib/use-catalogue";
import { useMe } from "@/lib/use-me";

type Notification = components["schemas"]["NotificationOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";

/** Your notifications (I-01): a question that came back to you, a question of yours published. */
export default function NotificationsPage() {
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
    <AppShell me={me} current="notifications" onSignOut={signOut} onStopActing={stopActing}>
      {shellError && (
        <p role="alert" className={`mb-4 max-w-2xl ${ALERT}`}>
          {shellError}
        </p>
      )}
      <Notifications />
    </AppShell>
  );
}

function Notifications() {
  const router = useRouter();
  const [items, setItems] = useState<Notification[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const ticket = useRef(0); // as on the review page: a late answer to an older load is dropped

  const load = useCallback(async (cursor: string | null) => {
    const mine = ++ticket.current;
    try {
      const result = await api().GET("/api/v1/notifications", {
        params: { query: { limit: 50, ...(cursor ? { cursor } : {}) } },
      });
      if (mine !== ticket.current) return;
      if (!result.data) {
        setProblem(errorMessage(result.error as never, result.response.status));
        return;
      }
      const page = result.data;
      setItems((now) => (cursor ? [...now, ...page.data] : page.data));
      setNext(page.page.next_cursor ?? null);
      setProblem(null);
      setLoaded(true);
    } catch {
      setProblem(NETWORK);
    }
  }, []);

  useEffect(() => {
    // `load` sets state only after the network call returns, never during this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(null);
  }, [load]);

  async function markRead(notification: Notification): Promise<void> {
    if (notification.read_at !== null) return;
    await api().POST("/api/v1/notifications/{notification_id}/read", {
      params: { path: { notification_id: notification.id } },
    });
    notificationsChanged();
  }

  async function open(notification: Notification, target: string) {
    try {
      await markRead(notification);
    } catch {
      // Opening the question matters more than the mark; it stays unread and can be marked later.
    }
    router.push(target);
  }

  async function readAll() {
    setBusy(true);
    setProblem(null);
    try {
      const result = await api().POST("/api/v1/notifications/read-all");
      if (result.response.ok) {
        const now = new Date().toISOString();
        setItems((list) => list.map((n) => (n.read_at === null ? { ...n, read_at: now } : n)));
        notificationsChanged();
      } else {
        setProblem(errorMessage(result.error as never, result.response.status));
      }
    } catch {
      setProblem(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  const unread = items.some((n) => n.read_at === null);
  return (
    <div className="grid max-w-3xl gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Notifications</h1>
        <button type="button" className={BUTTON} disabled={busy || !unread} onClick={readAll}>
          Mark all as read
        </button>
      </div>
      {problem && (
        <p role="alert" className={ALERT}>
          {problem}{" "}
          <button type="button" className="underline" onClick={() => void load(null)}>
            Try again
          </button>
        </p>
      )}
      {loaded && items.length === 0 && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Nothing yet. You are told here when a question of yours comes back or is published.
        </p>
      )}
      <ul className="grid gap-2" aria-label="Your notifications">
        {items.map((notification) => {
          const told = describe(notification);
          const fresh = notification.read_at === null;
          return (
            <li
              key={notification.id}
              className={`rounded-md border p-3 text-sm ${
                fresh
                  ? "border-sky-300 bg-sky-50 dark:border-sky-800 dark:bg-sky-950"
                  : "border-zinc-200 dark:border-zinc-800"
              }`}
            >
              <p className="font-medium">
                {fresh && <span className="sr-only">Unread: </span>}
                {told.questionId || told.href ? (
                  <Link
                    href={told.href ?? `/questions/${told.questionId}`}
                    className="underline"
                    onClick={(event) => {
                      event.preventDefault();
                      void open(notification, told.href ?? `/questions/${told.questionId}`);
                    }}
                  >
                    {told.title}
                  </Link>
                ) : (
                  told.title
                )}
              </p>
              {told.detail && (
                <p className="mt-1 text-zinc-700 dark:text-zinc-300">{told.detail}</p>
              )}
              <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
                {new Date(notification.created_at).toLocaleString(undefined, {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </p>
            </li>
          );
        })}
      </ul>
      {next && (
        <button
          type="button"
          className={`${BUTTON} justify-self-start`}
          onClick={() => void load(next)}
        >
          Show more
        </button>
      )}
    </div>
  );
}
