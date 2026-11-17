"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";

/** How often the unread count is read again while the page is open (design note §6). */
const EVERY_MS = 60_000;

/**
 * The header's link to the notifications, with how many are unread. Read when the page opens,
 * every minute, and when the person comes back to the tab. A count that cannot be read shows none
 * rather than a wrong number.
 */
export function NotificationBell() {
  const [unread, setUnread] = useState<number | null>(null);

  useEffect(() => {
    let stopped = false;
    async function read() {
      try {
        const result = await api().GET("/api/v1/notifications/unread-count");
        if (!stopped) setUnread(result.data ? result.data.count : null);
      } catch {
        if (!stopped) setUnread(null);
      }
    }
    void read();
    const timer = window.setInterval(() => void read(), EVERY_MS);
    const onFocus = () => void read();
    window.addEventListener("focus", onFocus);
    window.addEventListener("qbank:notifications-read", onFocus);
    return () => {
      stopped = true;
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("qbank:notifications-read", onFocus);
    };
  }, []);

  // The link's name is its visible text ("Notifications 3 unread"), so what is read out and what
  // is seen agree.
  return (
    <Link
      href="/notifications"
      className="relative rounded-md border border-zinc-300 px-3 py-1 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
    >
      Notifications
      {unread !== null && unread > 0 && (
        <>
          {" "}
          <span className="ml-1 rounded-full bg-red-600 px-2 py-0.5 text-xs font-semibold text-white">
            {unread > 99 ? "99+" : unread}
            <span className="sr-only"> unread</span>
          </span>
        </>
      )}
    </Link>
  );
}

/** Tell the bell to read its count again now (after something was marked read on this page). */
export function notificationsChanged(): void {
  window.dispatchEvent(new Event("qbank:notifications-read"));
}
