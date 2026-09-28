"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { User } from "@/lib/types";

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const bare = pathname === "/" || pathname === "/login" || pathname === "/register";
  const [user, setUser] = useState<User | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "anon">("loading");

  useEffect(() => {
    let cancelled = false;
    api<User>("/auth/me")
      .then((nextUser) => {
        if (cancelled) return;
        setUser(nextUser);
        setState("ready");
        if (pathname === "/" || pathname === "/login" || pathname === "/register") {
          router.replace("/courses");
        }
      })
      .catch(() => {
        if (cancelled) return;
        setUser(null);
        setState("anon");
        if (pathname !== "/" && pathname !== "/login" && pathname !== "/register") {
          router.replace("/login");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [pathname, router]);

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    setUser(null);
    router.replace("/login");
  }

  if (state === "loading" || (!bare && state !== "ready")) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-10 text-muted">Loading…</div>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-6 py-4">
          <Link href={user ? "/courses" : "/"} className="font-serif text-2xl tracking-tight">
            Folio
          </Link>
          {user ? (
            <div className="flex items-center gap-4 text-sm">
              <span className="hidden text-muted sm:inline">{user.email}</span>
              <button type="button" onClick={logout} className="text-ink underline-offset-4 hover:underline">
                Log out
              </button>
            </div>
          ) : null}
        </div>
      </header>
      {children}
    </div>
  );
}
