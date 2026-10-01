# StudyForge

Course-aware study system. PostgreSQL holds application state, object storage holds uploaded files, and the API is the only place that will orchestrate retrieval and planning.

This repository currently implements the foundation:

- accounts (register, login, logout)
- courses, with membership checks on every request
- upload of PDFs, text, spreadsheets, Word, PowerPoint, and images, with versions and background jobs
- grounded questions, flashcards, quizzes, and an exam study plan

## Run locally

```bash
docker compose up -d
python3 -m venv apps/api/.venv
apps/api/.venv/bin/pip install -e "apps/api[dev]"
make migrate
make api
```

In other terminals:

```bash
make worker
make web
```

Set `OPENAI_API_KEY` in `.env` before starting the worker. Embeddings use `text-embedding-3-small`. Answers use `gpt-4o-mini`.

Open [http://localhost:3000](http://localhost:3000).

The web app sends `/api/*` to the API on port 8000 and keeps the session in an HTTP-only cookie.

## Tests

```bash
make test
```

Tests use a separate `study_test` database on the same Postgres instance.

## Boundaries

- A course that the caller does not belong to responds as not found.
- Uploaded bytes are stored at `course/{course_id}/documents/{document_id}/versions/{version_id}/original` plus the file suffix. The database stores the key and metadata, including a SHA-256.
- Only the active document version is the one retrieval reads.
- Upload enqueues one `document_processing` job per version. The worker extracts text, chunks it, embeds it, and marks the version `READY`. A PDF with no extractable text fails and asks for OCR. A photo is transcribed instead.
- Questions, flashcards, and quizzes search only the active versions in that course. Weak retrieval returns insufficient evidence and does not call the chat model. Citations must name a retrieved chunk id. Quiz scores are computed by the server. A study plan's dates and durations are computed by the app.
