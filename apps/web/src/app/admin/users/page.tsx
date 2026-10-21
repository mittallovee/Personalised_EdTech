"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import type { components } from "@qbank/api-client";

import { AppShell } from "@/components/app-shell";
import { GrantsEditor } from "@/components/grants-editor";
import { LinkNotice, type IssuedLink } from "@/components/link-notice";
import { api, errorMessage, ifMatch } from "@/lib/api";
import { grantLabel } from "@/lib/grants";
import { useMe } from "@/lib/use-me";

type Member = components["schemas"]["MemberOut"];

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
  const [editing, setEditing] = useState<string | null>(null); // membership id
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

  async function newLink(member: Member, kind: "activation" | "reset") {
    setBusyId(member.membership_id);
    setRowError(null);
    try {
      const path = { membership_id: member.membership_id };
      const { data, error, response } =
        kind === "activation"
          ? await api().POST("/api/v1/members/{membership_id}/activation-link", {
              params: { path },
            })
          : await api().POST("/api/v1/members/{membership_id}/reset-link", { params: { path } });
      if (data) {
        setLink({ who: member.display_name, kind, token: data.token, expiresAt: data.expires_at });
      } else {
        setRowError({ id: member.membership_id, message: errorMessage(error, response.status) });
        void load(null); // the member may have changed (activated, removed...): show the truth
      }
    } catch {
      setRowError({ id: member.membership_id, message: NETWORK });
    } finally {
      setBusyId(null);
    }
  }

  async function saveGrants(member: Member, grants: string[]) {
    setBusyId(member.membership_id);
    setRowError(null);
    try {
      const { data, error, response } = await api().PUT("/api/v1/members/{membership_id}/grants", {
        params: {
          path: { membership_id: member.membership_id },
          header: { "If-Match": ifMatch(member.revision) },
        },
        body: { grants: grants as components["schemas"]["SetGrants"]["grants"] },
      });
      if (data) {
        setMembers((current) =>
          current.map((m) => (m.membership_id === data.membership_id ? data : m)),
        );
        setEditing(null);
      } else {
        setRowError({ id: member.membership_id, message: errorMessage(error, response.status) });
        if (response.status === 412 || response.status === 409) {
          setEditing(null);
          void load(null); // someone else changed it: reload so the next try starts from the truth
        }
      }
    } catch {
      setRowError({ id: member.membership_id, message: NETWORK });
    } finally {
      setBusyId(null);
    }
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
        Invite people, give faculty their grants, and make links when someone needs to get in.
      </p>

      {link && <LinkNotice link={link} onDismiss={() => setLink(null)} />}

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
            {members.map((member) => (
              <li
                key={member.membership_id}
                className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div>
                    <span className="font-medium">{member.display_name}</span>
                    <span className="ml-2 text-sm text-zinc-500">{member.email}</span>
                  </div>
                  <div className="flex gap-2 text-xs">
                    <span className="rounded-full bg-zinc-100 px-2 py-0.5 dark:bg-zinc-800">
                      {member.role.charAt(0) + member.role.slice(1).toLowerCase()}
                    </span>
                    {member.account_status !== "ACTIVE" && (
                      <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-800 dark:bg-amber-950 dark:text-amber-200">
                        {member.account_status === "INVITED" ? "Invited" : "Disabled"}
                      </span>
                    )}
                  </div>
                </div>
                <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
                  {member.role !== "FACULTY"
                    ? "Holds every grant"
                    : member.grants.length === 0
                      ? "No grants"
                      : `Grants: ${member.grants.map(grantLabel).join(", ")}`}
                </p>
                {member.actions.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {member.actions.includes("SET_GRANTS") && (
                      <button
                        type="button"
                        className={BUTTON}
                        onClick={() => {
                          setRowError(null);
                          setEditing(member.membership_id);
                        }}
                      >
                        Edit grants
                      </button>
                    )}
                    {member.actions.includes("NEW_ACTIVATION_LINK") && (
                      <button
                        type="button"
                        className={BUTTON}
                        disabled={busyId === member.membership_id}
                        onClick={() => void newLink(member, "activation")}
                      >
                        New activation link
                      </button>
                    )}
                    {member.actions.includes("NEW_RESET_LINK") && (
                      <button
                        type="button"
                        className={BUTTON}
                        disabled={busyId === member.membership_id}
                        onClick={() => void newLink(member, "reset")}
                      >
                        Password-reset link
                      </button>
                    )}
                  </div>
                )}
                {editing === member.membership_id && (
                  <GrantsEditor
                    name={member.display_name}
                    current={member.grants}
                    busy={busyId === member.membership_id}
                    onSave={(grants) => void saveGrants(member, grants)}
                    onCancel={() => setEditing(null)}
                  />
                )}
                {rowError?.id === member.membership_id && (
                  <p role="alert" className={`mt-3 ${ALERT}`}>
                    {rowError.message}
                  </p>
                )}
              </li>
            ))}
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
