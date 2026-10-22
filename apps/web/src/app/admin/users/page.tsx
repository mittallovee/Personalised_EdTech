"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import type { components, ErrorResponse } from "@qbank/api-client";

import { AppShell } from "@/components/app-shell";
import { LinkNotice, type IssuedLink } from "@/components/link-notice";
import { MemberCard, type Member, type Panel } from "@/components/member-card";
import { api, errorMessage, ifMatch } from "@/lib/api";
import { useMe } from "@/lib/use-me";

type Role = components["schemas"]["ChangeRole"]["expected_role"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON = "rounded-md border border-zinc-300 px-3 py-1 text-sm dark:border-zinc-700";
const NETWORK = "Cannot reach the server. Check your connection and try again.";

/**
 * Members of the coaching: who they are, their grants, and the buttons the API says the signed-in
 * person may use on each (`actions`). The page holds no permission rules; the API decides and
 * refuses everything else.
 */
export default function UsersPage() {
  const router = useRouter();
  const { me, loadError, signOutError, retry, signOut } = useMe();
  const [members, setMembers] = useState<Member[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [listState, setListState] = useState<"loading" | "ready" | "denied" | "failed">("loading");
  const [listError, setListError] = useState<string | null>(null);
  const [link, setLink] = useState<IssuedLink | null>(null);
  const [panel, setPanel] = useState<{ id: string; kind: Panel } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [rowError, setRowError] = useState<{ id: string; message: string } | null>(null);
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  // A retry of the same invitation reuses its Idempotency-Key, so a lost response never means
  // two accounts; a changed form gets a new key.
  const inviteKey = useRef<{ key: string; fingerprint: string } | null>(null);

  const load = useCallback(
    async (cursor: string | null) => {
      let result;
      try {
        result = await api().GET("/api/v1/members", {
          params: { query: cursor ? { cursor } : {} },
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
      const page = result.data;
      setMembers((current) => (cursor ? [...current, ...page.data] : page.data));
      setNextCursor(page.page.next_cursor ?? null);
      setListState("ready");
      setListError(null);
    },
    [router],
  );

  useEffect(() => {
    // `load` sets state only after the network call returns, never during this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(null);
  }, [load]);

  async function invite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const body = {
      email: String(data.get("email")),
      display_name: String(data.get("display_name")),
      role: String(data.get("role")) as "ADMIN" | "FACULTY",
    };
    const fingerprint = JSON.stringify(body);
    if (inviteKey.current?.fingerprint !== fingerprint) {
      inviteKey.current = { key: crypto.randomUUID(), fingerprint };
    }
    setInviting(true);
    setInviteError(null);
    try {
      const {
        data: invited,
        error,
        response,
      } = await api().POST("/api/v1/members/invitations", {
        body,
        params: { header: { "Idempotency-Key": inviteKey.current.key } },
      });
      if (invited) {
        const added = invited.member;
        setMembers((current) => [
          added,
          ...current.filter((m) => m.membership_id !== added.membership_id),
        ]);
        setLink(
          invited.activation && {
            who: added.display_name,
            kind: "activation",
            token: invited.activation.token,
            expiresAt: invited.activation.expires_at,
          },
        );
        inviteKey.current = null;
        form.reset();
      } else {
        setInviteError(errorMessage(error, response.status));
      }
    } catch {
      setInviteError(NETWORK);
    } finally {
      setInviting(false);
    }
  }

  /**
   * One change to one person: shows that it is running, shows the API's message if it is refused,
   * and reloads the list after a refusal so the next try starts from what is really there. A
   * stale or conflicting answer also closes the panel, because what it asked about has changed.
   */
  async function change<T>(
    member: Member,
    call: () => Promise<{ data?: T; error?: unknown; response: Response }>,
    done: (data: T) => void,
  ) {
    setBusyId(member.membership_id);
    setRowError(null);
    setNotice(null);
    try {
      const { data, error, response } = await call();
      if (data) {
        done(data);
        return;
      }
      const message = errorMessage(error as ErrorResponse | undefined, response.status);
      setRowError({ id: member.membership_id, message });
      if (response.status === 412 || response.status === 409) setPanel(null);
      void load(null);
    } catch {
      setRowError({ id: member.membership_id, message: NETWORK });
    } finally {
      setBusyId(null);
    }
  }

  function replace(updated: Member) {
    setMembers((current) =>
      current.map((m) => (m.membership_id === updated.membership_id ? updated : m)),
    );
    setPanel(null);
  }

  function newLink(member: Member, kind: "activation" | "reset") {
    const path = { membership_id: member.membership_id };
    const call = () =>
      kind === "activation"
        ? api().POST("/api/v1/members/{membership_id}/activation-link", { params: { path } })
        : api().POST("/api/v1/members/{membership_id}/reset-link", { params: { path } });
    void change(member, call, (data) =>
      setLink({ who: member.display_name, kind, token: data.token, expiresAt: data.expires_at }),
    );
  }

  function saveGrants(member: Member, grants: string[]) {
    void change(
      member,
      () =>
        api().PUT("/api/v1/members/{membership_id}/grants", {
          params: {
            path: { membership_id: member.membership_id },
            header: { "If-Match": ifMatch(member.revision) },
          },
          body: { grants: grants as components["schemas"]["SetGrants"]["grants"] },
        }),
      replace,
    );
  }

  function changeRole(member: Member) {
    const promoting = member.role === "FACULTY";
    void change(
      member,
      () =>
        api().POST("/api/v1/members/{membership_id}/change-role", {
          params: {
            path: { membership_id: member.membership_id },
            header: { "If-Match": ifMatch(member.revision) },
          },
          body: { expected_role: member.role as Role, new_role: promoting ? "ADMIN" : "FACULTY" },
        }),
      (updated) => {
        replace(updated);
        setNotice(`${member.display_name} is now ${promoting ? "an admin" : "faculty"}.`);
      },
    );
  }

  function remove(member: Member) {
    void change(
      member,
      () =>
        api().POST("/api/v1/members/{membership_id}/remove", {
          params: {
            path: { membership_id: member.membership_id },
            header: { "If-Match": ifMatch(member.revision) },
          },
          body: { expected_role: member.role as Role },
        }),
      () => {
        setMembers((current) => current.filter((m) => m.membership_id !== member.membership_id));
        setPanel(null);
        setNotice(`${member.display_name} was removed. Their access has ended.`);
      },
    );
  }

  /** The current Owner, from the list or, for a long list, from the pages not loaded yet. */
  async function findOwner(): Promise<Member | null> {
    const loaded = members.find((m) => m.role === "OWNER");
    if (loaded) return loaded;
    let cursor = nextCursor;
    while (cursor) {
      const { data } = await api().GET("/api/v1/members", { params: { query: { cursor } } });
      if (!data) return null;
      const found = data.data.find((m) => m.role === "OWNER");
      if (found) return found;
      cursor = data.page.next_cursor ?? null;
    }
    return null;
  }

  async function transfer(heir: Member) {
    let owner: Member | null;
    try {
      owner = await findOwner();
    } catch {
      setRowError({ id: heir.membership_id, message: NETWORK });
      return;
    }
    if (!owner) {
      setRowError({
        id: heir.membership_id,
        message: "Could not find the current Owner. Reload the page and try again.",
      });
      return;
    }
    const current = owner;
    void change(
      heir,
      () =>
        api().POST("/api/v1/organization/transfer-ownership", {
          params: { header: { "If-Match": ifMatch(current.revision) } },
          body: {
            expected_owner_membership_id: current.membership_id,
            new_owner_membership_id: heir.membership_id,
          },
        }),
      () => {
        setPanel(null);
        setNotice(`${heir.display_name} is now the Owner. You are an admin.`);
        void load(null);
        retry(); // your own role changed: reload who you are
      },
    );
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
    <AppShell me={me} current="users" onSignOut={signOut}>
      {signOutError && (
        <p role="alert" className={`mb-6 max-w-md ${ALERT}`}>
          {signOutError}
        </p>
      )}
      <h1 className="text-2xl font-semibold">Users &amp; grants</h1>
      <p className="mt-1 mb-6 text-zinc-600 dark:text-zinc-400">
        Invite people, give faculty their grants, change roles, remove people, and make links when
        someone needs to get in.
      </p>

      {link && <LinkNotice link={link} onDismiss={() => setLink(null)} />}
      {notice && (
        <p
          role="status"
          className="mb-6 max-w-2xl rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
        >
          {notice}
        </p>
      )}

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
      {listState === "loading" && <p className="text-sm text-zinc-500">Loading people…</p>}

      {listState === "ready" && (
        <>
          <form
            onSubmit={invite}
            aria-label="Invite someone"
            className="mb-8 max-w-2xl space-y-3 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
          >
            <h2 className="font-medium">Invite someone</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block space-y-1 text-sm font-medium">
                <span>Name</span>
                <input name="display_name" required maxLength={200} className={FIELD} />
              </label>
              <label className="block space-y-1 text-sm font-medium">
                <span>Email</span>
                <input name="email" type="email" required className={FIELD} />
              </label>
            </div>
            <label className="block space-y-1 text-sm font-medium sm:w-1/2">
              <span>Role</span>
              <select name="role" defaultValue="FACULTY" className={FIELD}>
                <option value="FACULTY">Faculty</option>
                <option value="ADMIN">Admin</option>
              </select>
            </label>
            {inviteError && (
              <p role="alert" className={ALERT}>
                {inviteError}
              </p>
            )}
            <button
              type="submit"
              disabled={inviting}
              className="rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
            >
              {inviting ? "Inviting…" : "Invite and make link"}
            </button>
          </form>

          <h2 className="mb-3 font-medium">People in your coaching</h2>
          <ul aria-label="Members" className="max-w-2xl space-y-3">
            {members.map((member) => {
              const id = member.membership_id;
              const open = panel?.id === id ? panel.kind : null;
              return (
                <MemberCard
                  key={id}
                  member={member}
                  panel={open}
                  busy={busyId === id}
                  error={rowError?.id === id ? rowError.message : null}
                  onOpen={(kind) => {
                    setRowError(null);
                    setPanel({ id, kind });
                  }}
                  onClose={() => setPanel(null)}
                  onNewLink={(kind) => newLink(member, kind)}
                  onSaveGrants={(grants) => saveGrants(member, grants)}
                  onChangeRole={() => changeRole(member)}
                  onRemove={() => remove(member)}
                  onTransfer={() => void transfer(member)}
                />
              );
            })}
          </ul>
          {nextCursor && (
            <button
              type="button"
              className={`mt-4 ${BUTTON}`}
              onClick={() => void load(nextCursor)}
            >
              Show more
            </button>
          )}
        </>
      )}
    </AppShell>
  );
}
