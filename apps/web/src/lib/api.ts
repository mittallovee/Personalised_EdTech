import { createApiClient, type ApiClient, type ErrorResponse } from "@qbank/api-client";

let client: ApiClient | undefined;

/** The browser's API client. Created on first use, because it needs `window.location`. */
export function api(): ApiClient {
  client ??= createApiClient();
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
