"use client";

import type { components } from "@qbank/api-client";
import { useEffect, useRef, useState } from "react";

import { api, errorMessage, ifMatch } from "@/lib/api";
import {
  PROVIDERS,
  PROVIDER_LABEL,
  REFRESH_PROBLEM,
  parseAmount,
  priceSource,
  priceText,
  type Provider,
} from "@/lib/ai-admin";
import { NETWORK } from "@/lib/use-catalogue";

type Models = components["schemas"]["ModelsOut"];
type Model = components["schemas"]["ModelOut"];
type ProviderState = components["schemas"]["ProviderStateOut"];

const ALERT =
  "rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300";
const OK =
  "rounded-md bg-green-50 px-3 py-2 text-sm text-green-800 dark:bg-green-950 dark:text-green-200";
const FIELD =
  "w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950";
const BUTTON =
  "rounded-md border border-zinc-300 px-3 py-1 text-sm disabled:opacity-60 dark:border-zinc-700";
const PRIMARY =
  "rounded-md bg-zinc-900 px-3 py-1 text-sm text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900";

/**
 * The models each provider offers this coaching (H-03, H-17): refresh the list from the provider,
 * turn models on for faculty, and add the facts the provider does not give (a price, whether batch
 * is offered). A price that nobody knows is shown as unknown, never guessed. `version` changes when
 * a key was saved or removed, so the list is read again; `onChanged` tells the page when this list
 * changed, so "What each operation uses" offers the models just turned on.
 */
export function AiModelsSection({
  version,
  onChanged,
}: {
  version: number;
  /** The list of models changed (one was turned on or off, a price changed, a refresh arrived):
   *  the sections that offer these models are read again. */
  onChanged: () => void;
}) {
  const [models, setModels] = useState<Models | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const reload = () => {
    setAttempt((n) => n + 1);
    onChanged();
  };

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const { data, error, response } = await api().GET("/api/v1/ai/models");
        if (cancelled) return;
        if (data) {
          setModels(data);
          setProblem(null);
        } else {
          setProblem(
            response.status === 403
              ? "Only the Owner and admins may see or change the models."
              : errorMessage(error as never, response.status),
          );
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

  return (
    <section aria-label="Models" className="grid gap-3">
      <div>
        <h2 className="text-lg font-medium">Models</h2>
        <p className="max-w-2xl text-sm text-zinc-600 dark:text-zinc-400">
          Refresh a provider&apos;s list with your key, then turn on the models faculty may use.
          Where the provider gives no price, add it yourself: a run on a model with no price is
          allowed but its cost is shown as unknown.
        </p>
      </div>
      {problem && (
        <p role="alert" className={ALERT}>
          {problem}
        </p>
      )}
      {!models && !problem && <p>Loading…</p>}
      {models &&
        PROVIDERS.map((provider) => (
          <ProviderBlock
            key={provider}
            provider={provider}
            state={models.providers.find((item) => item.provider === provider)}
            models={models.data.filter((model) => model.provider === provider)}
            reload={reload}
          />
        ))}
    </section>
  );
}

function ProviderBlock({
  provider,
  state,
  models,
  reload,
}: {
  provider: Provider;
  state: ProviderState | undefined;
  models: Model[];
  reload: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);
  const timers = useRef<number[]>([]);
  const label = PROVIDER_LABEL[provider];

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach((id) => window.clearTimeout(id));
  }, []);

  async function refresh() {
    if (busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const { error, response } = await api().POST("/api/v1/ai/models/refresh", {
        body: { provider },
      });
      if (response.status === 202) {
        setMessage({ ok: true, text: `Asking ${label} for its models…` });
        // The list is fetched in the background; look again a few times instead of making the
        // admin press a button.
        for (const wait of [3000, 8000, 20000]) {
          timers.current.push(window.setTimeout(reload, wait));
        }
        timers.current.push(window.setTimeout(() => setMessage(null), 21000));
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
    <div className="grid gap-3 rounded-md border border-zinc-200 p-4 dark:border-zinc-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium">{label}</h3>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={busy || !state?.configured}
          className={BUTTON}
          title={state?.configured ? undefined : "Store a key for this provider first"}
        >
          Refresh the list
        </button>
      </div>
      {!state?.configured && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Store a key above to read this provider&apos;s models.
        </p>
      )}
      {state?.last_refreshed_at && (
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Last read {new Date(state.last_refreshed_at).toLocaleString()}.
        </p>
      )}
      {state?.last_error && (
        <p role="alert" className={ALERT}>
          The last refresh failed. {REFRESH_PROBLEM[state.last_error] ?? "Try again."}
        </p>
      )}
      {message && (
        <p role={message.ok ? "status" : "alert"} className={message.ok ? OK : ALERT}>
          {message.text}
        </p>
      )}
      {models.length === 0 && state?.configured && (
        <p className="text-sm">No models yet. Refresh the list.</p>
      )}
      <ul className="grid gap-2">
        {models.map((model) => (
          <ModelRow key={`${model.id}-${model.revision}`} model={model} reload={reload} />
        ))}
      </ul>
    </div>
  );
}

