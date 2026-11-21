"use client";

import type { components } from "@qbank/api-client";
import { useCallback, useEffect, useState } from "react";

import { USAGE_STATE_TEXT, formatInr, parseAmount, usagePercent } from "@/lib/ai-admin";
import { api, errorMessage, ifMatch } from "@/lib/api";
import { useAll } from "@/lib/use-all";
import { NETWORK } from "@/lib/use-catalogue";

type Usage = components["schemas"]["UsageOut"];
type PersonUsage = components["schemas"]["PersonUsageOut"];
type Budget = components["schemas"]["BudgetOut"];
type Member = components["schemas"]["MemberOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/** A bar for how much of a budget is used. The amounts beside it are exact; the bar only shows share. */
function Bar({ spent, limit, label }: { spent: string; limit: string | null; label: string }) {
  const percent = usagePercent(spent, limit);
  if (percent === null) return null;
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      className="h-2 w-full rounded bg-zinc-200 dark:bg-zinc-800"
    >
      <div
        className={`h-2 rounded ${percent >= 100 ? "bg-red-600" : percent >= 80 ? "bg-amber-500" : "bg-emerald-600"}`}
        style={{ width: `${percent}%` }}
      />
    </div>
  );
}

/** The signed-in person's own use of the AI this month and what is left of their budget (H-05, H-06). */
export function MyUsage() {
  const [usage, setUsage] = useState<Usage | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const { data, error, response } = await api().GET("/api/v1/ai/usage/me");
        if (cancelled) return;
        if (data) setUsage(data);
        else setProblem(errorMessage(error as never, response.status));
      } catch {
        if (!cancelled) setProblem(NETWORK);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section aria-label="Your use" className="grid max-w-xl gap-2">
      <h2 className="text-lg font-medium">Your use this month</h2>
      {problem && (
        <p role="alert" className={ALERT}>
          {problem}
        </p>
      )}
      {!usage && !problem && <p>Loading…</p>}
      {usage && (
        <>
          <p>
            Used <strong>{formatInr(usage.spent_inr)}</strong>
            {usage.limit_inr !== null && ` of ${formatInr(usage.limit_inr)}`} (${usage.spent_usd}).{" "}
            {USAGE_STATE_TEXT[usage.state] ?? usage.state}.
          </p>
          <Bar spent={usage.spent_inr} limit={usage.limit_inr} label="Your budget used" />
          {usage.remaining_inr !== null && (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {formatInr(usage.remaining_inr)} left. The month is the calendar month in India time
              and starts again on the 1st.
            </p>
          )}
        </>
      )}
    </section>
  );
}

