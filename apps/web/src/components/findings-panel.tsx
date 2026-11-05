import type { components } from "@qbank/api-client";

type Finding = components["schemas"]["FindingOut"];

const LEVELS: { level: Finding["level"]; title: string; hint: string; style: string }[] = [
  {
    level: "error",
    title: "Mistakes",
    hint: "Something written is not valid.",
    style: "text-red-700 dark:text-red-300",
  },
  {
    level: "incomplete",
    title: "Still to do",
    hint: "Needed before this can be reviewed.",
    style: "text-amber-800 dark:text-amber-300",
  },
  {
    level: "warning",
    title: "Worth a look",
    hint: "Allowed, but check it.",
    style: "text-zinc-700 dark:text-zinc-300",
  },
];

/**
 * What is wrong with the question in plain words, from the server's findings (design note §5.4).
 * A draft with findings can still be saved; review and publishing will wait for the first two
 * groups to be empty.
 */
export function FindingsPanel({ findings }: { findings: Finding[] }) {
  return (
    <section aria-label="Findings" className="rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="text-base font-semibold">Findings</h2>
      {findings.length === 0 ? (
        <p className="mt-2 text-sm text-emerald-800 dark:text-emerald-300">
          Nothing left to fix.
        </p>
      ) : (
        LEVELS.map(({ level, title, hint, style }) => {
          const group = findings.filter((finding) => finding.level === level);
          if (group.length === 0) return null;
          return (
            <div key={level} className="mt-3">
              <h3 className={`text-sm font-medium ${style}`}>
                {title} ({group.length})
              </h3>
              <p className="text-xs text-zinc-600 dark:text-zinc-400">{hint}</p>
              <ul className="mt-1 grid gap-1 text-sm">
                {group.map((finding, index) => (
                  <li key={`${finding.code}-${finding.path}-${index}`}>{finding.message}</li>
                ))}
              </ul>
            </div>
          );
        })
      )}
    </section>
  );
}
