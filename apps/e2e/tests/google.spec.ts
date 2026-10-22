import { expect, test, type Page, type Route } from "@playwright/test";

import {
  activate,
  createCoaching,
  csrfOf,
  invite,
  person,
  setPassword,
  signedInOwner,
  unique,
} from "./helpers";

/**
 * The Google screens. Google itself cannot be reached from a test browser, and the test stack has
 * no Google client set up, so these tests stand in for the API's answers at the network edge
 * (`page.route`) and check what the screens send and show. The real flow, with a stand-in
 * Google, is covered by the API's integration tests (tests/integration/test_google_*.py).
 */

const FAKE_GOOGLE = "https://accounts.google.test/auth?state=abc";

/** The server says Google is set up. */
async function googleIsOn(page: Page) {
  await page.route("**/api/v1/auth/methods", (route) =>
    route.fulfill({ json: { password: true, google: true } }),
  );
}

/** "Google" is a page of our own, so a click that leaves for it can be seen arriving. */
async function fakeGoogle(page: Page) {
  await page.route("https://accounts.google.test/**", (route) =>
    route.fulfill({ contentType: "text/html", body: "<h1>Fake Google</h1>" }),
  );
}

/** Alerts in the page itself (Next also keeps a hidden route announcer with the alert role). */
function alerts(page: Page) {
  return page.locator("main").getByRole("alert");
}

function error(code: string, message: string, status: number) {
  return {
    status,
    json: { error: { code, message, request_id: null, fields: [], details: {} } },
  };
}

/** Answer the request, and remember what it sent. */
function answering(sent: unknown[], answer: Parameters<Route["fulfill"]>[0]) {
  return (route: Route) => {
    sent.push(route.request().postDataJSON());
    return route.fulfill(answer);
  };
}

test("the sign-in page shows Google only when the server has it set up", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in with Google" })).toHaveCount(0);

  await googleIsOn(page);
  await page.reload();

  await expect(page.getByRole("button", { name: "Sign in with Google" })).toBeVisible();
});

test("Sign in with Google goes to the address the server gives", async ({ page, baseURL }) => {
  await googleIsOn(page);
  await fakeGoogle(page);
  const sent: unknown[] = [];
  await page.route(
    "**/api/v1/auth/google/start",
    answering(sent, { json: { authorization_url: FAKE_GOOGLE } }),
  );
  await page.goto("/login");

  await page.getByRole("button", { name: "Sign in with Google" }).click();

  await expect(page).toHaveURL(FAKE_GOOGLE);
  await expect(page.getByRole("heading", { name: "Fake Google" })).toBeVisible();
  expect(sent).toEqual([{ purpose: "SIGN_IN", return_origin: baseURL }]);
});

test("a refusal from the server is shown, and the page stays", async ({ page }) => {
  await googleIsOn(page);
  await page.route("**/api/v1/auth/google/start", (route) =>
    route.fulfill(error("GOOGLE_DISABLED", "Google sign-in is not turned on.", 404)),
  );
  await page.goto("/login");

  await page.getByRole("button", { name: "Sign in with Google" }).click();

  await expect(alerts(page)).toHaveText("Google sign-in is not turned on.");
  await expect(page).toHaveURL(/\/login$/);
});

test("the page never leaves for an address that is not https", async ({ page }) => {
  await googleIsOn(page);
  await page.route("**/api/v1/auth/google/start", (route) =>
    route.fulfill({ json: { authorization_url: "http://accounts.google.test/auth" } }),
  );
  await page.goto("/login");

  await page.getByRole("button", { name: "Sign in with Google" }).click();

  await expect(alerts(page)).toHaveText("Google sign-in is not available right now.");
  await expect(page).toHaveURL(/\/login$/);
});

