/**
 * Typed client for the Question Bank API (`/api/v1`), built from the committed contract.
 *
 * Every app uses this instead of hand-written fetch calls, so a contract change shows up as a
 * type error. In the browser it talks to the same origin (the web app forwards `/api/*` to the API)
 * and the session cookie travels automatically; on every change it adds the CSRF header from the
 * readable `qb_csrf` cookie, as the API requires (style guide §7).
 */
import createClient, { type Middleware } from "openapi-fetch";

import type { components, paths } from "./schema";

export type { components, paths } from "./schema";
export type ErrorResponse = components["schemas"]["ErrorResponse"];
export type Me = components["schemas"]["Me"];

export const CSRF_COOKIE = "qb_csrf";
export const CSRF_HEADER = "X-CSRF-Token";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS"]);

/** Value of one cookie from a `document.cookie`-style string, or undefined. */
export function readCookie(cookies: string, name: string): string | undefined {
  for (const part of cookies.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return undefined;
}

/** Adds the X-CSRF-Token header to changes (POST/PUT/PATCH/DELETE). */
export function csrfHeader(readCookies: () => string): Middleware {
  return {
    onRequest({ request }) {
      if (SAFE_METHODS.has(request.method)) return request;
      const token = readCookie(readCookies(), CSRF_COOKIE);
      if (token) request.headers.set(CSRF_HEADER, token);
      return request;
    },
  };
}

export interface ApiClientOptions {
  /** Where the API is; defaults to the page's own origin (the web app's proxy). */
  baseUrl?: string;
  /** Where to read cookies from; defaults to `document.cookie`. */
  readCookies?: () => string;
  fetch?: typeof globalThis.fetch;
}

export function createApiClient(options: ApiClientOptions = {}) {
  const client = createClient<paths>({
    baseUrl: options.baseUrl ?? globalThis.location?.origin ?? "",
    credentials: "same-origin",
    ...(options.fetch ? { fetch: options.fetch } : {}),
  });
  client.use(csrfHeader(options.readCookies ?? (() => globalThis.document?.cookie ?? "")));
  return client;
}

export type ApiClient = ReturnType<typeof createApiClient>;
