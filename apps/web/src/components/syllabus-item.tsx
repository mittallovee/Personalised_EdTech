"use client";

import { useState } from "react";

import { ConfirmPanel } from "@/components/confirm-panel";
import { KIND_NAME, type Language, type Node } from "@/lib/syllabus";

const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";

export type Panel = "edit" | "retire" | null;

/**
 * One syllabus item: its name, order and names in other languages; for those who may change the
 * syllabus, the buttons to rename, retire and restore it.
 */
export function SyllabusItem({
  node,
  languages,
  canManage,
  panel,
  busy,
  error,
  onOpenPanel,
  onSave,
  onRetire,
  onRestore,
  onOpen,
}: {
  node: Node;
  languages: Language[];
  canManage: boolean;
  panel: Panel;
  busy: boolean;
  error: string | null;
  onOpenPanel: (panel: Panel) => void;
  onSave: (changes: { name: string; sort_order: number; labels: Record<string, string> }) => void;
  onRetire: () => void;
  onRestore: () => void;
  /** Go inside this item (to its subjects, chapters...); not offered for a subtopic. */
  onOpen: (() => void) | null;
}) {
  const [name, setName] = useState(node.name);
  const [sortOrder, setSortOrder] = useState(String(node.sort_order));
  const [labels, setLabels] = useState<Record<string, string>>({ ...node.labels });
  const retired = node.state === "DEPRECATED";
  const others = languages.filter((language) => language.tag !== "en");
  const shown = Object.entries(node.labels)
    .map(([tag, label]) => `${languages.find((l) => l.tag === tag)?.english_name ?? tag}: ${label}`)
    .join(" · ");

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const filled = Object.fromEntries(
      Object.entries(labels)
        .map(([tag, label]) => [tag, label.trim()] as const)
        .filter(([, label]) => label !== ""),
    );
    onSave({ name: name.trim(), sort_order: Number(sortOrder), labels: filled });
  }

  return (
    <li className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <span className={`font-medium ${retired ? "text-zinc-500 line-through" : ""}`}>
            {node.name}
          </span>
          {retired && (
            <span className="ml-2 rounded bg-zinc-200 px-2 py-0.5 text-xs dark:bg-zinc-800">
              Retired
            </span>
          )}
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Order {node.sort_order}
            {shown && ` · ${shown}`}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {onOpen && (
            <button type="button" onClick={onOpen} className={BUTTON}>
              Open
            </button>
          )}
          {canManage && !retired && panel !== "edit" && (
            <button type="button" onClick={() => onOpenPanel("edit")} className={BUTTON}>
              Edit
            </button>
          )}
          {canManage && !retired && panel !== "retire" && (
            <button type="button" onClick={() => onOpenPanel("retire")} className={BUTTON}>
              Retire
            </button>
          )}
          {canManage && retired && (
            <button type="button" disabled={busy} onClick={onRestore} className={BUTTON}>
              Restore
            </button>
          )}
        </div>
      </div>

      {panel === "edit" && (
        <form onSubmit={submit} aria-label={`Edit ${node.name}`} className="mt-3 space-y-3">
          <label className="block text-sm font-medium">
            Name (English)
            <input
              name="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={200}
              className={`${FIELD} mt-1`}
            />
          </label>
          <label className="block text-sm font-medium">
            Order (smaller comes first)
            <input
              name="sort_order"
              type="number"
              min={0}
              max={100000}
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value)}
              required
              className={`${FIELD} mt-1`}
            />
          </label>
          <fieldset className="grid gap-3 sm:grid-cols-2">
            <legend className="text-sm font-medium">Names in other languages</legend>
            {others.map((language) => (
              <label key={language.tag} className="block text-sm">
                {language.english_name} ({language.native_name})
                <input
                  name={`label_${language.tag}`}
                  value={labels[language.tag] ?? ""}
                  onChange={(e) => setLabels({ ...labels, [language.tag]: e.target.value })}
                  maxLength={200}
                  className={`${FIELD} mt-1`}
                />
              </label>
            ))}
          </fieldset>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="rounded-md bg-zinc-900 px-3 py-1 text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {busy ? "Saving…" : "Save"}
            </button>
            <button type="button" onClick={() => onOpenPanel(null)} className={BUTTON}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {panel === "retire" && (
        <ConfirmPanel
          question={`Retire ${node.name}?`}
          detail={`It can no longer be chosen for new questions, and nothing is deleted: questions that already use this ${KIND_NAME[node.kind]} keep it, and you can restore it any time.`}
          confirmLabel="Retire"
          busy={busy}
          onConfirm={onRetire}
          onCancel={() => onOpenPanel(null)}
        />
      )}

      {error && (
        <p role="alert" className={`mt-3 ${ALERT}`}>
          {error}
        </p>
      )}
    </li>
  );
}
