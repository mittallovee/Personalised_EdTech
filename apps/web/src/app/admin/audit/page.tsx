"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import type { components } from "@qbank/api-client";

import { AppShell } from "@/components/app-shell";
import { api, errorMessage } from "@/lib/api";
import { changeLines, ENTITY_TYPES, entityTypeLabel, humanize } from "@/lib/audit";
import { useMe } from "@/lib/use-me";

type AuditEvent = components["schemas"]["AuditEventOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
const NETWORK = "Cannot reach the server. Check your connection and try again.";

/** What narrows the list. Dates are days in this browser's time zone, as `YYYY-MM-DD`. */
interface Filters {
  entityType: string;
  from: string;
  until: string;
  /** Set from an event's "Only this person" button. */
  actor: { id: string; name: string } | null;
  /** Set from an event's "Only this record" button. */
  record: { id: string; label: string } | null;
}

const NO_FILTERS: Filters = { entityType: "", from: "", until: "", actor: null, record: null };

function isFiltered(f: Filters): boolean {
  return Boolean(f.entityType || f.from || f.until || f.actor || f.record);
}

/** The API's `since`/`until` for the chosen days: the start of the first, the end of the last. */
function timeRange(f: Filters): { since?: string; until?: string } {
  const range: { since?: string; until?: string } = {};
  if (f.from) range.since = new Date(`${f.from}T00:00:00`).toISOString();
  if (f.until) {
    const end = new Date(`${f.until}T00:00:00`);
    end.setDate(end.getDate() + 1); // `until` is exclusive, so the whole last day is included
    range.until = end.toISOString();
  }
  return range;
}

function actorName(event: AuditEvent): string {
  const { actor } = event;
  if (actor.display_name) return actor.display_name;
  if (actor.is_platform_admin) return "Platform admin";
  return actor.user_id ? "Someone outside this coaching" : "The system";
}

/**
 * The coaching's audit log (I-03): who changed what and when, with before and after, newest
 * first. The API decides who may read it and which events they see; the page only filters.
 */
export default function AuditPage() {
  const router = useRouter();
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const moreInFlight = useRef(false);
  const [listState, setListState] = useState<"loading" | "ready" | "denied" | "failed">("loading");
  const [listError, setListError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  // Each fresh load (new filters) starts a new generation, so a slow answer to older filters never
  // replaces the list, and "Show more" for an old list is dropped.
  const generation = useRef(0);

  const load = useCallback(
    async (f: Filters, cursor: string | null) => {
      const mine = cursor ? generation.current : ++generation.current;
      let result;
      try {
        result = await api().GET("/api/v1/audit-events", {
          params: {
            query: {
              ...(cursor ? { cursor } : {}),
              ...(f.entityType ? { entity_type: f.entityType } : {}),
              ...(f.actor ? { actor_user_id: f.actor.id } : {}),
              ...(f.record ? { entity_id: f.record.id } : {}),
              ...timeRange(f),
            },
          },
        });
      } catch {
        if (mine !== generation.current) return;
        setListState("failed");
        setListError(NETWORK);
        return;
      }
      if (mine !== generation.current) return;
      if (result.response.status === 401) {
        router.replace("/login");
        return;
      }
      if (result.response.status === 403) {
        setListState("denied");
        return;
      }
      if (!result.data) {
        setListState("failed");
        setListError(errorMessage(result.error, result.response.status));
        return;
      }
      const page = result.data.data;
      // An event already shown is not added twice.
      setEvents((current) =>
        cursor ? [...current, ...page.filter((e) => !current.some((c) => c.id === e.id))] : page,
      );
      setNextCursor(result.data.page.next_cursor ?? null);
      setListState("ready");
      setListError(null);
    },
    [router],
  );

  useEffect(() => {
    // `load` sets state only after the network call returns, never during this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(filters, null);
  }, [load, filters]);

  /** "Show more": one request at a time, so pressing it twice does not load the page twice. */
  async function showMore() {
    if (moreInFlight.current || !nextCursor) return;
    moreInFlight.current = true;
    setLoadingMore(true);
    try {
      await load(filters, nextCursor);
    } finally {
      moreInFlight.current = false;
      setLoadingMore(false);
    }
  }

  function narrow(change: Partial<Filters>) {
    setFilters((current) => ({ ...current, ...change }));
  }

  if (loadError) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-4">
        <p role="alert" className={ALERT}>
          {loadError} Please try again.
        </p>
        <button type="button" onClick={retry} className={BUTTON}>
          Try again
        </button>
      </main>
    );
  }
  if (!me) return <p className="p-8 text-sm text-zinc-500">Loading…</p>;

  const platformLevel = me.is_platform_admin && me.acting_organization_id === null;

  return (
    <AppShell me={me} current="audit" onSignOut={signOut} onStopActing={stopActing}>
      {shellError && (
        <p role="alert" className={`mb-6 max-w-md ${ALERT}`}>
          {shellError}
        </p>
      )}
      <h1 className="text-2xl font-semibold">Audit log</h1>
      <p className="mt-1 mb-6 text-zinc-600 dark:text-zinc-400">
        {platformLevel
          ? "Platform-level changes: creating and changing coachings. Act in a coaching to read its own log."
          : "Every change in the coaching: who made it, when, and what it was before and after."}
      </p>

      {listState === "denied" && (
        <p role="alert" className={`max-w-md ${ALERT}`}>
          You don&apos;t have access to this page.
        </p>
      )}
      {listState === "loading" && <p className="text-sm text-zinc-500">Loading events…</p>}
      {listState === "failed" && (
        <div className="max-w-md space-y-3">
          <p role="alert" className={ALERT}>
            {listError}
          </p>
          <button type="button" className={BUTTON} onClick={() => void load(filters, null)}>
            Try again
          </button>
        </div>
      )}

      {listState === "ready" && (
        <>
          <form
            aria-label="Filter events"
            onSubmit={(event) => event.preventDefault()}
            className="mb-4 flex max-w-3xl flex-wrap items-end gap-3"
          >
            <label className="block space-y-1 text-sm font-medium">
              <span>Kind</span>
              <select
                className={`block ${FIELD}`}
                value={filters.entityType}
                onChange={(e) => narrow({ entityType: e.target.value })}
              >
                <option value="">Everything</option>
                {ENTITY_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block space-y-1 text-sm font-medium">
              <span>From</span>
              <input
                type="date"
                className={`block ${FIELD}`}
                value={filters.from}
                max={filters.until || undefined}
                onChange={(e) => narrow({ from: e.target.value })}
              />
            </label>
            <label className="block space-y-1 text-sm font-medium">
              <span>To</span>
              <input
                type="date"
                className={`block ${FIELD}`}
                value={filters.until}
                min={filters.from || undefined}
                onChange={(e) => narrow({ until: e.target.value })}
              />
            </label>
            {isFiltered(filters) && (
              <button type="button" className={BUTTON} onClick={() => setFilters(NO_FILTERS)}>
                Clear filters
              </button>
            )}
          </form>

          {(filters.actor || filters.record) && (
            <ul aria-label="Active filters" className="mb-4 flex flex-wrap gap-2 text-sm">
              {filters.actor && (
                <li className="flex items-center gap-2 rounded-full bg-zinc-100 px-3 py-1 dark:bg-zinc-800">
                  Done by {filters.actor.name}
                  <button
                    type="button"
                    className="underline"
                    onClick={() => narrow({ actor: null })}
                  >
                    Show everyone
                  </button>
                </li>
              )}
              {filters.record && (
                <li className="flex items-center gap-2 rounded-full bg-zinc-100 px-3 py-1 dark:bg-zinc-800">
                  About {filters.record.label}
                  <button
                    type="button"
                    className="underline"
                    onClick={() => narrow({ record: null })}
                  >
                    Show all records
                  </button>
                </li>
              )}
            </ul>
          )}
          <p className="mb-4 text-xs text-zinc-500">
            Times and days are in your browser&apos;s time zone.
          </p>

          {events.length === 0 ? (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {isFiltered(filters) ? "No events match these filters." : "No events yet."}
            </p>
          ) : (
            <ul aria-label="Events" className="max-w-3xl space-y-3">
              {events.map((event) => {
                const lines = changeLines(event.before, event.after);
                const who = actorName(event);
                return (
                  <li
                    key={event.id}
                    className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
                  >
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="font-medium">{humanize(event.action)}</span>
                      <time dateTime={event.created_at} className="text-sm text-zinc-500">
                        {new Date(event.created_at).toLocaleString()}
                      </time>
                    </div>
                    <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                      By {who}
                      {event.actor.is_platform_admin && event.actor.display_name
                        ? " (acting as platform admin)"
                        : ""}
                      {" · "}
                      {entityTypeLabel(event.entity_type)}
                    </p>
                    {lines.length > 0 && (
                      <ul aria-label="Changes" className="mt-2 space-y-0.5 text-sm">
                        {lines.map((line) => (
                          <li key={line}>{line}</li>
                        ))}
                      </ul>
                    )}
                    <div className="mt-3 flex flex-wrap gap-2">
                      {event.actor.user_id && (
                        <button
                          type="button"
                          className={BUTTON}
                          onClick={() => narrow({ actor: { id: event.actor.user_id!, name: who } })}
                        >
                          Only this person
                        </button>
                      )}
                      {event.entity_id && (
                        <button
                          type="button"
                          className={BUTTON}
                          onClick={() =>
                            narrow({
                              record: {
                                id: event.entity_id!,
                                label: `${entityTypeLabel(event.entity_type).toLowerCase()} ${event.entity_id!.slice(0, 8)}`,
                              },
                            })
                          }
                        >
                          Only this record
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
          {nextCursor && (
            <button
              type="button"
              className={`mt-4 ${BUTTON}`}
              disabled={loadingMore}
              onClick={() => void showMore()}
            >
              Show more
            </button>
          )}
        </>
      )}
    </AppShell>
  );
}
