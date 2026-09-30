"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import { StageTracker } from "@/components/stage-tracker";
import { StudyPanel } from "@/components/study-panel";
import { alertClass, buttonClass, fieldClass, labelClass } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import {
  DOCUMENT_TYPES,
  documentTypeLabel,
  formatBytes,
  statusLabel,
  type Course,
  type DocumentRecord,
  type QuestionResult,
} from "@/lib/types";

const IN_FLIGHT = new Set(["PROCESSING", "EXTRACTING", "CHUNKING", "EMBEDDING", "INDEXING"]);

function tally(documents: DocumentRecord[]) {
  return {
    uploaded: documents.filter((document) => document.status === "UPLOADED").length,
    inflight: documents.filter((document) => IN_FLIGHT.has(document.status)).length,
    ready: documents.filter((document) => document.status === "READY").length,
    failed: documents.filter((document) => document.status === "FAILED").length,
  };
}

export default function CoursePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const courseId = params.id;
  const [course, setCourse] = useState<Course | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [documentType, setDocumentType] = useState("LECTURE");
  const [file, setFile] = useState<File | null>(null);
  const [pending, setPending] = useState(false);
  const [uploadKey, setUploadKey] = useState(0);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<QuestionResult | null>(null);

  function applyDocuments(nextDocuments: DocumentRecord[], preferredId?: string) {
    setDocuments(nextDocuments);
    setSelectedId((current) => {
      if (preferredId && nextDocuments.some((document) => document.id === preferredId)) return preferredId;
      if (current && nextDocuments.some((document) => document.id === current)) return current;
      return nextDocuments[0]?.id ?? null;
    });
  }

  async function load(preferredId?: string) {
    const [nextCourse, nextDocuments] = await Promise.all([
      api<Course>(`/courses/${courseId}`),
      api<DocumentRecord[]>(`/courses/${courseId}/documents`),
    ]);
    setCourse(nextCourse);
    applyDocuments(nextDocuments, preferredId);
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
        applyDocuments(nextDocuments);
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

  useEffect(() => {
    if (!documents?.some((document) => document.status !== "READY" && document.status !== "FAILED")) return;
    const timer = window.setInterval(() => {
      api<DocumentRecord[]>(`/courses/${courseId}/documents`)
        .then((nextDocuments) => applyDocuments(nextDocuments))
        .catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [courseId, documents]);

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
      setNote(
        uploaded.duplicate
          ? "This exact file is already in the corpus."
          : "Stored. The worker will extract and index it.",
      );
      await load(uploaded.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    } finally {
      setPending(false);
    }
  }

  async function removeDocument(documentId: string) {
    if (!window.confirm("Remove this file from the corpus?")) return;
    setError(null);
    try {
      await api(`/documents/${documentId}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    }
  }

  async function removeCourse() {
    if (!course || !window.confirm(`Delete ${course.name}? Uploaded files for this corpus will be removed.`)) return;
    try {
      await api(`/courses/${courseId}`, { method: "DELETE" });
      router.replace("/courses");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    }
  }

  const counts = documents ? tally(documents) : null;
  const selected = documents?.find((document) => document.id === selectedId) ?? null;

  return (
    <main className="px-5 py-8 sm:px-8 lg:py-10">
      <Link href="/courses" className="font-mono text-[11px] uppercase tracking-[0.16em] text-slag hover:text-bone">
        All courses
      </Link>

      {course ? (
        <header className="mt-4">
          {course.code ? <p className="font-mono text-[11px] tracking-[0.18em] text-ember uppercase">{course.code}</p> : null}
          <h1 className="mt-1 font-display text-4xl">{course.name}</h1>
          {course.description ? <p className="mt-3 max-w-2xl text-slag">{course.description}</p> : null}
        </header>
      ) : (
        <h1 className="mt-4 font-display text-4xl">Course</h1>
      )}

      {error ? (
        <p role="alert" className={`mt-6 ${alertClass}`}>
          {error}
        </p>
      ) : null}

      <div className="mt-8 grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section>
          {counts ? (
            <dl className="grid grid-cols-2 gap-px border border-line bg-line sm:grid-cols-4">
              {(
                [
                  ["Uploaded", counts.uploaded],
                  ["In flight", counts.inflight],
                  ["Ready", counts.ready],
                  ["Failed", counts.failed],
                ] as const
              ).map(([label, value]) => (
                <div key={label} className="bg-panel px-3 py-3">
                  <dt className="font-mono text-[10px] uppercase tracking-[0.16em] text-slag">{label}</dt>
                  <dd className="mt-2 font-mono text-xl leading-none">{value}</dd>
                </div>
              ))}
            </dl>
          ) : null}

          <form onSubmit={onUpload} className="mt-4 border border-line bg-panel p-4">
            <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-ember">Add to corpus</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_11rem]">
              <label className={labelClass}>
                Title
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Optional, otherwise taken from the filename"
                  className={fieldClass}
                />
              </label>
              <label className={labelClass}>
                Type
                <select
                  value={documentType}
                  onChange={(event) => setDocumentType(event.target.value)}
                  className={fieldClass}
                >
                  {DOCUMENT_TYPES.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="mt-4 flex flex-wrap items-end gap-3">
              <label className={labelClass}>
                File
                <input
                  type="file"
                  accept=".pdf,.txt,.md,.csv,.xlsx,.docx,.pptx,.png,.jpg,.jpeg,.webp"
                  required
                  key={uploadKey}
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  className="mt-1.5 block text-sm text-slag file:mr-3 file:border-0 file:bg-ember file:px-3 file:py-2 file:text-sm file:font-medium file:text-forge"
                />
              </label>
              <button type="submit" disabled={pending || !file} className={buttonClass}>
                {pending ? "Uploading…" : "Upload"}
              </button>
            </div>
          </form>
          {note ? <p className="mt-3 text-sm text-slag">{note}</p> : null}

          {documents && documents.length === 0 ? (
            <p className="mt-8 text-slag">
              This corpus is empty. Upload notes, slides, a spreadsheet, or a photo. Retrieval stays locked until the files are indexed.
            </p>
          ) : null}

          {documents && documents.length > 0 ? (
            <ul className="mt-4 border-y border-line">
              {documents.map((document) => {
                const active = document.id === selectedId;
                return (
                  <li key={document.id} className="border-b border-line last:border-b-0">
                    <button
                      type="button"
                      onClick={() => setSelectedId(document.id)}
                      className={`w-full px-1 py-4 text-left ${active ? "bg-panel" : "hover:bg-panel/60"}`}
                    >
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <span className="font-display text-xl">{document.title}</span>
                        <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-slag">
                          {statusLabel(document.status)}
                        </span>
                      </div>
                      <p className="mt-1 font-mono text-[11px] text-slag">
                        {documentTypeLabel(document.document_type)} · {formatBytes(document.size_bytes)} · v
                        {document.version_number}
                      </p>
                      <div className="mt-3">
                        <StageTracker status={document.status} />
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : null}

          {course?.role === "OWNER" ? (
            <button type="button" onClick={removeCourse} className="mt-8 text-sm text-fault underline-offset-4 hover:underline">
              Delete course
            </button>
          ) : null}
        </section>

        <aside className="space-y-4">
          <section className="border border-line bg-panel p-4">
            <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-ember">Inspector</p>
            {selected ? (
              <dl className="mt-4 space-y-3 text-sm">
                <div>
                  <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-slag">File</dt>
                  <dd className="mt-1 break-all">{selected.original_filename}</dd>
                </div>
                <div>
                  <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-slag">SHA-256</dt>
                  <dd className="mt-1 font-mono text-[11px] break-all text-bone">{selected.sha256}</dd>
                </div>
                <div>
                  <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-slag">Active version</dt>
                  <dd className="mt-1 font-mono text-xs">v{selected.version_number}</dd>
                </div>
                <p className="text-slag">Only the active version will be retrieved.</p>
                {selected.status === "UPLOADED" ? (
                  <p className="text-slag">Waiting for the worker to extract and index this file.</p>
                ) : null}
                {selected.error ? <p className="text-fault">{selected.error}</p> : null}
                <div className="flex gap-4 pt-1">
                  <a
                    href={`/api/documents/${selected.id}/file`}
                    className="text-sm text-bone underline-offset-4 hover:underline"
                    target="_blank"
                    rel="noreferrer"
                  >
                    View file
                  </a>
                  <button
                    type="button"
                    onClick={() => removeDocument(selected.id)}
                    className="text-sm text-fault underline-offset-4 hover:underline"
                  >
                    Remove
                  </button>
                </div>
              </dl>
            ) : (
              <p className="mt-4 text-sm text-slag">Select a file to inspect its version and hash.</p>
            )}
          </section>

          <section className="border border-line bg-panel p-4">
            <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-ember">Retrieval</p>
            {counts && counts.ready > 0 ? (
              <form
                className="mt-4"
                onSubmit={(event) => {
                  event.preventDefault();
                  if (!question.trim()) return;
                  setAsking(true);
                  setError(null);
                  setAnswer(null);
                  api<QuestionResult>(`/courses/${courseId}/questions`, {
                    method: "POST",
                    body: JSON.stringify({ question: question.trim() }),
                  })
                    .then((result) => setAnswer(result))
                    .catch((err: unknown) => {
                      setError(
                        err instanceof ApiError
                          ? err.message
                          : "Something went wrong. Your existing course data is safe. Try again.",
                      );
                    })
                    .finally(() => setAsking(false));
                }}
              >
                <label className={labelClass}>
                  Question
                  <textarea
                    rows={4}
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="Ask this corpus"
                    className={fieldClass}
                  />
                </label>
                <button type="submit" className={`${buttonClass} mt-3`} disabled={asking || !question.trim()}>
                  {asking ? "Searching the corpus…" : "Ask"}
                </button>
                {answer?.status === "answered" && answer.answer ? (
                  <div className="mt-4 border-t border-line pt-4">
                    <p className="text-sm text-bone">{answer.answer}</p>
                    <ul className="mt-3 space-y-2">
                      {answer.citations.map((citation) => (
                        <li key={citation.chunk_id}>
                          <a
                            href={`/api/documents/${citation.document_id}/file#page=${citation.page_start ?? 1}`}
                            className="text-sm text-bone underline-offset-4 hover:underline"
                            target="_blank"
                            rel="noreferrer"
                          >
                            {citation.document_title}
                            {citation.page_start ? `, p. ${citation.page_start}` : ""}
                            {citation.section ? ` · ${citation.section}` : ""}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {answer?.status === "insufficient_evidence" ? (
                  <p className="mt-4 text-sm text-slag">
                    Insufficient evidence. This corpus does not contain an answer to that question.
                  </p>
                ) : null}
              </form>
            ) : (
              <>
                <label className={`${labelClass} mt-4`}>
                  Question
                  <textarea
                    disabled
                    rows={4}
                    placeholder="Ask this corpus"
                    className={`${fieldClass} cursor-not-allowed opacity-60`}
                  />
                </label>
                <p className="mt-3 text-sm text-slag">
                  This corpus has no indexed chunks yet, so StudyForge will not answer.
                </p>
              </>
            )}
          </section>
        </aside>
      </div>
      {documents ? <StudyPanel courseId={courseId} enabled={(counts?.ready ?? 0) > 0} /> : null}
    </main>
  );
}