test("after a failed Google sign-in the sign-in page explains, once", async ({ page }) => {
  await page.goto("/login?google=failed");

  await expect(alerts(page)).toContainText("could not sign you in with Google");
  await expect(page).toHaveURL(/\/login$/); // removed from the address, so a reload is clean
  await page.reload();
  await expect(alerts(page)).toHaveCount(0);
});

test("the activation page offers Continue with Google and sends the link", async ({
  browser,
  baseURL,
}) => {
  const adminContext = await browser.newContext();
  const { token } = await createCoaching(adminContext.request, baseURL!, `Gact ${unique()}`);
  await adminContext.close();
  const page = await (await browser.newContext()).newPage();
  await googleIsOn(page);
  await fakeGoogle(page);
  const sent: unknown[] = [];
  await page.route(
    "**/api/v1/auth/google/start-activation",
    answering(sent, { json: { authorization_url: FAKE_GOOGLE } }),
  );
  await page.goto(`/activate#${token}`);

  await page.getByRole("button", { name: "Continue with Google instead" }).click();

  await expect(page).toHaveURL(FAKE_GOOGLE);
  expect(sent).toEqual([{ return_origin: baseURL, link_token: token }]);
});

test("the activation page shows no Google button when the server has none", async ({
  browser,
  baseURL,
}) => {
  const adminContext = await browser.newContext();
  const { token } = await createCoaching(adminContext.request, baseURL!, `Gnone ${unique()}`);
  await adminContext.close();
  const page = await (await browser.newContext()).newPage();

  await page.goto(`/activate#${token}`);

  await expect(page.getByRole("button", { name: "Save and sign in" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Google/ })).toHaveCount(0);
});

test("the Profile page says Google is not set up when the server has none", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Gprof ${unique()}`);
  const page = await context.newPage();

  await page.goto("/profile");

  const methods = page.getByRole("list", { name: "Sign-in methods" });
  await expect(methods).toContainText("Password");
  await expect(methods).toContainText("Set.");
  await expect(methods).toContainText("not set up on this server");
  await expect(page.getByRole("form", { name: "Link a Google account" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Profile" })).toBeVisible();
});

test("linking Google asks for the password, shows a wrong one, and goes to Google", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Glink ${unique()}`);
  const page = await context.newPage();
  await googleIsOn(page);
  await fakeGoogle(page);
  const sent: { password: string; return_origin: string }[] = [];
  await page.route("**/api/v1/auth/google/start-link", (route) => {
    const body = route.request().postDataJSON();
    sent.push(body);
    return body.password === "an owner passphrase"
      ? route.fulfill({ json: { authorization_url: FAKE_GOOGLE } })
      : route.fulfill(error("PASSWORD_INCORRECT", "The password is incorrect.", 403));
  });
  await page.goto("/profile");
  const form = page.getByRole("form", { name: "Link a Google account" });

  await form.getByLabel("Your password").fill("wrong password!");
  await form.getByRole("button", { name: "Link Google account" }).click();
  await expect(alerts(page)).toHaveText("The password is incorrect.");
  await expect(page).toHaveURL(/\/profile$/);

  await form.getByLabel("Your password").fill("an owner passphrase");
  await form.getByRole("button", { name: "Link Google account" }).click();

  await expect(page).toHaveURL(FAKE_GOOGLE);
  expect(sent.map((s) => s.password)).toEqual(["wrong password!", "an owner passphrase"]);
  expect(sent[1]?.return_origin).toBe(baseURL);
});

