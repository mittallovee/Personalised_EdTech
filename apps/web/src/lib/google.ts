"use client";

import { useEffect, useState } from "react";

import type { ErrorResponse } from "@qbank/api-client";

import { api, errorMessage } from "@/lib/api";

const NETWORK = "Cannot reach the server. Check your connection and try again.";

export interface AuthMethods {
  password: boolean;
  /** True only when the server has said Google is set up; false while loading, on failure, or off. */
  google: boolean;
  /** Whether `google` is the server's answer yet: pages that explain "off" must wait for "ready". */
  status: "loading" | "ready" | "failed";
  retry: () => void;
}

/**
 * Which ways of signing in this server offers (`GET /auth/methods`). Google is hidden until the
 * server says it is set up; until the answer arrives, or if it cannot be had, only the password is
 * shown, which always works. `status` tells a page whether `google: false` is the server's answer
 * or just "not known yet".
 */
export function useAuthMethods(): AuthMethods {
  const [methods, setMethods] = useState({ password: true, google: false });
  const [status, setStatus] = useState<AuthMethods["status"]>("loading");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let cancelled = false;
    api()
      .GET("/api/v1/auth/methods")
      .then(({ data }) => {
        if (cancelled) return;
        if (data) {
          setMethods(data);
          setStatus("ready");
        } else {
          setStatus("failed");
        }
      })
      .catch(() => {
        if (!cancelled) setStatus("failed");
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);
  function retry() {
    setStatus("loading");
    setAttempt((n) => n + 1);
  }
  return { ...methods, status, retry };
}

/**
 * Send the browser to Google, using the address a "start" request returned. Resolves to a message
 * for the person if that was not possible; on success the page is left, so nothing more is shown.
 */
export async function goToGoogle(
  request: () => Promise<{
    data?: { authorization_url: string };
    error?: ErrorResponse;
    response: Response;
  }>,
): Promise<string | null> {
  try {
    const { data, error, response } = await request();
    if (error?.error.code === "LINK_INVALID") {
      // Only activating can say this: the link is spent or expired, or it is a password-reset link,
      // which Google cannot use. The password form on the same page still works for a reset link.
      return "Google cannot use this link. If it is a password-reset link, set a new password below; otherwise ask your coaching admin for a new link.";
    }
    if (!data) return errorMessage(error, response.status);
    // Only ever leave for an https address, whatever came back.
    if (new URL(data.authorization_url).protocol !== "https:") {
      return "Google sign-in is not available right now.";
    }
    window.location.assign(data.authorization_url);
    return null;
  } catch {
    return NETWORK;
  }
}

/**
 * The `?google=...` result Google's callback leaves in the address bar. It is read once and
 * removed, so a reload or a copied address does not repeat the message.
 */
export type GoogleResult = "linked" | "failed" | "link-failed";

export function useGoogleResult(): GoogleResult | null {
  const [result, setResult] = useState<GoogleResult | null>(null);
  useEffect(() => {
    const value = new URLSearchParams(window.location.search).get("google");
    if (value === "linked" || value === "failed" || value === "link-failed") {
      window.history.replaceState(null, "", window.location.pathname);
      // Reading the address bar is only possible in the browser, after the first render.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setResult(value);
    }
  }, []);
  return result;
}
