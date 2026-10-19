import { describe, expect, it } from "vitest";

import { createApiClient, readCookie } from "../src/index";

function recordingFetch(status = 200, body: unknown = {}) {
  const requests: Request[] = [];
  const fetch = async (input: Request) => {
    requests.push(input);
    return new Response(status === 204 ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  };
  return { fetch: fetch as typeof globalThis.fetch, requests };
}

describe("readCookie", () => {
  it("finds a cookie among others and decodes it", () => {
    expect(readCookie("a=1; qb_csrf=abc%2Bdef; b=2", "qb_csrf")).toBe("abc+def");
  });

  it("returns undefined when the cookie is missing", () => {
    expect(readCookie("a=1", "qb_csrf")).toBeUndefined();
    expect(readCookie("", "qb_csrf")).toBeUndefined();
  });
});

describe("createApiClient", () => {
  const options = { baseUrl: "http://web.test", readCookies: () => "qb_csrf=token-123" };

  it("sends the CSRF header on changes", async () => {
    const { fetch, requests } = recordingFetch(204);
    const api = createApiClient({ ...options, fetch });

    await api.POST("/api/v1/auth/logout");

    expect(requests[0]?.url).toBe("http://web.test/api/v1/auth/logout");
    expect(requests[0]?.headers.get("X-CSRF-Token")).toBe("token-123");
  });

  it("does not send the CSRF header on reads", async () => {
    const { fetch, requests } = recordingFetch(200, { user_id: "u" });
    const api = createApiClient({ ...options, fetch });

    await api.GET("/api/v1/me");

    expect(requests[0]?.headers.has("X-CSRF-Token")).toBe(false);
  });

  it("returns the error envelope on failures", async () => {
    const envelope = {
      error: {
        code: "UNAUTHENTICATED",
        message: "Please sign in.",
        request_id: "r",
        fields: [],
        details: {},
      },
    };
    const { fetch } = recordingFetch(401, envelope);
    const api = createApiClient({ ...options, fetch });

    const { data, error, response } = await api.GET("/api/v1/me");

    expect(data).toBeUndefined();
    expect(response.status).toBe(401);
    expect(error?.error.code).toBe("UNAUTHENTICATED");
  });
});
