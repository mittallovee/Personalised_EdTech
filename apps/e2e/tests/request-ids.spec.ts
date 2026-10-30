import { expect, test } from "@playwright/test";

// K-06 (ADR-0019): a problem can be followed from the browser through the web server into the API
// by one request ID. The web server makes the ID when the caller sent none and the API echoes it.

test("a call to the API carries a request ID made by the web server", async ({ request }) => {
  const made = await request.get("/health/live");
  expect(made.headers()["x-request-id"]).toMatch(/^web_[0-9a-f]{32}$/);

  const kept = await request.get("/health/live", { headers: { "X-Request-ID": "e2e-trace-me" } });
  expect(kept.headers()["x-request-id"]).toBe("e2e-trace-me");

  const replaced = await request.get("/health/live", { headers: { "X-Request-ID": "not ok!" } });
  expect(replaced.headers()["x-request-id"]).toMatch(/^web_[0-9a-f]{32}$/);
});