function ModelRow({ model, reload }: { model: Model; reload: () => void }) {
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [priceIn, setPriceIn] = useState(model.overlay.price_in ?? "");
  const [priceOut, setPriceOut] = useState(model.overlay.price_out ?? "");
  const [batch, setBatch] = useState(model.overlay.batch_supported === true);
  const [vision, setVision] = useState(model.overlay.supports_vision === true);
  const [discount, setDiscount] = useState(model.overlay.batch_discount ?? "");
  const [problems, setProblems] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  async function patch(body: components["schemas"]["UpdateModel"]) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const { error: failure, response } = await api().PATCH("/api/v1/ai/models/{model_id}", {
        params: { path: { model_id: model.id }, header: { "If-Match": ifMatch(model.revision) } },
        body,
      });
      if (response.ok) {
        setEditing(false);
        reload();
      } else if (response.status === 412) {
        setError("Someone else changed this model. The list has been reloaded.");
        reload();
      } else {
        setError(errorMessage(failure as never, response.status));
      }
    } catch {
      setError(NETWORK);
    } finally {
      setBusy(false);
    }
  }

  async function saveFacts() {
    const found: Record<string, string> = {};
    const price = { maxDecimals: 6, max: 100000, allowEmpty: true };
    const parsedIn = parseAmount(priceIn, price);
    const parsedOut = parseAmount(priceOut, price);
    const parsedDiscount = parseAmount(discount, { maxDecimals: 4, max: 1, allowEmpty: true });
    if (!parsedIn.ok) found.price_in = parsedIn.message;
    if (!parsedOut.ok) found.price_out = parsedOut.message;
    if (!parsedDiscount.ok) found.discount = parsedDiscount.message;
    else if (parsedDiscount.value !== null && Number(parsedDiscount.value) === 0)
      found.discount = "A discount must be above 0 (0.5 means half price).";
    setProblems(found);
    if (!parsedIn.ok || !parsedOut.ok || !parsedDiscount.ok || Object.keys(found).length > 0)
      return;
    await patch({
      overlay: {
        price_in: parsedIn.value,
        price_out: parsedOut.value,
        batch_supported: batch ? true : null,
        supports_vision: vision ? true : null,
        batch_discount: parsedDiscount.value,
      },
    });
  }

  return (
    <li className="grid gap-2 rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-medium">{model.display_name}</p>
          <p className="text-xs text-zinc-600 dark:text-zinc-400">{model.model_id}</p>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={model.enabled}
            disabled={busy || !model.available}
            onChange={(event) => void patch({ enabled: event.target.checked })}
          />
          {`Offer ${model.display_name}`}
        </label>
      </div>
      {!model.available && (
        <p className="text-sm text-amber-700 dark:text-amber-400">
          The provider no longer lists this model.
        </p>
      )}
      <p className="text-sm text-zinc-700 dark:text-zinc-300">
        Price per million tokens: in {priceText(model.price_in_per_mtok)}, out{" "}
        {priceText(model.price_out_per_mtok)} ({priceSource(model.price_source)}).{" "}
        {model.batch_supported
          ? `Economy runs are on${model.batch_discount ? ` (discount ${model.batch_discount})` : ""}.`
          : "Economy runs are not offered."}{" "}
        {model.supports_json === false && "This model cannot give structured answers."}
      </p>
      {error && (
        <p role="alert" className={ALERT}>
          {error}
        </p>
      )}
      {editing ? (
        <form
          aria-label={`Facts for ${model.display_name}`}
          className="grid gap-3 sm:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            void saveFacts();
          }}
        >
          <Amount
            label="Price in (dollars per million tokens)"
            value={priceIn}
            onChange={setPriceIn}
            problem={problems.price_in}
          />
          <Amount
            label="Price out (dollars per million tokens)"
            value={priceOut}
            onChange={setPriceOut}
            problem={problems.price_out}
          />
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input
              type="checkbox"
              checked={batch}
              onChange={(event) => setBatch(event.target.checked)}
            />
            This model offers Economy (batch) runs
          </label>
          <label className="flex items-center gap-2 text-sm sm:col-span-2">
            <input
              type="checkbox"
              checked={vision}
              onChange={(event) => setVision(event.target.checked)}
            />
            This model reads pictures (needed to read uploaded papers)
          </label>
          <Amount
            label="Batch discount (0.5 means half price)"
            value={discount}
            onChange={setDiscount}
            problem={problems.discount}
          />
          <p className="text-xs text-zinc-600 sm:col-span-2 dark:text-zinc-400">
            Leave a box empty to use what the provider says. Economy also needs a known price and a
            provider that can find a batch again, which today means OpenAI and Google.
          </p>
          <div className="flex gap-2 sm:col-span-2">
            <button type="submit" disabled={busy} className={PRIMARY}>
              Save
            </button>
            <button type="button" onClick={() => setEditing(false)} className={BUTTON}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div>
          <button type="button" onClick={() => setEditing(true)} className={BUTTON}>
            Prices and Economy
          </button>
        </div>
      )}
    </li>
  );
}

function Amount({
  label,
  value,
  onChange,
  problem,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  problem: string | undefined;
}) {
  return (
    <label className="grid gap-1 text-sm">
      {label}
      <input
        inputMode="decimal"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={problem ? true : undefined}
        className={FIELD}
      />
      {problem && (
        <span role="alert" className="text-red-700 dark:text-red-300">
          {problem}
        </span>
      )}
    </label>
  );
}
