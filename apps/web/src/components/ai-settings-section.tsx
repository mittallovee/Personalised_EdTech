"use client";

import type { components } from "@qbank/api-client";
import { useEffect, useState } from "react";

import { api, errorMessage, ifMatch } from "@/lib/api";
import {
  MODE_LABEL,
  OPERATIONS,
  OPERATION_LABEL,
  PROVIDER_LABEL,
  formatInr,
  parseAmount,
  type Mode,
  type Operation,
} from "@/lib/ai-admin";
import { NETWORK } from "@/lib/use-catalogue";

type Settings = components["schemas"]["SettingsOut"];
type OperationRow = components["schemas"]["OperationOut"];
type Model = components["schemas"]["ModelOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const OK =
  "rounded-md bg-green-50 px-3 py-2 text-sm text-green-800 dark:bg-green-950 dark:text-green-200";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/** The coaching's money rules (H-05, H-06) and which model each operation uses first (H-03, H-04). */
export function AiSettingsSection({ version }: { version: number }) {
  return (
    <>
      <MoneyForm />
      <OperationsForm version={version} />
    </>
  );
}

function MoneyForm() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [rate, setRate] = useState("");
  const [budget, setBudget] = useState("");
  const [problems, setProblems] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const { data, error, response } = await api().GET("/api/v1/ai/settings");
        if (cancelled) return;
        if (data) {
          setSettings(data);
          setRate(data.usd_to_inr ?? "");
          setBudget(data.default_budget_inr ?? "");
        } else {
          setMessage({ ok: false, text: errorMessage(error as never, response.status) });
        }
      } catch {
        if (!cancelled) setMessage({ ok: false, text: NETWORK });
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  async function save() {
    if (busy || !settings) return;
    const found: Record<string, string> = {};
    const parsedRate = parseAmount(rate, { maxDecimals: 4, max: 10000, allowEmpty: true });
    const parsedBudget = parseAmount(budget, { maxDecimals: 2, max: 10000000, allowEmpty: true });
    if (!parsedRate.ok) found.rate = parsedRate.message;
    if (!parsedBudget.ok) found.budget = parsedBudget.message;
    setProblems(found);
    setMessage(null);
    if (!parsedRate.ok || !parsedBudget.ok) return;
    if (parsedBudget.value !== null && parsedRate.value === null) {
      setProblems({ rate: "Enter the dollar-to-rupee rate before setting a budget." });
      return;
    }
    setBusy(true);
    try {
      const { data, error, response } = await api().PUT("/api/v1/ai/settings", {
        params: { header: { "If-Match": ifMatch(settings.revision) } },
        body: { usd_to_inr: parsedRate.value, default_budget_inr: parsedBudget.value },
      });
      if (data) {
        setSettings(data);
        setRate(data.usd_to_inr ?? "");
        setBudget(data.default_budget_inr ?? "");
        setMessage({ ok: true, text: "Saved. New runs use these numbers." });
      } else if (response.status === 412) {
        setMessage({ ok: false, text: "Someone else changed this. It has been reloaded." });
        setAttempt((n) => n + 1);
      } else {
        setMessage({ ok: false, text: errorMessage(error as never, response.status) });
      }
    } catch {
      setMessage({ ok: false, text: NETWORK });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Rate and budget" className="grid gap-3">
      <div>
        <h2 className="text-lg font-medium">Rate and monthly budget</h2>
        <p className="max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          Providers bill in US dollars; budgets are in rupees. Enter today&apos;s rate to turn
          budgets on. The default budget is each person&apos;s limit per calendar month (India time)
          unless you give someone their own. Leave the budget empty for no limit.
        </p>
      </div>
      {!settings && !message && <p>Loading…</p>}
      {settings && (
        <form
          aria-label="Rate and budget"
          className="grid max-w-xl gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <label className="grid gap-1 text-sm">
            Rupees for one US dollar
            <input
              inputMode="decimal"
              value={rate}
              onChange={(event) => setRate(event.target.value)}
              aria-invalid={problems.rate ? true : undefined}
              className={FIELD}
            />
            {problems.rate && (
              <span role="alert" className="text-red-700 dark:text-red-300">
                {problems.rate}
              </span>
            )}
          </label>
          <label className="grid gap-1 text-sm">
            Default monthly budget per person (rupees)
            <input
              inputMode="decimal"
              value={budget}
              onChange={(event) => setBudget(event.target.value)}
              aria-invalid={problems.budget ? true : undefined}
              className={FIELD}
            />
            {problems.budget && (
              <span role="alert" className="text-red-700 dark:text-red-300">
                {problems.budget}
              </span>
            )}
          </label>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Now: rate {settings.usd_to_inr ?? "not set"}, budget{" "}
            {formatInr(settings.default_budget_inr)}.
            {settings.usd_to_inr === null && " Without a rate, budgets are off."}
          </p>
          <div>
            <button type="submit" disabled={busy} className={PRIMARY}>
              Save
            </button>
          </div>
        </form>
      )}
      {message && (
        <p role={message.ok ? "status" : "alert"} className={message.ok ? OK : ALERT}>
          {message.text}
        </p>
      )}
    </section>
  );
}

const PROBLEM_TEXT: Record<string, string> = {
  MODEL_UNAVAILABLE: "The provider no longer lists this model.",
  MODEL_DISABLED: "This model is turned off.",
};

function OperationsForm({ version }: { version: number }) {
  const [rows, setRows] = useState<OperationRow[] | null>(null);
  const [models, setModels] = useState<Model[]>([]);
  const [problem, setProblem] = useState<string | null>(null);

  const [attempt, setAttempt] = useState(0);
  const reload = () => setAttempt((n) => n + 1);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [ops, list] = await Promise.all([
          api().GET("/api/v1/ai/operations"),
          api().GET("/api/v1/ai/models"),
        ]);
        if (cancelled) return;
        if (ops.data && list.data) {
          setRows(ops.data.data);
          setModels(list.data.data);
          setProblem(null);
        } else {
          const failed = ops.data ? list : ops;
          setProblem(errorMessage(failed.error as never, failed.response.status));
        }
      } catch {
        if (!cancelled) setProblem(NETWORK);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [attempt, version]);

  const usable = models.filter((model) => model.enabled && model.available);

  return (
    <section aria-label="Operations" className="grid gap-3">
      <div>
        <h2 className="text-lg font-medium">What each operation uses</h2>
        <p className="max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          Pick the model each operation uses first, up to two models to fall back on if it fails,
          and whether runs are Now or Economy by default. Faculty can choose differently for one
          run. Only models you turned on above are listed.
        </p>
      </div>
      {problem && (
        <p role="alert" className={ALERT}>
          {problem}
        </p>
      )}
      {!rows && !problem && <p>Loading…</p>}
      {rows && (
        <ul className="grid gap-3">
          {OPERATIONS.map((operation) => {
            const row = rows.find((item) => item.operation === operation);
            return row ? (
              <OperationCard
                key={`${operation}-${row.revision}`}
                row={row}
                usable={usable}
                reload={reload}
              />
            ) : null;
          })}
        </ul>
      )}
    </section>
  );
}

