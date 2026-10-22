import {
  expect,
  type APIRequestContext,
  type Browser,
  type BrowserContext,
  type Page,
} from "@playwright/test";

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

/** Fill in the activation page and save. */
export async function setPassword(page: Page, password: string, repeat = password): Promise<void> {
  await page.fill('input[name="password"]', password);
  await page.fill('input[name="repeat"]', repeat);
  await page.click('button[type="submit"]');
}

/**
 * A new coaching whose Owner has already activated (through the API, to keep the test short;
 * activation.spec.ts covers the screen). Returns a browser context signed in as the Owner.
 */
export async function signedInOwner(
  browser: Browser,
  baseURL: string,
  displayName: string,
): Promise<{ context: BrowserContext; ownerName: string }> {
  const adminContext = await browser.newContext();
  const { token, ownerName } = await createCoaching(adminContext.request, baseURL, displayName);
  await adminContext.close();
  const context = await browser.newContext();
  const redeemed = await context.request.post("/api/v1/auth/links/redeem", {
    headers: { Origin: baseURL },
    data: { token, password: "an owner passphrase" },
  });
  if (!redeemed.ok()) throw new Error(`activating the Owner failed: HTTP ${redeemed.status()}`);
  return { context, ownerName };
}

/** Invite someone on the Users & grants screen; returns the activation link shown once. */
export async function invite(
  page: Page,
  name: string,
  email: string,
  role: "FACULTY" | "ADMIN" = "FACULTY",
): Promise<string> {
  await page.fill('input[name="display_name"]', name);
  await page.fill('input[name="email"]', email);
  await page.selectOption('select[name="role"]', role);
  await page.getByRole("button", { name: "Invite and make link" }).click();
  const notice = page.getByRole("status", { name: `Activation link for ${name}` });
  await expect(notice).toBeVisible();
  const link = await notice.getByLabel("Link").inputValue();
  expect(link).toContain("/activate#");
  return link;
}

/** One person's card in the Members list, found by their email or name. */
export function person(page: Page, text: string) {
  return page
    .getByRole("list", { name: "Members" })
    .getByRole("listitem")
    .filter({ hasText: text });
}

/** Open an activation link in a browser of its own and set a password; returns that browser's page. */
export async function activate(browser: Browser, link: string, name: string): Promise<Page> {
  const page = await (await browser.newContext()).newPage();
  await page.goto(link);
  await setPassword(page, "a long enough passphrase");
  await expect(page.getByRole("heading", { name: `Welcome, ${name}` })).toBeVisible();
  return page;
}

/** The CSRF token the API gave this browser at sign-in (changes must send it back). */
export async function csrfOf(context: BrowserContext): Promise<string> {
  const cookie = (await context.cookies()).find((c) => c.name === "qb_csrf");
  if (!cookie) throw new Error("not signed in: no CSRF cookie");
  return decodeURIComponent(cookie.value);
}

/** A browser signed in as the platform admin, through the API (sign-in has its own tests). */
export async function platformAdminContext(
  browser: Browser,
  baseURL: string,
): Promise<BrowserContext> {
  const context = await browser.newContext();
  const login = await context.request.post("/api/v1/auth/login", {
    headers: { Origin: baseURL },
    data: admin,
  });
  if (!login.ok()) throw new Error(`admin sign-in failed: HTTP ${login.status()}`);
  return context;
}

/** The platform admin acting inside a coaching (A-06), through the API. */
export async function actingPlatformAdmin(
  browser: Browser,
  baseURL: string,
  organizationId: string,
): Promise<BrowserContext> {
  const context = await platformAdminContext(browser, baseURL);
  const acted = await context.request.post("/api/v1/platform/acting-organization", {
    headers: { Origin: baseURL, "X-CSRF-Token": await csrfOf(context) },
    data: { organization_id: organizationId },
  });
  if (acted.status() !== 204) throw new Error(`acting in the coaching failed: ${acted.status()}`);
  return context;
}

/** One coaching's card on the Coachings screen, found by its name. */
export function coaching(page: Page, name: string) {
  return page
    .getByRole("list", { name: "Coachings" })
    .getByRole("listitem")
    .filter({ hasText: name });
}
