import type { ReactNode } from "react";

import type { Me } from "@qbank/api-client";

// Modules arrive in later milestones (M3 authoring, M4 review, M5 AI, admin console).
const UPCOMING = ["Questions", "Review", "Taxonomy", "AI & prompts", "Admin"];

export function AppShell({
  me,
  onSignOut,
  children,
}: {
  me: Me;
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
            <li className="rounded-md bg-zinc-100 px-3 py-2 font-medium dark:bg-zinc-800">Home</li>
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
