"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import type { Me } from "@qbank/api-client";

import { api } from "@/lib/api";

/**
 * The signed-in person for a page of the app: loads `/me`, sends signed-out visitors to the
 * sign-in page, and signs out. Every page behind the sign-in page uses it.
 */
export function useMe() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [signOutError, setSignOutError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      let who;
      try {
        who = await api().GET("/api/v1/me");
      } catch {
        if (!cancelled) setLoadError("Cannot reach the server. Check your connection.");
        return;
      }
      if (cancelled) return;
      // Only "not signed in" leads to the sign-in page; any other failure is an outage to report.
      if (who.response.status === 401) {
        router.replace("/login");
        return;
      }
      if (!who.data) {
        setLoadError("The server could not load your account right now.");
        return;
      }
      setMe(who.data);
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [router, attempt]);

  function retry() {
    setLoadError(null);
    setAttempt((n) => n + 1);
  }

  async function signOut() {
    setSignOutError(null);
    try {
      const { response } = await api().POST("/api/v1/auth/logout");
      // 401: the session had already ended (expired or revoked), so the user is signed out anyway.
      if (response.ok || response.status === 401) {
        router.replace("/login");
        return;
      }
    } catch {
      // network failure: fall through
    }
    // Never show the signed-out screen while the server session may still be valid.
    setSignOutError("Could not sign out. You are still signed in; please try again.");
  }

  return { me, loadError, signOutError, retry, signOut };
}
