"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Wordmark } from "@/components/wordmark";
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

  if (bare) {
    if (state === "loading" || state === "ready") {
      return <div className="px-6 py-10 font-mono text-xs uppercase tracking-[0.16em] text-slag">Loading…</div>;
    }
    return <>{children}</>;
  }

  if (state !== "ready" || !user) {
    return <div className="px-6 py-10 font-mono text-xs uppercase tracking-[0.16em] text-slag">Loading…</div>;
  }

  const coursesActive = pathname.startsWith("/courses");

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[220px_minmax(0,1fr)]">
      <aside className="flex items-center justify-between gap-4 border-b border-line px-4 py-3 lg:flex-col lg:items-stretch lg:justify-between lg:border-r lg:border-b-0 lg:px-5 lg:py-6">
        <div className="flex items-center gap-5 lg:block">
          <Wordmark href="/courses" />
          <nav className="lg:mt-8">
            <Link
              href="/courses"
              className={`font-mono text-[11px] uppercase tracking-[0.16em] ${coursesActive ? "text-ember" : "text-slag hover:text-bone"}`}
            >
              Courses
            </Link>
          </nav>
        </div>
        <div className="min-w-0 text-right lg:text-left">
          <p className="truncate font-mono text-[11px] text-slag">{user.email}</p>
          <button type="button" onClick={logout} className="mt-1 text-sm text-bone underline-offset-4 hover:underline">
            Log out
          </button>
        </div>
      </aside>
      <div className="min-w-0">{children}</div>
    </div>
  );
}
