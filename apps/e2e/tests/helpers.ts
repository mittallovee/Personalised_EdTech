import type { APIRequestContext } from "@playwright/test";

/** The platform admin the tests sign in as (created with `qbank create-platform-admin`). */
export const admin = {
  email: process.env.E2E_ADMIN_EMAIL ?? "owner@example.com",
  password: process.env.E2E_ADMIN_PASSWORD ?? "e2e-password-123",
};

/** A value that is different on every run, so tests never collide with older data. */
export function unique(): string {
  return `${Date.now()}-${Math.floor(Math.random() * 1000)}`;
}

/**
 * Create a coaching through the API as the platform admin (the console screens come later in M2)
 * and return its Owner's activation token. Same-origin requests, as the web app sends them.
 */
export async function createCoaching(
  request: APIRequestContext,
  baseURL: string,
  displayName: string,
): Promise<{ token: string; ownerName: string }> {
  const origin = { Origin: baseURL };
  const login = await request.post("/api/v1/auth/login", {
    headers: origin,
    data: admin,
  });
  if (!login.ok()) throw new Error(`admin sign-in failed: HTTP ${login.status()}`);
  const { csrf_token: csrf } = (await login.json()) as { csrf_token: string };

  const ownerName = "Priya Sharma";
  const created = await request.post("/api/v1/platform/organizations", {
    headers: { ...origin, "X-CSRF-Token": csrf },
    data: {
      display_name: displayName,
      timezone: "Asia/Kolkata",
      owner: {
        email: `priya-${unique()}@example.com`,
        display_name: ownerName,
      },
    },
  });
  if (created.status() !== 201) {
    throw new Error(`creating the coaching failed: HTTP ${created.status()}`);
  }
  const body = (await created.json()) as { activation: { token: string } };
  return { token: body.activation.token, ownerName };
}
