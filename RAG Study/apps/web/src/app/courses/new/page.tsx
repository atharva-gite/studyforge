"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { alertClass, buttonClass, fieldClass, labelClass } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { Course } from "@/lib/types";

export default function NewCoursePage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const course = await api<Course>("/courses", {
        method: "POST",
        body: JSON.stringify({
          name,
          code: code || null,
          description: description || null,
        }),
      });
      router.replace(`/courses/${course.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
      setPending(false);
    }
  }

  return (
    <main className="px-5 py-8 sm:px-8 lg:py-10">
      <Link href="/courses" className="font-mono text-[11px] uppercase tracking-[0.16em] text-slag hover:text-bone">
        All courses
      </Link>
      <h1 className="mt-4 font-display text-4xl">New course</h1>
      <p className="mt-2 max-w-lg text-slag">A course is a corpus. Its files stay separate from every other course.</p>
      <form onSubmit={onSubmit} className="mt-8 max-w-xl space-y-4 border border-line bg-panel p-5">
        <label className={labelClass}>
          Name
          <input
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Operating Systems"
            className={fieldClass}
          />
        </label>
        <label className={labelClass}>
          Code
          <input
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="CS301"
            className={fieldClass}
          />
        </label>
        <label className={labelClass}>
          Description
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={4}
            className={fieldClass}
          />
        </label>
        {error ? (
          <p role="alert" className={alertClass}>
            {error}
          </p>
        ) : null}
        <button type="submit" disabled={pending} className={buttonClass}>
          {pending ? "Creating…" : "Create course"}
        </button>
      </form>
    </main>
  );
}
