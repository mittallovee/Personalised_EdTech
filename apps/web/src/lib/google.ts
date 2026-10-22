"use client";

import { useEffect, useState } from "react";

import type { ErrorResponse } from "@qbank/api-client";

import { api, errorMessage } from "@/lib/api";

const NETWORK = "Cannot reach the server. Check your connection and try again.";

/**
 * Which ways of signing in this server offers (`GET /auth/methods`). Google is hidden until the
 * server says it is set up; until the answer arrives, or if it cannot be had, only the password is
 * shown, which always works.
 */
export function useAuthMethods(): { password: boolean; google: boolean } {
  const [methods, setMethods] = useState({ password: true, google: false });
  useEffect(() => {
    let cancelled = false;
    api()
      .GET("/api/v1/auth/methods")
      .then(({ data }) => {
        if (!cancelled && data) setMethods(data);
      })
      .catch(() => {
        // Keep the password-only default: the sign-in page must work without this answer.
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return methods;
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
export function useGoogleResult(): "linked" | "failed" | null {
  const [result, setResult] = useState<"linked" | "failed" | null>(null);
  useEffect(() => {
    const value = new URLSearchParams(window.location.search).get("google");
    if (value === "linked" || value === "failed") {
      window.history.replaceState(null, "", window.location.pathname);
      // Reading the address bar is only possible in the browser, after the first render.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setResult(value);
    }
  }, []);
  return result;
}
