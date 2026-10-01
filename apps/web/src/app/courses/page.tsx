"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { alertClass, buttonClass } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { Course } from "@/lib/types";

export default function CoursesPage() {
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Course[]>("/courses")
      .then(setCourses)
      .catch((err: unknown) => {
        setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
      });
  }, []);

  return (
    <main className="px-5 py-8 sm:px-8 lg:py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ember">Corpora</p>
          <h1 className="mt-2 font-display text-4xl">Courses</h1>
          <p className="mt-2 max-w-xl text-slag">Each course is its own corpus. Files, versions, and later retrieval stay inside it.</p>
        </div>
        <Link href="/courses/new" className={buttonClass}>
          New course
        </Link>
      </div>

      {error ? (
        <p role="alert" className={`mt-8 ${alertClass}`}>
          {error}
        </p>
      ) : null}

      {courses === null && !error ? <p className="mt-10 font-mono text-xs uppercase tracking-[0.16em] text-slag">Loading corpora…</p> : null}

      {courses && courses.length === 0 ? (
        <div className="mt-10 border border-dashed border-line bg-panel px-6 py-10">
          <p className="font-display text-2xl">No corpus yet</p>
          <p className="mt-2 max-w-lg text-slag">
            Create a course, then upload the syllabus and lectures. Retrieval stays locked until those files are indexed.
          </p>
        </div>
      ) : null}

      {courses && courses.length > 0 ? (
        <ul className="mt-8 border-y border-line">
          {courses.map((course) => (
            <li key={course.id} className="border-b border-line last:border-b-0">
              <Link href={`/courses/${course.id}`} className="flex items-baseline justify-between gap-6 py-5 hover:bg-panel">
                <span className="min-w-0">
                  {course.code ? (
                    <span className="mr-3 font-mono text-[11px] tracking-[0.16em] text-ember uppercase">{course.code}</span>
                  ) : null}
                  <span className="font-display text-2xl">{course.name}</span>
                </span>
                <span className="shrink-0 font-mono text-[11px] uppercase tracking-[0.14em] text-slag">
                  {course.document_count} {course.document_count === 1 ? "file" : "files"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </main>
  );
}
