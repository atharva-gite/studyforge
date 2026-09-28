"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

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
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-4xl">Courses</h1>
          <p className="mt-2 text-muted">Each course keeps its own documents and, later, its own progress.</p>
        </div>
        <Link href="/courses/new" className="rounded-full bg-pine px-5 py-2.5 text-sm text-sand hover:bg-pine-deep">
          New course
        </Link>
      </div>

      {error ? (
        <p role="alert" className="mt-8 rounded-md bg-clay-soft px-3 py-2 text-sm text-clay">
          {error}
        </p>
      ) : null}

      {courses === null && !error ? <p className="mt-10 text-muted">Loading courses…</p> : null}

      {courses && courses.length === 0 ? (
        <div className="mt-10 rounded-lg border border-dashed border-line bg-sand px-6 py-10">
          <p className="font-serif text-2xl">No courses yet</p>
          <p className="mt-2 max-w-lg text-muted">
            Create a course, then upload your syllabus or lecture notes to start asking course questions.
          </p>
        </div>
      ) : null}

      {courses && courses.length > 0 ? (
        <ul className="mt-8 divide-y divide-line border-y border-line">
          {courses.map((course) => (
            <li key={course.id}>
              <Link href={`/courses/${course.id}`} className="flex items-baseline justify-between gap-6 py-5 hover:bg-sand">
                <span>
                  {course.code ? (
                    <span className="mr-3 text-xs tracking-[0.16em] text-pine uppercase">{course.code}</span>
                  ) : null}
                  <span className="font-serif text-2xl">{course.name}</span>
                </span>
                <span className="shrink-0 text-sm text-muted">
                  {course.document_count} {course.document_count === 1 ? "document" : "documents"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </main>
  );
}
