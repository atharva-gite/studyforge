"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Pipeline } from "@/components/pipeline";
import { alertClass, buttonClass, fieldClass, labelClass } from "@/components/ui";
import { Wordmark } from "@/components/wordmark";
import { ApiError, api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      router.replace("/courses");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="flex flex-col justify-center px-6 py-16 sm:px-10 lg:px-16">
        <Wordmark />
        <h1 className="mt-12 font-display text-4xl">Sign in</h1>
        <p className="mt-2 text-slag">Open a course corpus.</p>
        <form onSubmit={onSubmit} className="mt-8 max-w-md space-y-4">
          <label className={labelClass}>
            Email
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={fieldClass}
            />
          </label>
          <label className={labelClass}>
            Password
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={fieldClass}
            />
          </label>
          {error ? (
            <p role="alert" className={alertClass}>
              {error}
            </p>
          ) : null}
          <button type="submit" disabled={pending} className={buttonClass}>
            {pending ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="mt-6 text-sm text-slag">
          No account yet?{" "}
          <Link href="/register" className="text-bone underline-offset-4 hover:underline">
            Create one
          </Link>
        </p>
      </section>
      <section className="border-t border-line bg-panel px-6 py-14 sm:px-10 lg:border-t-0 lg:border-l lg:px-12 lg:py-16">
        <Pipeline />
      </section>
    </main>
  );
}
