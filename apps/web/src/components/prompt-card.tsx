"use client";

import type { components } from "@qbank/api-client";
import { useEffect, useState } from "react";

import { api, errorMessage, ifMatch } from "@/lib/api";
import { type Operation } from "@/lib/ai-admin";
import { SCOPE_LABEL, lineStyle, type Template } from "@/lib/prompts";
import { NETWORK } from "@/lib/use-catalogue";

import { PromptEditor } from "./prompt-editor";

type Locked = components["schemas"]["LockedPartsOut"];
type Language = components["schemas"]["LanguageOut"];
type Version = components["schemas"]["VersionOut"];
type Summary = components["schemas"]["VersionSummary"];
type Diff = components["schemas"]["PromptDiffOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const OK =
  "rounded-md bg-green-50 px-3 py-2 text-sm text-green-800 dark:bg-green-950 dark:text-green-200";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";

/**
 * One prompt: what it says now, its versions, a comparison of any two, and the switches (activate,
 * roll back, reset to the platform's, take or ignore a newer platform default). Which of these
 * the person may use is the API's decision; `canEdit` only decides whether the buttons are shown.
 */
export function PromptCard({
  template,
  canEdit,
  locked,
  languages,
  reload,
}: {
  template: Template;
  canEdit: boolean;
  locked: Locked | undefined;
  languages: Language[];
  reload: () => void;
}) {
  const operation: Operation = template.operation;
  const active = template.active_version;
  const [shown, setShown] = useState<Version | null>(null);
  const [versions, setVersions] = useState<Summary[] | null>(null);
  const [diff, setDiff] = useState<{ from: number; to: number; data: Diff } | null>(null);
  const [editing, setEditing] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const activeId = active?.id;
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    async function load() {
      try {
        const list = await api().GET("/api/v1/ai/prompts/templates/{template_id}/versions", {
          params: { path: { template_id: template.id } },
        });
        const current = activeId
          ? await api().GET("/api/v1/ai/prompts/versions/{version_id}", {
              params: { path: { version_id: activeId } },
            })
          : null;
        if (cancelled) return;
        if (list.data) setVersions(list.data.data);
        if (current?.data) setShown(current.data);
      } catch {
        if (!cancelled) setMessage({ ok: false, text: NETWORK });
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [open, template.id, activeId, attempt]);

  async function act(
    path: "activate" | "reset" | "adopt-default" | "dismiss-update",
    version?: string,
  ) {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const params = {
        path: { template_id: template.id },
        header: { "If-Match": ifMatch(template.revision) },
      };
      const result =
        path === "activate"
          ? await api().POST("/api/v1/ai/prompts/templates/{template_id}/activate", {
              params,
              body: { version_id: version ?? "" },
            })
          : path === "reset"
            ? await api().POST("/api/v1/ai/prompts/templates/{template_id}/reset", { params })
            : path === "adopt-default"
              ? await api().POST("/api/v1/ai/prompts/templates/{template_id}/adopt-default", {
                  params,
                })
              : await api().POST("/api/v1/ai/prompts/templates/{template_id}/dismiss-update", {
                  params,
                });
      if (result.data) {
        reload();
      } else if (result.response.status === 412) {
        setMessage({ ok: false, text: "Someone else changed this prompt. It has been reloaded." });
        reload();
      } else {
        setMessage({
          ok: false,
          text: errorMessage(result.error as never, result.response.status),
        });
      }
    } catch {
      setMessage({ ok: false, text: NETWORK });
    } finally {
      setBusy(false);
    }
  }

  async function compare(to: Summary) {
    if (!active || active.id === to.id) return;
    setMessage(null);
    try {
      const { data, error, response } = await api().GET("/api/v1/ai/prompts/diff", {
        params: { query: { from: active.id, to: to.id } },
      });
      if (data) setDiff({ from: active.version_no, to: to.version_no, data });
      else setMessage({ ok: false, text: errorMessage(error as never, response.status) });
    } catch {
      setMessage({ ok: false, text: NETWORK });
    }
  }

  const label = `${SCOPE_LABEL[template.scope]}${template.target_language ? ` (${template.target_language})` : ""}${template.scope === "PERSONAL" ? `: ${template.name}` : ""}`;

  return (
    <li className="grid gap-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="font-medium">{label}</h4>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          {active
            ? `Version ${active.version_no} in use`
            : template.scope === "COACHING"
              ? "Not switched on: the platform's default is used"
              : "No version yet"}
        </p>
      </div>
      {template.update_available && (
        <div role="status" className={`${OK} grid gap-2`}>
          <p>
            The platform has a newer default (version {template.update_available.version_no}):{" "}
            {template.update_available.change_note}
          </p>
          {canEdit && (
            <div className="flex gap-2">
              <button
                type="button"
                disabled={busy}
                className={BUTTON}
                onClick={() => void act("adopt-default")}
              >
                Use the new default
              </button>
              <button
                type="button"
                disabled={busy}
                className={BUTTON}
                onClick={() => void act("dismiss-update")}
              >
                Keep ours
              </button>
            </div>
          )}
        </div>
      )}
      {message && (
        <p role={message.ok ? "status" : "alert"} className={message.ok ? OK : ALERT}>
          {message.text}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className={BUTTON}
          aria-expanded={open}
        >
          {open ? "Hide" : "Show the text and versions"}
        </button>
        {canEdit && !editing && (
          <button
            type="button"
            onClick={() => {
              setOpen(true);
              setEditing(true);
            }}
            className={BUTTON}
          >
            Write a new version
          </button>
        )}
        {canEdit && template.scope === "COACHING" && active && (
          <button
            type="button"
            disabled={busy}
            onClick={() => void act("reset")}
            className={BUTTON}
          >
            Go back to the platform default
          </button>
        )}
      </div>
      {open && shown && !editing && (
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-zinc-50 p-3 text-sm dark:bg-zinc-900">
          {shown.instructions}
        </pre>
      )}
      {editing && (
        <PromptEditor
          operation={operation}
          scope={template.scope}
          template={template}
          startingText={shown?.instructions ?? ""}
          startingTemperature={shown?.temperature ?? null}
          locked={locked}
          languages={languages}
          onSaved={() => {
            setEditing(false);
            setAttempt((n) => n + 1);
            reload();
          }}
          onCancel={() => setEditing(false)}
        />
      )}
      {open && versions && (
        <section aria-label="Versions" className="grid gap-2">
          <h5 className="text-sm font-medium">Versions</h5>
          <ul className="grid gap-2">
            {versions.map((version) => (
              <li
                key={version.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800"
              >
                <span>
                  <strong>Version {version.version_no}</strong>
                  {version.id === active?.id && " (in use)"}: {version.change_note}
                  <span className="text-zinc-600 dark:text-zinc-400">
                    {" "}
                    by {version.author_name ?? "the platform"},{" "}
                    {new Date(version.created_at).toLocaleDateString()}
                  </span>
                </span>
                <span className="flex gap-2">
                  {active && version.id !== active.id && (
                    <button type="button" className={BUTTON} onClick={() => void compare(version)}>
                      Compare with the one in use
                    </button>
                  )}
                  {canEdit && template.scope !== "PERSONAL" && version.id !== active?.id && (
                    <button
                      type="button"
                      disabled={busy}
                      className={BUTTON}
                      onClick={() => void act("activate", version.id)}
                    >
                      {active && version.version_no < active.version_no
                        ? "Roll back to this"
                        : "Use this"}
                    </button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
      {diff && (
        <section aria-label="Comparison" className="grid gap-1">
          <h5 className="text-sm font-medium">
            Version {diff.from} (in use) compared with version {diff.to}
          </h5>
          {!diff.data.changed ? (
            <p className="text-sm">They are the same.</p>
          ) : (
            <pre className="max-h-96 overflow-auto rounded-md border border-zinc-200 p-2 text-sm dark:border-zinc-800">
              {diff.data.lines.map((line, index) => {
                const style = lineStyle(line);
                return (
                  <div key={index} className={`whitespace-pre-wrap ${style.className}`}>
                    {style.mark} {line.text}
                  </div>
                );
              })}
            </pre>
          )}
          {diff.data.temperature_from !== diff.data.temperature_to && (
            <p className="text-sm">
              Temperature: {diff.data.temperature_from ?? "default"} to{" "}
              {diff.data.temperature_to ?? "default"}.
            </p>
          )}
        </section>
      )}
    </li>
  );
}
