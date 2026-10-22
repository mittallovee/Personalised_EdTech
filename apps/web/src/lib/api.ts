import { createApiClient, type ApiClient, type ErrorResponse } from "@qbank/api-client";

let client: ApiClient | undefined;

// Requests for people who are not signed in (or that already handle their own 401). For these a
// 401 means a wrong password, a bad link or "already signed out", never "your sign-in has ended".
// Every other API request, including the signed-in ones under /auth/ (linking Google, unlinking),
// sends the person to the sign-in page on a 401.
const SIGNED_OUT_ENDPOINTS = new Set([
  "/api/v1/auth/login",
  "/api/v1/auth/logout",
  "/api/v1/auth/links/redeem",
  "/api/v1/auth/google/start",
  "/api/v1/auth/google/start-activation",
]);

/**
 * The browser's API client. Created on first use, because it needs `window.location`.
 *
 * Whatever a screen was doing, a 401 means the sign-in has ended (it expired, was revoked, or
 * ended in another tab): go to the sign-in page, so no screen keeps showing a stale console. The
 * requests in `SIGNED_OUT_ENDPOINTS` are left out: for them a 401 is a wrong password or a bad link.
 */
export function api(): ApiClient {
  if (!client) {
    client = createApiClient();
    client.use({
      onResponse({ request, response }) {
        const path = new URL(request.url).pathname;
        if (response.status === 401 && !SIGNED_OUT_ENDPOINTS.has(path)) {
          // Not inside React, so no router here; a full page load also drops whatever the stale
          // screen still held in memory. `replace` rather than `assign`, so the sign-in page takes
          // the console's place in the history and Back cannot bring the old screen (and its data)
          // back from the browser's memory.
          window.location.replace("/login");
        }
      },
    });
  }
  return client;
}

/** A sentence for the user from the API's error envelope (clients never branch on `message`). */
export function errorMessage(error: ErrorResponse | undefined, status: number): string {
  if (status === 429) {
    const wait = error?.error.details["retry_after_seconds"];
    return typeof wait === "number"
      ? `Too many attempts. Please wait ${wait} seconds and try again.`
      : "Too many attempts. Please wait and try again.";
  }
  if (error?.error.message) return error.error.message;
  return "Something went wrong. Please try again.";
}

/**
 * The `If-Match` value for a change based on a revision read earlier: the API's ETag for a
 * resource is its revision as `"rev-<number>"` (style guide §6).
 */
export function ifMatch(revision: number): string {
  return `"rev-${revision}"`;
}
