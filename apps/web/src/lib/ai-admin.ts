import type { components } from "@qbank/api-client";

export type Provider = components["schemas"]["Provider"];
export type Operation = components["schemas"]["Operation"];
export type Mode = components["schemas"]["Mode"];

export const PROVIDERS: Provider[] = ["ANTHROPIC", "OPENAI", "GOOGLE", "OPENROUTER"];

export const PROVIDER_LABEL: Record<Provider, string> = {
  ANTHROPIC: "Anthropic",
  OPENAI: "OpenAI",
  GOOGLE: "Google",
  OPENROUTER: "OpenRouter",
};

export const OPERATIONS: Operation[] = ["TAG", "TRANSLATE", "SOLVE", "VERIFY"];

export const OPERATION_LABEL: Record<Operation, string> = {
  TAG: "Tag a question",
  TRANSLATE: "Translate a question",
  SOLVE: "Solve a question",
  VERIFY: "Verify a question",
};

export const MODE_LABEL: Record<Mode, string> = {
  NOW: "Now (normal price)",
  ECONOMY: "Economy (about half price, done within 24 hours)",
};

/** What a failed refresh of a model list says, in words (the API gives only the kind). */
export const REFRESH_PROBLEM: Record<string, string> = {
  AUTH: "The provider refused the key.",
  RATE_LIMITED: "The provider asked us to slow down. Try again in a minute.",
  TIMEOUT: "The provider did not answer in time.",
  UNAVAILABLE: "The provider could not be reached.",
  BAD_REQUEST: "The provider refused the request.",
  BAD_OUTPUT: "The provider's answer could not be read.",
  TOO_LARGE: "The provider's answer was too large to read.",
  KEY_UNREADABLE: "The stored key could not be opened. Enter it again.",
};

export type Amount = { ok: true; value: string | null } | { ok: false; message: string };

/**
 * A non-negative decimal typed by a person (a price, a rupee amount, a rate). The text is kept as
 * text and sent as text: money is never turned into a floating-point number. The server decides
 * what is allowed; this only catches typing slips early and gives them a sentence.
 */
export function parseAmount(
  text: string,
  options: { maxDecimals: number; max: number; allowEmpty: boolean },
): Amount {
  const typed = text.trim();
  if (typed === "") {
    return options.allowEmpty
      ? { ok: true, value: null }
      : { ok: false, message: "Enter a number." };
  }
  const match = /^(\d+)(?:\.(\d+))?$/.exec(typed);
  if (!match) return { ok: false, message: "Use digits and at most one point, like 12.50." };
  const decimals = match[2] ?? "";
  if (decimals.length > options.maxDecimals) {
    return {
      ok: false,
      message:
        options.maxDecimals === 0
          ? "Use a whole number."
          : `Use at most ${options.maxDecimals} decimal places.`,
    };
  }
  if (Number(typed) > options.max) {
    return { ok: false, message: `Use a number not above ${options.max}.` };
  }
  return { ok: true, value: typed };
}

/** Rupees as text with Indian digit grouping, from the API's exact decimal string. */
export function formatInr(value: string | null | undefined): string {
  if (value === null || value === undefined) return "not set";
  const [whole = "0", fraction] = value.split(".");
  const digits = whole.replace(/^0+(?=\d)/, "");
  const last3 = digits.slice(-3);
  const rest = digits.slice(0, -3);
  const grouped = rest === "" ? last3 : `${rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",")},${last3}`;
  return `₹${grouped}${fraction ? `.${fraction}` : ""}`;
}

/** A price per million tokens, or "unknown" (never a guess). */
export function priceText(value: string | null | undefined): string {
  return value === null || value === undefined ? "unknown" : `$${value}`;
}

/** Where a price came from, in words. */
export function priceSource(source: string): string {
  if (source === "PROVIDER") return "from the provider";
  if (source === "ADMIN") return "set by an admin";
  return "unknown";
}

/**
 * How much of a budget is used, as a whole percent from 0 to 100, for the width of a bar only
 * (the amounts themselves are shown exactly, as the API gave them). ``null`` without a limit.
 */
export function usagePercent(spent: string, limit: string | null): number | null {
  if (limit === null) return null;
  const cap = Number(limit);
  if (!(cap > 0)) return 100;
  return Math.min(100, Math.max(0, Math.round((Number(spent) / cap) * 100)));
}

export const USAGE_STATE_TEXT: Record<string, string> = {
  OK: "Within budget",
  WARNING: "Above 80% of the budget",
  REACHED: "Budget used up",
  NO_LIMIT: "No limit",
  OFF: "Budgets are off (no rate set)",
};
