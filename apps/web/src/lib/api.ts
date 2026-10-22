import { createApiClient, type ApiClient, type ErrorResponse } from "@qbank/api-client";

let client: ApiClient | undefined;

/**
 * The browser's API client. Created on first use, because it needs `window.location`.
 *
 * Whatever a screen was doing, a 401 means the sign-in has ended (it expired, was revoked, or
 * ended in another tab): go to the sign-in page, so no screen keeps showing a stale console. The
 * sign-in and link requests are left out: for them a 401 is a wrong password or a bad link.
 */
export function api(): ApiClient {
  if (!client) {
    client = createApiClient();
    client.use({
      onResponse({ request, response }) {
        const path = new URL(request.url).pathname;
        if (response.status === 401 && !path.startsWith("/api/v1/auth/")) {
          // Not inside React, so no router here; a full page load also drops whatever the stale
          // screen still held in memory.
          // eslint-disable-next-line @next/next/no-location-assign-relative-destination
          window.location.assign("/login");
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
