"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { api, errorMessage } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const { error, response } = await api().POST("/api/v1/auth/login", {
        body: { email: String(form.get("email")), password: String(form.get("password")) },
      });
      if (response.ok) {
        router.replace("/");
        return;
      }
      setError(errorMessage(error, response.status));
    } catch {
      setError("Cannot reach the server. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-4 dark:bg-zinc-950">
      <form
        onSubmit={signIn}
        className="w-full max-w-sm space-y-5 rounded-xl border border-zinc-200 bg-white p-8 shadow-sm dark:border-zinc-800 dark:bg-zinc-900"
      >
        <div>
          <h1 className="text-xl font-semibold">Question Bank</h1>
          <p className="text-sm text-zinc-500">Sign in to continue</p>
        </div>
        <label className="block space-y-1 text-sm font-medium">
          <span>Email</span>
          <input
            name="email"
            type="email"
            autoComplete="username"
            required
            className="w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950"
          />
        </label>
        <label className="block space-y-1 text-sm font-medium">
          <span>Password</span>
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="w-full rounded-md border border-zinc-300 px-3 py-2 font-normal dark:border-zinc-700 dark:bg-zinc-950"
          />
        </label>
        {error && (
          <p
            role="alert"
            className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
          >
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-md bg-zinc-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-60 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
