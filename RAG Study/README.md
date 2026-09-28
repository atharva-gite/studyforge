# StudyForge

Course-aware study system. PostgreSQL holds application state, object storage holds uploaded files, and the API is the only place that will orchestrate retrieval and planning.

This repository currently implements the foundation:

- accounts (register, login, logout)
- courses, with membership checks on every request
- PDF upload, exact-duplicate detection, versions, and background-job records

Document text extraction, hybrid retrieval, quizzes, and study plans are later phases. Their tables already exist so that work extends this model instead of replacing it.

## Run locally

```bash
docker compose up -d
python3 -m venv apps/api/.venv
apps/api/.venv/bin/pip install -e "apps/api[dev]"
make migrate
make api
```

In another terminal:

```bash
make web
```

Open [http://localhost:3000](http://localhost:3000).

The web app sends `/api/*` to the API on port 8000 and keeps the session in an HTTP-only cookie.

## Tests

```bash
make test
```

Tests use a separate `study_test` database on the same Postgres instance.

## Boundaries

- A course that the caller does not belong to responds as not found.
- Uploaded bytes are stored at `course/{course_id}/documents/{document_id}/versions/{version_id}/original.pdf`. The database stores the key and metadata, including a SHA-256.
- Only the active document version is the one later retrieval should read.
- Upload enqueues one `document_processing` job per version. Reprocess reuses that job unless it is already running. The worker that extracts and indexes PDFs is not part of this phase, so new documents stay `UPLOADED`.
