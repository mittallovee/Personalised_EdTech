"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import type { ErrorResponse } from "@qbank/api-client";

import { AppShell } from "@/components/app-shell";
import { CoachingCard, type Coaching, type CoachingPanel } from "@/components/coaching-card";
import { LinkNotice, type IssuedLink } from "@/components/link-notice";
import { StatusNotice } from "@/components/status-notice";
import { api, errorMessage, ifMatch } from "@/lib/api";
import { useMe } from "@/lib/use-me";

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
const NETWORK = "Cannot reach the server. Check your connection and try again.";

/**
 * The platform admin's list of coachings: create one with its first Owner, rename it, suspend or
 * reactivate it (A-04, A-07), or act inside it (A-06). The API refuses everyone else (403).
 */
export default function CoachingsPage() {
  const router = useRouter();
  const { me, loadError, shellError, retry, signOut, stopActing } = useMe();
  const [coachings, setCoachings] = useState<Coaching[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const moreInFlight = useRef(false);
  const [listState, setListState] = useState<"loading" | "ready" | "denied" | "failed">("loading");
  const [listError, setListError] = useState<string | null>(null);
  const [link, setLink] = useState<IssuedLink | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [panel, setPanel] = useState<{ id: string; kind: CoachingPanel } | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [rowError, setRowError] = useState<{ id: string; message: string } | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  // A retry of the same creation reuses its Idempotency-Key, so a lost response never means two
  // coachings; a changed form gets a new key.
  const createKey = useRef<{ key: string; fingerprint: string } | null>(null);

  /** Load a page of coachings; a reload passes `keep` (how many were showing) to keep them all. */
  const load = useCallback(
    async (cursor: string | null, keep = 0) => {
      let after = cursor;
      let loaded: Coaching[] = [];
      for (;;) {
        let result;
        try {
          result = await api().GET("/api/v1/platform/organizations", {
            params: { query: after ? { cursor: after } : {} },
          });
        } catch {
          setListState("failed");
          setListError(NETWORK);
          return;
        }
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
        loaded = [...loaded, ...result.data.data];
        after = result.data.page.next_cursor ?? null;
        if (!after || loaded.length >= keep) break;
      }
      // A page already shown is not added twice, whatever order requests finish in.
      setCoachings((current) =>
        cursor
          ? [...current, ...loaded.filter((l) => !current.some((c) => c.id === l.id))]
          : loaded,
      );
      setNextCursor(after);
      setListState("ready");
      setListError(null);
    },
    [router],
  );

  /** "Show more": one request at a time, so pressing it twice does not load the page twice. */
  async function showMore() {
    if (moreInFlight.current || !nextCursor) return;
    moreInFlight.current = true;
    setLoadingMore(true);
    try {
      await load(nextCursor);
    } finally {
      moreInFlight.current = false;
      setLoadingMore(false);
    }
  }

  useEffect(() => {
    // `load` sets state only after the network call returns, never during this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(null);
  }, [load]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const body = {
      display_name: String(data.get("display_name")),
      timezone: String(data.get("timezone")),
      owner: {
        email: String(data.get("owner_email")),
        display_name: String(data.get("owner_name")),
      },
    };
    const fingerprint = JSON.stringify(body);
    if (createKey.current?.fingerprint !== fingerprint) {
      createKey.current = { key: crypto.randomUUID(), fingerprint };
    }
    setCreating(true);
    setCreateError(null);
    setNotice(null);
    try {
      const {
        data: created,
        error,
        response,
      } = await api().POST("/api/v1/platform/organizations", {
        body,
        params: { header: { "Idempotency-Key": createKey.current.key } },
      });
      if (created) {
        const added = created.organization;
        setCoachings((current) => [added, ...current.filter((c) => c.id !== added.id)]);
        setLink(
          created.activation && {
            who: created.owner.display_name,
            kind: "activation",
            token: created.activation.token,
            expiresAt: created.activation.expires_at,
          },
        );
        createKey.current = null;
        form.reset();
      } else {
        setCreateError(errorMessage(error, response.status));
      }
    } catch {
      setCreateError(NETWORK);
    } finally {
      setCreating(false);
    }
  }

  /**
   * One change to one coaching: shows that it is running, shows the API's message if it is refused
   * and reloads the list so the next try starts from what is really there.
   */
  async function change(
    coaching: Coaching,
    call: () => Promise<{ data?: Coaching; error?: unknown; response: Response }>,
    done: (updated: Coaching) => void,
  ) {
    setBusyId(coaching.id);
    setRowError(null);
    setNotice(null);
    try {
      const { data, error, response } = await call();
      if (data) {
        done(data);
        return;
      }
      const message = errorMessage(error as ErrorResponse | undefined, response.status);
      setRowError({ id: coaching.id, message });
      if (response.status === 412 || response.status === 409) setPanel(null);
      void load(null, coachings.length);
    } catch {
      setRowError({ id: coaching.id, message: NETWORK });
    } finally {
      setBusyId(null);
    }
  }

  function replace(updated: Coaching) {
    setCoachings((current) => current.map((c) => (c.id === updated.id ? updated : c)));
    setPanel(null);
  }

  function save(coaching: Coaching, changes: { display_name: string; timezone: string }) {
    void change(
      coaching,
      () =>
        api().PATCH("/api/v1/platform/organizations/{organization_id}", {
          params: {
            path: { organization_id: coaching.id },
            header: { "If-Match": ifMatch(coaching.revision) },
          },
          body: changes,
        }),
      (updated) => {
        replace(updated);
        setNotice(`${updated.display_name} was saved.`);
        // The banner names the coaching you are acting in: reload who you are if it just changed.
        if (updated.id === me?.acting_organization_id) retry();
      },
    );
  }

  function setStatus(coaching: Coaching, action: "suspend" | "reactivate") {
    const params = {
      path: { organization_id: coaching.id },
      header: { "If-Match": ifMatch(coaching.revision) },
    };
    void change(
      coaching,
      () =>
        action === "suspend"
          ? api().POST("/api/v1/platform/organizations/{organization_id}/suspend", { params })
          : api().POST("/api/v1/platform/organizations/{organization_id}/reactivate", { params }),
      (updated) => {
        replace(updated);
        setNotice(
          action === "suspend"
            ? `${updated.display_name} is suspended. Its people are signed out.`
            : `${updated.display_name} is active again. Its people can sign in.`,
        );
      },
    );
  }

  async function actIn(coaching: Coaching) {
    setBusyId(coaching.id);
    setRowError(null);
    setNotice(null);
    try {
      const { error, response } = await api().POST("/api/v1/platform/acting-organization", {
        body: { organization_id: coaching.id },
      });
      if (response.ok) {
        router.push("/admin/users"); // the banner and the coaching's screens load from there
        return;
      }
      setRowError({ id: coaching.id, message: errorMessage(error, response.status) });
    } catch {
      setRowError({ id: coaching.id, message: NETWORK });
    }
    setBusyId(null);
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

  return (
    <AppShell me={me} current="coachings" onSignOut={signOut} onStopActing={stopActing}>
      {shellError && (
        <p role="alert" className={`mb-6 max-w-md ${ALERT}`}>
          {shellError}
        </p>
      )}
      <h1 className="text-2xl font-semibold">Coachings</h1>
      <p className="mt-1 mb-6 text-zinc-600 dark:text-zinc-400">
        Create a coaching with its first Owner, rename it, suspend it, or act inside it.
      </p>

      {link && <LinkNotice link={link} onDismiss={() => setLink(null)} />}
      {notice && <StatusNotice>{notice}</StatusNotice>}

      {listState === "denied" && (
        <p role="alert" className={`max-w-md ${ALERT}`}>
          You don&apos;t have access to this page.
        </p>
      )}
      {listState === "failed" && (
        <div className="max-w-md space-y-3">
          <p role="alert" className={ALERT}>
            {listError}
          </p>
          <button type="button" className={BUTTON} onClick={() => void load(null)}>
            Try again
          </button>
        </div>
      )}
      {listState === "loading" && <p className="text-sm text-zinc-500">Loading coachings…</p>}

      {listState === "ready" && (
        <>
          <form
            onSubmit={create}
            aria-label="Create a coaching"
            className="mb-8 max-w-2xl space-y-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
          >
            <h2 className="font-medium">Create a coaching</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block space-y-1 text-sm font-medium">
                <span>Coaching name</span>
                <input name="display_name" required maxLength={200} className={FIELD} />
              </label>
              <label className="block space-y-1 text-sm font-medium">
                <span>Time zone</span>
                <input
                  name="timezone"
                  defaultValue="Asia/Kolkata"
                  required
                  maxLength={64}
                  className={FIELD}
                />
              </label>
              <label className="block space-y-1 text-sm font-medium">
                <span>Owner&apos;s name</span>
                <input name="owner_name" required maxLength={200} className={FIELD} />
              </label>
              <label className="block space-y-1 text-sm font-medium">
                <span>Owner&apos;s email</span>
                <input name="owner_email" type="email" required className={FIELD} />
              </label>
            </div>
            {createError && (
              <p role="alert" className={ALERT}>
                {createError}
              </p>
            )}
            <button
              type="submit"
              disabled={creating}
              className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {creating ? "Creating…" : "Create coaching and make the Owner's link"}
            </button>
          </form>

          <h2 className="mb-3 font-medium">All coachings</h2>
          <ul aria-label="Coachings" className="max-w-2xl space-y-3">
            {coachings.map((coaching) => {
              const open = panel?.id === coaching.id ? panel.kind : null;
              return (
                <CoachingCard
                  key={coaching.id}
                  coaching={coaching}
                  panel={open}
                  busy={busyId === coaching.id}
                  error={rowError?.id === coaching.id ? rowError.message : null}
                  onOpen={(kind) => {
                    setRowError(null);
                    setPanel({ id: coaching.id, kind });
                  }}
                  onClose={() => setPanel(null)}
                  onSave={(changes) => save(coaching, changes)}
                  onSuspend={() => setStatus(coaching, "suspend")}
                  onReactivate={() => setStatus(coaching, "reactivate")}
                  onActIn={() => void actIn(coaching)}
                />
              );
            })}
          </ul>
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