function OperationCard({
  row,
  usable,
  reload,
}: {
  row: OperationRow;
  usable: Model[];
  reload: () => void;
}) {
  const operation: Operation = row.operation;
  const [model, setModel] = useState(row.default_model?.id ?? "");
  const [mode, setMode] = useState<Mode>(row.mode);
  const [first, setFirst] = useState(row.fallbacks[0]?.id ?? "");
  const [second, setSecond] = useState(row.fallbacks[1]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  async function save() {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    const chain = [first, second].filter((id) => id !== "");
    try {
      const { data, error, response } = await api().PUT("/api/v1/ai/operations/{operation}", {
        params: { path: { operation }, header: { "If-Match": ifMatch(row.revision) } },
        body: {
          default_model_id: model === "" ? null : model,
          mode,
          fallback_model_ids: model === "" ? [] : chain,
        },
      });
      if (data) {
        setMessage({ ok: true, text: "Saved." });
        reload();
      } else if (response.status === 412) {
        setMessage({ ok: false, text: "Someone else changed this. It has been reloaded." });
        reload();
      } else {
        setMessage({ ok: false, text: errorMessage(error as never, response.status) });
      }
    } catch {
      setMessage({ ok: false, text: NETWORK });
    } finally {
      setBusy(false);
    }
  }

  const options = (
    <>
      <option value="">None</option>
      {usable.map((item) => (
        <option key={item.id} value={item.id}>
          {item.display_name} ({PROVIDER_LABEL[item.provider]})
        </option>
      ))}
    </>
  );

  return (
    <li className="grid gap-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
      <h3 className="font-medium">{OPERATION_LABEL[operation]}</h3>
      {row.problem && (
        <p role="alert" className={ALERT}>
          {PROBLEM_TEXT[row.problem] ?? "The chosen model cannot be used."} Choose another.
        </p>
      )}
      <form
        aria-label={OPERATION_LABEL[operation]}
        className="grid gap-3 sm:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        <label className="grid gap-1 text-sm">
          First model
          <select
            value={model}
            onChange={(event) => setModel(event.target.value)}
            className={FIELD}
          >
            {options}
          </select>
        </label>
        <label className="grid gap-1 text-sm">
          Default mode
          <select
            value={mode}
            onChange={(event) => setMode(event.target.value as Mode)}
            className={FIELD}
          >
            {(Object.keys(MODE_LABEL) as Mode[]).map((value) => (
              <option key={value} value={value}>
                {MODE_LABEL[value]}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-sm">
          If it fails, try
          <select
            value={first}
            disabled={model === ""}
            onChange={(event) => setFirst(event.target.value)}
            className={FIELD}
          >
            {options}
          </select>
        </label>
        <label className="grid gap-1 text-sm">
          And then
          <select
            value={second}
            disabled={model === "" || first === ""}
            onChange={(event) => setSecond(event.target.value)}
            className={FIELD}
          >
            {options}
          </select>
        </label>
        <div className="sm:col-span-2">
          <button type="submit" disabled={busy} className={PRIMARY}>
            Save
          </button>
        </div>
      </form>
      {message && (
        <p role={message.ok ? "status" : "alert"} className={message.ok ? OK : ALERT}>
          {message.text}
        </p>
      )}
    </li>
  );
}