/** Everyone's use this month, and each person's own budget (admins only; the API refuses others). */
export function EveryonesUsage() {
  const [month, setMonth] = useState("");
  const [people, setPeople] = useState<PersonUsage[] | null>(null);
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [problem, setProblem] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const reload = useCallback(() => setAttempt((n) => n + 1), []);

  const fetchMembers = useCallback(
    (cursor: string | null) =>
      api().GET("/api/v1/members", { params: { query: cursor ? { cursor } : {} } }),
    [],
  );
  const members = useAll<Member>("members", fetchMembers);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [list, own] = await Promise.all([
          api().GET("/api/v1/ai/usage", { params: { query: { month: month || undefined } } }),
          api().GET("/api/v1/ai/budgets"),
        ]);
        if (cancelled) return;
        if (list.data) {
          setPeople(list.data.data);
          setProblem(null);
        } else {
          setProblem(
            list.response.status === 403
              ? "Only the Owner and admins may see everyone's use."
              : errorMessage(list.error as never, list.response.status),
          );
        }
        if (own.data) setBudgets(own.data.data);
      } catch {
        if (!cancelled) setProblem(NETWORK);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [month, attempt]);

  const rows = members.items.map((member) => ({
    member,
    usage: people?.find((item) => item.user_id === member.user_id) ?? null,
    budget: budgets.find((item) => item.user_id === member.user_id) ?? null,
  }));

  return (
    <section aria-label="Everyone's use" className="grid gap-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium">Everyone&apos;s use</h2>
          <p className="max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
            What each person has used, and the monthly budget they have: the default from Admin, AI
            unless you give someone their own.
          </p>
        </div>
        <label className="grid gap-1 text-sm">
          Month
          <input
            type="month"
            value={month}
            onChange={(event) => setMonth(event.target.value)}
            className={FIELD}
          />
        </label>
      </div>
      {problem && (
        <p role="alert" className={ALERT}>
          {problem}
        </p>
      )}
      {members.failed && (
        <p role="alert" className={ALERT}>
          The list of people could not be read.
        </p>
      )}
      {(!people || members.loading) && !problem && <p>Loading…</p>}
      {people && !members.loading && (
        <ul className="grid gap-3">
          {rows.map((row) => (
            <PersonRow
              key={row.member.user_id}
              name={row.member.display_name}
              role={row.member.role}
              userId={row.member.user_id}
              usage={row.usage}
              budget={row.budget}
              onChanged={reload}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

function PersonRow({
  name,
  role,
  userId,
  usage,
  budget,
  onChanged,
}: {
  name: string;
  role: string;
  userId: string;
  usage: PersonUsage | null;
  budget: Budget | null;
  onChanged: () => void;
}) {
  const [typed, setTyped] = useState(budget?.monthly_inr ?? "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function save() {
    if (busy) return;
    const parsed = parseAmount(typed, { maxDecimals: 2, max: 10000000, allowEmpty: false });
    if (!parsed.ok || parsed.value === null) {
      setMessage(parsed.ok ? "Enter a number." : parsed.message);
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const { error, response } = await api().PUT("/api/v1/ai/budgets/{user_id}", {
        params: {
          path: { user_id: userId },
          header: budget ? { "If-Match": ifMatch(budget.revision) } : {},
        },
        body: { monthly_inr: parsed.value },
      });
      if (response.ok) onChanged();
      else if (response.status === 412) {
        setMessage("Someone else changed this. It has been reloaded.");
        onChanged();
      } else setMessage(errorMessage(error as never, response.status));
    } catch {
      setMessage(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  async function clear() {
    if (busy || !budget) return;
    setBusy(true);
    setMessage(null);
    try {
      const { error, response } = await api().DELETE("/api/v1/ai/budgets/{user_id}", {
        params: { path: { user_id: userId }, header: { "If-Match": ifMatch(budget.revision) } },
      });
      if (response.ok) {
        setTyped("");
        onChanged();
      } else setMessage(errorMessage(error as never, response.status));
    } catch {
      setMessage(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="grid gap-2 rounded-md border border-zinc-200 p-3 text-sm dark:border-zinc-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium">
          {name}{" "}
          <span className="font-normal text-zinc-600 dark:text-zinc-400">
            ({role.toLowerCase()})
          </span>
        </p>
        <p>
          {usage ? (
            <>
              {formatInr(usage.spent_inr)}
              {usage.limit_inr !== null && ` of ${formatInr(usage.limit_inr)}`} ·{" "}
              {USAGE_STATE_TEXT[usage.state] ?? usage.state}
            </>
          ) : (
            "No use"
          )}
        </p>
      </div>
      {usage && (
        <Bar spent={usage.spent_inr} limit={usage.limit_inr} label={`${name}'s budget used`} />
      )}
      <form
        aria-label={`Budget for ${name}`}
        className="flex flex-wrap items-end gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <label className="grid gap-1">
          {budget
            ? "Their own monthly budget (rupees)"
            : "Give them their own monthly budget (rupees)"}
          <input
            inputMode="decimal"
            value={typed}
            onChange={(event) => setTyped(event.target.value)}
            className={FIELD}
          />
        </label>
        <button type="submit" disabled={busy} className={PRIMARY}>
          Save
        </button>
        {budget && (
          <button type="button" disabled={busy} onClick={() => void clear()} className={BUTTON}>
            Use the default
          </button>
        )}
      </form>
      {message && (
        <p role="alert" className="text-red-700 dark:text-red-300">
          {message}
        </p>
      )}
    </li>
  );
}
