import Link from "next/link";
import type { ReactNode } from "react";

import type { Me } from "@qbank/api-client";

// Modules arrive in later milestones (M3 authoring, M4 review, M5 AI, more admin screens).
const UPCOMING = ["Questions", "Review", "Taxonomy", "AI & prompts"];

/**
 * Whether to show the Users & grants link. Only a hint for the menu: the API refuses everyone
 * else (403) whatever the menu shows, and decides what each person may do on the page.
 */
function showsUsers(me: Me): boolean {
  const role = me.organization?.role;
  return role === "OWNER" || role === "ADMIN" || me.acting_organization_id !== null;
}

export type Page = "home" | "users";

const ITEM = "block rounded-md px-3 py-2";
const CURRENT = "bg-zinc-100 font-medium dark:bg-zinc-800";

export function AppShell({
  me,
  current,
  onSignOut,
  children,
}: {
  me: Me;
  current: Page;
  onSignOut: () => void;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b border-zinc-200 px-6 py-3 dark:border-zinc-800">
        <span className="font-semibold">{me.organization?.display_name ?? "Question Bank"}</span>
        <div className="flex items-center gap-4 text-sm">
          <span>{me.display_name}</span>
          <button
            type="button"
            onClick={onSignOut}
            className="rounded-md border border-zinc-300 px-3 py-1 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            Sign out
          </button>
        </div>
      </header>
      <div className="flex flex-1">
        <nav
          aria-label="Modules"
          className="w-52 border-r border-zinc-200 p-4 dark:border-zinc-800"
        >
          <ul className="space-y-1 text-sm">
            <li>
              <Link
                href="/"
                aria-current={current === "home" ? "page" : undefined}
                className={`${ITEM} ${current === "home" ? CURRENT : "hover:bg-zinc-50 dark:hover:bg-zinc-900"}`}
              >
                Home
              </Link>
            </li>
            {showsUsers(me) && (
              <li>
                <Link
                  href="/admin/users"
                  aria-current={current === "users" ? "page" : undefined}
                  className={`${ITEM} ${current === "users" ? CURRENT : "hover:bg-zinc-50 dark:hover:bg-zinc-900"}`}
                >
                  Users &amp; grants
                </Link>
              </li>
            )}
            {UPCOMING.map((name) => (
              <li
                key={name}
                className="px-3 py-2 text-zinc-400"
                title="Coming in a later milestone"
              >
                {name}
              </li>
            ))}
          </ul>
        </nav>
        <main className="flex-1 p-8">{children}</main>
      </div>
    </div>
  );
}
