"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

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
    <main className="mx-auto max-w-xl px-6 py-12">
      <Link href="/courses" className="text-sm text-muted underline-offset-4 hover:underline">
        Back to courses
      </Link>
      <h1 className="mt-4 font-serif text-4xl">New course</h1>
      <form onSubmit={onSubmit} className="mt-8 space-y-4">
        <label className="block text-sm">
          Name
          <input
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Operating Systems"
            className="mt-1 w-full rounded-md border border-line bg-sand px-3 py-2 outline-none focus:border-pine"
          />
        </label>
        <label className="block text-sm">
          Code
          <input
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="CS301"
            className="mt-1 w-full rounded-md border border-line bg-sand px-3 py-2 outline-none focus:border-pine"
          />
        </label>
        <label className="block text-sm">
          Description
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={4}
            className="mt-1 w-full rounded-md border border-line bg-sand px-3 py-2 outline-none focus:border-pine"
          />
        </label>
        {error ? (
          <p role="alert" className="rounded-md bg-clay-soft px-3 py-2 text-sm text-clay">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={pending}
          className="rounded-full bg-pine px-5 py-2.5 text-sm text-sand hover:bg-pine-deep disabled:opacity-60"
        >
          {pending ? "Creating…" : "Create course"}
        </button>
      </form>
    </main>
  );
}