test("the Profile page shows a linked Google account and unlinks it after asking", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Gunlink ${unique()}`);
  const page = await context.newPage();
  await googleIsOn(page);
  let linked = true;
  await page.route("**/api/v1/me/login-methods", (route) =>
    route.fulfill({
      json: {
        password: true,
        google: linked
          ? { linked: true, email: "priya@gmail.example" }
          : { linked: false, email: null },
      },
    }),
  );
  let unlinkRequests = 0;
  await page.route("**/api/v1/auth/google/unlink", (route) => {
    unlinkRequests += 1;
    linked = false;
    return route.fulfill({ status: 204 });
  });
  await page.goto("/profile");
  const methods = page.getByRole("list", { name: "Sign-in methods" });
  await expect(methods).toContainText("priya@gmail.example");

  await page.getByRole("button", { name: "Unlink Google", exact: true }).click();
  expect(unlinkRequests).toBe(0); // it asks first
  await page.getByRole("button", { name: "Cancel" }).click();
  expect(unlinkRequests).toBe(0);
  await page.getByRole("button", { name: "Unlink Google", exact: true }).click();
  await page.getByRole("button", { name: "Unlink Google" }).last().click();

  await expect(page.getByRole("status")).toContainText("Your Google account is unlinked");
  await expect(page.getByRole("form", { name: "Link a Google account" })).toBeVisible();
  expect(unlinkRequests).toBe(1);
});

test("a Google-only account cannot unlink and is told why", async ({ browser, baseURL }) => {
  const { context } = await signedInOwner(browser, baseURL!, `Gonly ${unique()}`);
  const page = await context.newPage();
  await googleIsOn(page);
  await page.route("**/api/v1/me/login-methods", (route) =>
    route.fulfill({
      json: { password: false, google: { linked: true, email: null } },
    }),
  );

  await page.goto("/profile");

  const methods = page.getByRole("list", { name: "Sign-in methods" });
  await expect(methods).toContainText("Not set. You sign in with Google.");
  await expect(methods).toContainText("Google is your only way in");
  await expect(page.getByRole("button", { name: /Unlink/ })).toHaveCount(0);
});

test("the Profile page reports the result Google's callback leaves, once", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Gresult ${unique()}`);
  const page = await context.newPage();

  await page.goto("/profile?google=linked");
  await expect(page.getByRole("status")).toContainText("Your Google account is linked");
  await expect(page).toHaveURL(/\/profile$/);

  await page.goto("/profile?google=failed");
  await expect(alerts(page)).toContainText("could not link your Google account");
  await page.reload();
  await expect(alerts(page)).toHaveCount(0);
});

