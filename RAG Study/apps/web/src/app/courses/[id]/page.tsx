"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import {
  DOCUMENT_TYPES,
  documentTypeLabel,
  formatBytes,
  statusLabel,
  type Course,
  type DocumentRecord,
} from "@/lib/types";

function statusClass(status: string): string {
  if (status === "READY") return "bg-pine-soft text-pine";
  if (status === "FAILED") return "bg-clay-soft text-clay";
  if (status === "UPLOADED") return "bg-gold-soft text-gold";
  return "bg-sand text-ink";
}

export default function CoursePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const courseId = params.id;
  const [course, setCourse] = useState<Course | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [documentType, setDocumentType] = useState("LECTURE");
  const [file, setFile] = useState<File | null>(null);
  const [pending, setPending] = useState(false);
  const [uploadKey, setUploadKey] = useState(0);

  async function load() {
    const [nextCourse, nextDocuments] = await Promise.all([
      api<Course>(`/courses/${courseId}`),
      api<DocumentRecord[]>(`/courses/${courseId}/documents`),
    ]);
    setCourse(nextCourse);
    setDocuments(nextDocuments);
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api<Course>(`/courses/${courseId}`),
      api<DocumentRecord[]>(`/courses/${courseId}/documents`),
    ])
      .then(([nextCourse, nextDocuments]) => {
        if (cancelled) return;
        setCourse(nextCourse);
        setDocuments(nextDocuments);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setError("Course not found");
          return;
        }
        setError(
          err instanceof ApiError
            ? err.message
            : "Something went wrong. Your existing course data is safe. Try again.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  async function onUpload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setPending(true);
    setError(null);
    setNote(null);
    const body = new FormData();
    body.set("file", file);
    body.set("document_type", documentType);
    if (title.trim()) body.set("title", title.trim());
    try {
      const uploaded = await api<DocumentRecord>(`/courses/${courseId}/documents`, {
        method: "POST",
        body,
      });
      setTitle("");
      setFile(null);
      setUploadKey((value) => value + 1);
      setNote(uploaded.duplicate ? "This exact file is already in the course." : "Stored. Text extraction has not started yet.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    } finally {
      setPending(false);
    }
  }

  async function removeDocument(documentId: string) {
    if (!window.confirm("Remove this document from the course?")) return;
    setError(null);
    try {
      await api(`/documents/${documentId}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    }
  }

  async function removeCourse() {
    if (!course || !window.confirm(`Delete ${course.name}? Uploaded files for this course will be removed.`)) return;
    try {
      await api(`/courses/${courseId}`, { method: "DELETE" });
      router.replace("/courses");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <Link href="/courses" className="text-sm text-muted underline-offset-4 hover:underline">
        All courses
      </Link>

      {course ? (
        <header className="mt-4">
          {course.code ? <p className="text-xs tracking-[0.18em] text-pine uppercase">{course.code}</p> : null}
          <h1 className="font-serif text-4xl">{course.name}</h1>
          {course.description ? <p className="mt-3 max-w-2xl text-muted">{course.description}</p> : null}
        </header>
      ) : (
        <h1 className="mt-4 font-serif text-4xl">Course</h1>
      )}

      {error ? (
        <p role="alert" className="mt-6 rounded-md bg-clay-soft px-3 py-2 text-sm text-clay">
          {error}
        </p>
      ) : null}

      <form onSubmit={onUpload} className="mt-8 grid gap-3 rounded-lg border border-line bg-sand p-4 sm:grid-cols-[1fr_10rem_auto]">
        <label className="text-sm sm:col-span-1">
          Title
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Optional, otherwise taken from the filename"
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2 outline-none focus:border-pine"
          />
        </label>
        <label className="text-sm">
          Type
          <select
            value={documentType}
            onChange={(event) => setDocumentType(event.target.value)}
            className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2 outline-none focus:border-pine"
          >
            {DOCUMENT_TYPES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-end gap-3 sm:col-span-3">
          <label className="text-sm">
            PDF
            <input
              type="file"
              accept="application/pdf,.pdf"
              required
              key={uploadKey}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              className="mt-1 block text-sm"
            />
          </label>
          <button
            type="submit"
            disabled={pending || !file}
            className="rounded-full bg-pine px-5 py-2.5 text-sm text-sand hover:bg-pine-deep disabled:opacity-60"
          >
            {pending ? "Uploading…" : "Upload"}
          </button>
        </div>
      </form>
      {note ? <p className="mt-3 text-sm text-muted">{note}</p> : null}

      {documents && documents.length === 0 ? (
        <p className="mt-10 text-muted">Upload your syllabus or lecture notes to start asking course questions.</p>
      ) : null}

      {documents && documents.length > 0 ? (
        <ul className="mt-8 divide-y divide-line border-y border-line">
          {documents.map((document) => (
            <li key={document.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-serif text-xl">{document.title}</p>
                <p className="mt-1 text-sm text-muted">
                  {documentTypeLabel(document.document_type)} · {document.original_filename} · {formatBytes(document.size_bytes)} · v{document.version_number}
                </p>
                {document.status === "UPLOADED" ? (
                  <p className="mt-1 text-sm text-muted">Stored. Text extraction has not started yet.</p>
                ) : null}
                {document.error ? <p className="mt-1 text-sm text-clay">{document.error}</p> : null}
              </div>
              <div className="flex items-center gap-3">
                <span className={`rounded-full px-3 py-1 text-xs ${statusClass(document.status)}`}>
                  {statusLabel(document.status)}
                </span>
                <a href={`/api/documents/${document.id}/file`} className="text-sm underline-offset-4 hover:underline" target="_blank" rel="noreferrer">
                  View
                </a>
                <button type="button" onClick={() => removeDocument(document.id)} className="text-sm text-clay underline-offset-4 hover:underline">
                  Remove
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : null}

      {course?.role === "OWNER" ? (
        <button type="button" onClick={removeCourse} className="mt-12 text-sm text-clay underline-offset-4 hover:underline">
          Delete course
        </button>
      ) : null}
    </main>
  );
}
