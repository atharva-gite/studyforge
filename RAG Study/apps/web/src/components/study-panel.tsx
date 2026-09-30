"use client";

import { useEffect, useState } from "react";

import { buttonClass, fieldClass, labelClass } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import type { Attempt, Deck, DeckResult, Quiz, QuizResult, StudyPlan } from "@/lib/types";

const locked = "Index a file before studying. StudyForge will not invent cards or questions.";

export function StudyPanel({ courseId, enabled }: { courseId: string; enabled: boolean }) {
  const [focus, setFocus] = useState("");
  const [deck, setDeck] = useState<Deck | null>(null);
  const [showBack, setShowBack] = useState(false);
  const [deckNote, setDeckNote] = useState<string | null>(null);
  const [makingDeck, setMakingDeck] = useState(false);
  const [quizFocus, setQuizFocus] = useState("");
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [choices, setChoices] = useState<Record<string, number>>({});
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [quizNote, setQuizNote] = useState<string | null>(null);
  const [makingQuiz, setMakingQuiz] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [examTitle, setExamTitle] = useState("");
  const [examDate, setExamDate] = useState("");
  const [hours, setHours] = useState("1");
  const [plan, setPlan] = useState<StudyPlan | null>(null);
  const [planNote, setPlanNote] = useState<string | null>(null);
  const [makingPlan, setMakingPlan] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    Promise.all([
      api<Deck[]>(`/courses/${courseId}/decks`),
      api<StudyPlan[]>(`/courses/${courseId}/plans`),
    ])
      .then(([decks, plans]) => {
        if (cancelled) return;
        setDeck(decks[0] ?? null);
        setPlan(plans[0] ?? null);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [courseId, enabled]);

  const card = deck?.cards.find((item) => item.id === deck.next_card_id) ?? deck?.cards[0] ?? null;

  async function onDeck(event: { preventDefault: () => void }) {
    event.preventDefault();
    if (!focus.trim()) return;
    setMakingDeck(true);
    setError(null);
    setDeckNote(null);
    try {
      const result = await api<DeckResult>(`/courses/${courseId}/decks`, {
        method: "POST",
        body: JSON.stringify({ focus: focus.trim() }),
      });
      if (result.status === "insufficient_evidence" || !result.deck) {
        setDeckNote("Insufficient evidence. This corpus does not support a deck on that focus.");
        return;
      }
      setDeck(result.deck);
      setShowBack(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    } finally {
      setMakingDeck(false);
    }
  }

  async function rate(rating: "AGAIN" | "KNOWN") {
    if (!deck || !card) return;
    setError(null);
    try {
      const next = await api<Deck>(`/decks/${deck.id}/reviews`, {
        method: "POST",
        body: JSON.stringify({ card_id: card.id, rating }),
      });
      setDeck(next);
      setShowBack(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    }
  }

  async function onQuiz() {
    if (!quizFocus.trim()) return;
    setMakingQuiz(true);
    setError(null);
    setQuizNote(null);
    setAttempt(null);
    setChoices({});
    try {
      const result = await api<QuizResult>(`/courses/${courseId}/quizzes`, {
        method: "POST",
        body: JSON.stringify({ focus: quizFocus.trim() }),
      });
      if (result.status === "insufficient_evidence" || !result.quiz) {
        setQuiz(null);
        setQuizNote("Insufficient evidence. This corpus does not support a quiz on that focus.");
        return;
      }
      setQuiz(result.quiz);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    } finally {
      setMakingQuiz(false);
    }
  }

  async function onAttempt() {
    if (!quiz) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await api<Attempt>(`/quizzes/${quiz.id}/attempts`, {
        method: "POST",
        body: JSON.stringify({
          answers: quiz.questions.map((question) => ({
            question_id: question.id,
            selected_option_index: choices[question.id],
          })),
        }),
      });
      setAttempt(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function onPlan(event: { preventDefault: () => void }) {
    event.preventDefault();
    if (!examTitle.trim() || !examDate) return;
    setMakingPlan(true);
    setError(null);
    setPlanNote(null);
    try {
      const created = await api<StudyPlan>(`/courses/${courseId}/plans`, {
        method: "POST",
        body: JSON.stringify({
          exam_title: examTitle.trim(),
          exam_date: examDate,
          hours_per_day: Number(hours),
        }),
      });
      setPlan(created);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    } finally {
      setMakingPlan(false);
    }
  }

  async function complete(sessionId: string) {
    setError(null);
    try {
      const updated = await api<StudyPlan["sessions"][number]>(`/sessions/${sessionId}/complete`, { method: "POST" });
      setPlan((current) =>
        current
          ? { ...current, sessions: current.sessions.map((session) => (session.id === updated.id ? updated : session)) }
          : current,
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Your existing course data is safe. Try again.");
    }
  }

  return (
    <section className="mt-8 border border-line bg-panel p-4">
      <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-ember">Study</p>
      {error ? <p className="mt-3 text-sm text-fault">{error}</p> : null}
      {!enabled ? (
        <p className="mt-4 text-sm text-slag">{locked}</p>
      ) : (
        <div className="mt-4 grid gap-6 xl:grid-cols-3">
          <form onSubmit={onDeck}>
            <p className="font-display text-lg">Flashcards</p>
            <label className={`${labelClass} mt-3`}>
              Focus
              <input value={focus} onChange={(event) => setFocus(event.target.value)} className={fieldClass} placeholder="virtual memory" />
            </label>
            <button type="submit" className={`${buttonClass} mt-3`} disabled={makingDeck || !focus.trim()}>
              {makingDeck ? "Building the deck…" : "Generate deck"}
            </button>
            {deckNote ? <p className="mt-3 text-sm text-slag">{deckNote}</p> : null}
            {card ? (
              <div className="mt-4 border-t border-line pt-4">
                <p className="text-sm text-bone">{showBack ? card.back : card.front}</p>
                {card.document_title ? (
                  <a
                    href={`/api/documents/${card.document_id}/file#page=${card.page_start ?? 1}`}
                    className="mt-2 block text-sm text-bone underline-offset-4 hover:underline"
                    target="_blank"
                    rel="noreferrer"
                  >
                    {card.document_title}
                    {card.page_start ? `, p. ${card.page_start}` : ""}
                  </a>
                ) : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" className={buttonClass} onClick={() => setShowBack((value) => !value)}>
                    {showBack ? "Show front" : "Flip"}
                  </button>
                  {showBack ? (
                    <>
                      <button type="button" className={buttonClass} onClick={() => rate("AGAIN")}>
                        Again
                      </button>
                      <button type="button" className={buttonClass} onClick={() => rate("KNOWN")}>
                        Known
                      </button>
                    </>
                  ) : null}
                </div>
              </div>
            ) : null}
          </form>

          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (!attempt) void onQuiz();
            }}
          >
            <p className="font-display text-lg">Quiz</p>
            <label className={`${labelClass} mt-3`}>
              Focus
              <input value={quizFocus} onChange={(event) => setQuizFocus(event.target.value)} className={fieldClass} placeholder="virtual memory" />
            </label>
            <button type="button" className={`${buttonClass} mt-3`} disabled={makingQuiz || !quizFocus.trim()} onClick={() => void onQuiz()}>
              {makingQuiz ? "Writing questions…" : "Generate quiz"}
            </button>
            {quizNote ? <p className="mt-3 text-sm text-slag">{quizNote}</p> : null}
            {quiz && !attempt ? (
              <div className="mt-4 space-y-4 border-t border-line pt-4">
                {quiz.questions.map((question, index) => (
                  <fieldset key={question.id}>
                    <legend className="text-sm text-bone">
                      {index + 1}. {question.prompt}
                    </legend>
                    <div className="mt-2 space-y-1">
                      {question.options.map((option, optionIndex) => (
                        <label key={option} className="flex items-center gap-2 text-sm text-slag">
                          <input
                            type="radio"
                            name={question.id}
                            checked={choices[question.id] === optionIndex}
                            onChange={() => setChoices((current) => ({ ...current, [question.id]: optionIndex }))}
                          />
                          {option}
                        </label>
                      ))}
                    </div>
                  </fieldset>
                ))}
                <button
                  type="button"
                  className={buttonClass}
                  disabled={submitting || quiz.questions.some((question) => choices[question.id] === undefined)}
                  onClick={() => void onAttempt()}
                >
                  {submitting ? "Scoring…" : "Submit"}
                </button>
              </div>
            ) : null}
            {attempt ? (
              <div className="mt-4 border-t border-line pt-4">
                <p className="font-mono text-sm text-bone">Score {attempt.score}</p>
                <ul className="mt-3 space-y-3">
                  {attempt.results.map((result) => (
                    <li key={result.question_id} className="text-sm">
                      <p className={result.correct ? "text-signal" : "text-fault"}>{result.prompt}</p>
                      {result.explanation ? <p className="mt-1 text-slag">{result.explanation}</p> : null}
                      {result.citation ? (
                        <a
                          href={`/api/documents/${result.citation.document_id}/file#page=${result.citation.page_start ?? 1}`}
                          className="mt-1 block text-bone underline-offset-4 hover:underline"
                          target="_blank"
                          rel="noreferrer"
                        >
                          {result.citation.document_title}
                          {result.citation.page_start ? `, p. ${result.citation.page_start}` : ""}
                        </a>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </form>

          <form onSubmit={onPlan}>
            <p className="font-display text-lg">Exam plan</p>
            <label className={`${labelClass} mt-3`}>
              Exam
              <input value={examTitle} onChange={(event) => setExamTitle(event.target.value)} className={fieldClass} placeholder="Midterm" />
            </label>
            <label className={`${labelClass} mt-3`}>
              Date
              <input type="date" value={examDate} onChange={(event) => setExamDate(event.target.value)} className={fieldClass} />
            </label>
            <label className={`${labelClass} mt-3`}>
              Hours per day
              <input
                type="number"
                min={0.5}
                max={16}
                step={0.5}
                value={hours}
                onChange={(event) => setHours(event.target.value)}
                className={fieldClass}
              />
            </label>
            <button type="submit" className={`${buttonClass} mt-3`} disabled={makingPlan || !examTitle.trim() || !examDate}>
              {makingPlan ? "Scheduling…" : "Build plan"}
            </button>
            {planNote ? <p className="mt-3 text-sm text-slag">{planNote}</p> : null}
            {plan ? (
              <ul className="mt-4 space-y-3 border-t border-line pt-4">
                {plan.sessions.map((session) => (
                  <li key={session.id} className="text-sm">
                    <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-slag">
                      {session.scheduled_on} · {session.duration_minutes} min · {session.activity}
                    </p>
                    <p className="text-bone">{session.focus}</p>
                    {session.status === "COMPLETED" ? (
                      <p className="text-signal">Done</p>
                    ) : (
                      <button type="button" className={`${buttonClass} mt-2`} onClick={() => complete(session.id)}>
                        Mark complete
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            ) : null}
          </form>
        </div>
      )}
    </section>
  );
}