test("a password-reset link is not offered Google, and still resets the password", async ({
  browser,
  baseURL,
}) => {
  // Codex review on PR #27: /activate serves both kinds of link, but Google only activates.
  const { context } = await signedInOwner(browser, baseURL!, `Greset ${unique()}`);
  const owner = await context.newPage();
  await owner.goto("/admin/users");
  const activationLink = await invite(owner, "Anita Rao", `anita-${unique()}@example.com`);
  await activate(browser, activationLink, "Anita Rao");
  await owner.reload(); // she is active now, so the card offers a reset link
  await person(owner, "Anita Rao").getByRole("button", { name: "Password-reset link" }).click();
  const notice = owner.getByRole("status", { name: "Password-reset link for Anita Rao" });
  const resetLink = await notice.getByLabel("Link").inputValue();
  expect(resetLink).toMatch(/\/activate#[A-Za-z0-9_-]+\.reset$/);
  const visitor = await (await browser.newContext()).newPage();
  await googleIsOn(visitor);

  await visitor.goto(resetLink);

  await expect(visitor.getByRole("button", { name: "Save and sign in" })).toBeVisible();
  await expect(visitor.getByRole("button", { name: /Google/ })).toHaveCount(0);
  await setPassword(visitor, "a brand new passphrase");
  await expect(visitor.getByRole("heading", { name: "Welcome, Anita Rao" })).toBeVisible();
});

test("an activation link is still offered Google, and its address has no marker", async ({
  browser,
  baseURL,
}) => {
  const { context } = await signedInOwner(browser, baseURL!, `Gmark ${unique()}`);
  const owner = await context.newPage();
  await owner.goto("/admin/users");

  const link = await invite(owner, "Anita Rao", `anita-${unique()}@example.com`);

  expect(link).toMatch(/\/activate#[A-Za-z0-9_-]+$/);
  const visitor = await (await browser.newContext()).newPage();
  await googleIsOn(visitor);
  await visitor.goto(link);
  await expect(visitor.getByRole("button", { name: "Continue with Google instead" })).toBeVisible();
});

test("linking or unlinking after the session has ended sends you to sign in", async ({
  browser,
  baseURL,
}) => {
  // Codex review on PR #27: these two signed-in actions live under /auth/, but a 401 on them means
  // the sign-in has ended, not "wrong password".
  for (const action of ["link", "unlink"] as const) {
    const { context } = await signedInOwner(browser, baseURL!, `Gended ${action} ${unique()}`);
    const page = await context.newPage();
    await googleIsOn(page);
    if (action === "unlink") {
      await page.route("**/api/v1/me/login-methods", (route) =>
        route.fulfill({
          json: { password: true, google: { linked: true, email: "me@gmail.example" } },
        }),
      );
    }
    await page.goto("/profile");
    await expect(page.getByRole("list", { name: "Sign-in methods" })).toBeVisible();
    // The same sign-in ends elsewhere (another tab, or it expired).
    const ended = await context.request.post("/api/v1/auth/logout", {
      headers: { Origin: baseURL!, "X-CSRF-Token": await csrfOf(context) },
    });
    expect(ended.ok()).toBe(true);

    if (action === "link") {
      const form = page.getByRole("form", { name: "Link a Google account" });
      await form.getByLabel("Your password").fill("an owner passphrase");
      await form.getByRole("button", { name: "Link Google account" }).click();
    } else {
      await page.getByRole("button", { name: "Unlink Google", exact: true }).click();
      await page.getByRole("button", { name: "Unlink Google" }).last().click();
    }

    await expect(page).toHaveURL(/\/login$/);
  }
});

test("the Profile page does not claim Google is off while it is still finding out", async ({
  browser,
  baseURL,
}) => {
  // Codex review on PR #27: "not set up" must only be said when the server really said so.
  const { context } = await signedInOwner(browser, baseURL!, `Gwait ${unique()}`);
  const page = await context.newPage();
  let calls = 0;
  await page.route("**/api/v1/auth/methods", async (route) => {
    calls += 1;
    if (calls === 1) {
      await new Promise((resolve) => setTimeout(resolve, 1500)); // a slow answer...
      return route.fulfill(error("INTERNAL_ERROR", "Something went wrong.", 500)); // ...then a failure
    }
    return route.fulfill({ json: { password: true, google: true } });
  });

  await page.goto("/profile");
  const methods = page.getByRole("list", { name: "Sign-in methods" });
  await expect(methods).toBeVisible();
  await expect(methods).not.toContainText("not set up on this server"); // still waiting
  await expect(methods).toContainText("Could not check whether Google sign-in is available");
  await expect(methods).not.toContainText("not set up on this server"); // a failure is not "off"

  await methods.getByRole("button", { name: "Try again" }).click();

  await expect(page.getByRole("form", { name: "Link a Google account" })).toBeVisible();
});

test("while one way of activating is under way the other cannot be started", async ({
  browser,
  baseURL,
}) => {
  // Codex review on PR #27: both use the same one-time link, so they must not run together.
  const adminContext = await browser.newContext();
  const { token } = await createCoaching(adminContext.request, baseURL!, `Gbusy ${unique()}`);
  await adminContext.close();
  const page = await (await browser.newContext()).newPage();
  await googleIsOn(page);
  await page.route("**/api/v1/auth/google/start-activation", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    return route.fulfill({ json: { authorization_url: FAKE_GOOGLE } });
  });
  await fakeGoogle(page);
  await page.goto(`/activate#${token}`);

  await page.getByRole("button", { name: "Continue with Google instead" }).click();

  await expect(page.getByRole("button", { name: "Save and sign in" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Going to Google…" })).toBeDisabled();
});

test("while Google sign-in is under way the password button waits", async ({ page }) => {
  await googleIsOn(page);
  await page.route("**/api/v1/auth/google/start", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1500));
    return route.fulfill({ json: { authorization_url: FAKE_GOOGLE } });
  });
  await fakeGoogle(page);
  await page.goto("/login");

  await page.getByRole("button", { name: "Sign in with Google" }).click();

  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeDisabled();
});

test("after unlinking, a failed refresh does not leave Google shown as linked", async ({
  browser,
  baseURL,
}) => {
  // Codex review on PR #27: the page said "unlinked" while still showing the old state.
  const { context } = await signedInOwner(browser, baseURL!, `Gstale ${unique()}`);
  const page = await context.newPage();
  await googleIsOn(page);
  let reads = 0;
  await page.route("**/api/v1/me/login-methods", (route) => {
    reads += 1;
    return reads === 1
      ? route.fulfill({
          json: { password: true, google: { linked: true, email: "me@gmail.example" } },
        })
      : route.fulfill(error("INTERNAL_ERROR", "Something went wrong.", 500)); // the refresh fails
  });
  await page.route("**/api/v1/auth/google/unlink", (route) => route.fulfill({ status: 204 }));
  await page.goto("/profile");
  await expect(page.getByRole("list", { name: "Sign-in methods" })).toContainText(
    "me@gmail.example",
  );

  await page.getByRole("button", { name: "Unlink Google", exact: true }).click();
  await page.getByRole("button", { name: "Unlink Google" }).last().click();

  await expect(page.getByRole("status")).toContainText("Your Google account is unlinked");
  const methods = page.getByRole("list", { name: "Sign-in methods" });
  await expect(methods).not.toContainText("me@gmail.example");
  await expect(page.getByRole("button", { name: /Unlink/ })).toHaveCount(0);
});

test("after a failed Google activation the person is told to open their link again", async ({
  page,
}) => {
  // Codex review on PR #27: the sign-in page's advice (use your password, link on Profile) does
  // not fit someone who is still activating and has no password.
  await page.goto("/activate?google=failed");

  await expect(alerts(page)).toContainText("could not finish setting up your account with Google");
  await expect(alerts(page)).toContainText("Open the link your coaching admin sent you again");
  await expect(page).toHaveURL(/\/activate$/); // removed from the address, so a reload is clean
});

test("a link that Google cannot use says what to do, and the password form stays", async ({
  browser,
  baseURL,
}) => {
  const adminContext = await browser.newContext();
  const { token } = await createCoaching(adminContext.request, baseURL!, `Ginval ${unique()}`);
  await adminContext.close();
  const page = await (await browser.newContext()).newPage();
  await googleIsOn(page);
  await page.route("**/api/v1/auth/google/start-activation", (route) =>
    route.fulfill(error("LINK_INVALID", "This link is not valid any more.", 401)),
  );
  await page.goto(`/activate#${token}`);

  await page.getByRole("button", { name: "Continue with Google instead" }).click();

  await expect(alerts(page)).toContainText("password-reset link");
  await expect(alerts(page)).toContainText("ask your coaching admin for a new link");
  await expect(page).not.toHaveURL(/\/login/);
  await expect(page.getByRole("button", { name: "Save and sign in" })).toBeEnabled();
});

test("a link that failed because the person was signed out is explained on the sign-in page", async ({
  page,
}) => {
  // Codex review on PR #27: the Profile page would bounce a signed-out person and lose the message.
  await page.goto("/login?google=link-failed");

  await expect(alerts(page)).toContainText("could not link your Google account");
  await expect(alerts(page)).toContainText("signed out");
  await expect(alerts(page)).toContainText("Sign in with your password");
  await expect(page).toHaveURL(/\/login$/);
  await page.reload();
  await expect(alerts(page)).toHaveCount(0);
});
