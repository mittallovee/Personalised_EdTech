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

/**
 * Whether to show the Audit log link: the same people as Users & grants, and platform admins, who
 * read platform-level events when they are not acting in a coaching. A hint, like the above.
 */
function showsAudit(me: Me): boolean {
  return showsUsers(me) || me.is_platform_admin;
}

/** Whether to show the Coachings link: the platform admin's own screen. A hint, like the above. */
function showsCoachings(me: Me): boolean {
  return me.is_platform_admin;
}

export type Page = "home" | "users" | "coachings" | "audit" | "profile";

const ITEM = "block rounded-md px-3 py-2";
const CURRENT = "bg-zinc-100 font-medium dark:bg-zinc-800";

export function AppShell({
  me,
  current,
  onSignOut,
  onStopActing,
  children,
}: {
  me: Me;
  current: Page;
  onSignOut: () => void;
  onStopActing: () => void;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col">
      {me.acting_organization_id && (
        <div
          role="region"
          aria-label="Acting in a coaching"
          className="flex flex-wrap items-center justify-between gap-2 bg-amber-200 px-6 py-2 text-sm text-amber-950"
        >
          <span>
            Acting in <strong>{me.acting_organization_name}</strong>. You have full authority here,
            and what you change is recorded as a platform change.
          </span>
          <button
            type="button"
            onClick={onStopActing}
            className="rounded-md border border-amber-900 px-3 py-1 font-medium hover:bg-amber-300"
          >
            Stop acting
          </button>
        </div>
      )}
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
            {showsCoachings(me) && (
              <li>
                <Link
                  href="/platform/coachings"
                  aria-current={current === "coachings" ? "page" : undefined}
                  className={`${ITEM} ${current === "coachings" ? CURRENT : "hover:bg-zinc-50 dark:hover:bg-zinc-900"}`}
                >
                  Coachings
                </Link>
              </li>
            )}
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
            {showsAudit(me) && (
              <li>
                <Link
                  href="/admin/audit"
                  aria-current={current === "audit" ? "page" : undefined}
                  className={`${ITEM} ${current === "audit" ? CURRENT : "hover:bg-zinc-50 dark:hover:bg-zinc-900"}`}
                >
                  Audit log
                </Link>
              </li>
            )}
            <li>
              <Link
                href="/profile"
                aria-current={current === "profile" ? "page" : undefined}
                className={`${ITEM} ${current === "profile" ? CURRENT : "hover:bg-zinc-50 dark:hover:bg-zinc-900"}`}
              >
                Profile
              </Link>
            </li>
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
