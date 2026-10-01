from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.models import Flashcard, FlashcardDeck, QuizQuestion, StudySession
from tests.test_auth import register
from tests.test_courses import _create_course
from tests.test_questions import _ready_course

FOCUS = "virtual memory addresses frames"


def test_deck_cites_a_real_chunk_and_drops_invented_ids(client, db):
    course_id = _ready_course(client, db)
    created = client.post(f"/courses/{course_id}/decks", json={"focus": FOCUS})
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "created"
    cards = body["deck"]["cards"]
    assert len(cards) == 1
    stored = db.scalars(select(Flashcard)).all()
    assert len(stored) == 1
    assert cards[0]["chunk_id"] == str(stored[0].source_chunk_id)
    assert cards[0]["document_title"] == "Virtual Memory"
    assert cards[0]["page_start"] == 1
    assert "correct_option_index" not in cards[0]

    reviewed = client.post(
        f"/decks/{body['deck']['id']}/reviews",
        json={"card_id": cards[0]["id"], "rating": "AGAIN"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["next_card_id"] == cards[0]["id"]
    assert reviewed.json()["cards"][0]["latest_rating"] == "AGAIN"
    assert db.scalar(select(func.count()).select_from(FlashcardDeck)) == 1


def test_deck_outside_the_corpus_is_not_saved(client, db, language_model):
    course_id = _ready_course(client, db)
    created = client.post(f"/courses/{course_id}/decks", json={"focus": "xylophone"})
    assert created.status_code == 200
    assert created.json()["status"] == "insufficient_evidence"
    assert created.json()["deck"] is None
    assert language_model.complete_calls == 0
    assert db.scalar(select(func.count()).select_from(FlashcardDeck)) == 0


def test_quiz_score_is_computed_by_the_server(client, db):
    course_id = _ready_course(client, db)
    created = client.post(f"/courses/{course_id}/quizzes", json={"focus": FOCUS})
    assert created.status_code == 200
    quiz = created.json()["quiz"]
    assert len(quiz["questions"]) == 1
    question = quiz["questions"][0]
    assert "correct_option_index" not in question
    assert len(question["options"]) == 4
    stored = db.scalars(select(QuizQuestion)).one()
    assert stored.correct_option_index == 0
    assert str(stored.source_chunk_id)

    correct = client.post(
        f"/quizzes/{quiz['id']}/attempts",
        json={"answers": [{"question_id": question["id"], "selected_option_index": 0}]},
    )
    assert correct.status_code == 200
    assert correct.json()["score"] == 100
    assert correct.json()["results"][0]["correct"] is True
    assert correct.json()["results"][0]["correct_option_index"] == 0
    assert correct.json()["results"][0]["citation"]["document_title"] == "Virtual Memory"

    wrong = client.post(
        f"/quizzes/{quiz['id']}/attempts",
        json={"answers": [{"question_id": question["id"], "selected_option_index": 2}]},
    )
    assert wrong.json()["score"] == 0
    assert wrong.json()["results"][0]["correct"] is False


def test_plan_dates_and_durations_come_from_the_app(client, db):
    course_id = _ready_course(client, db)
    today = datetime.now(timezone.utc).date()
    exam = today + timedelta(days=1)
    created = client.post(
        f"/courses/{course_id}/plans",
        json={"exam_title": FOCUS, "exam_date": exam.isoformat(), "hours_per_day": 1},
    )
    assert created.status_code == 200
    body = created.json()
    sessions = body["sessions"]
    assert len(sessions) == 4
    assert {item["duration_minutes"] for item in sessions} == {25}
    assert {item["scheduled_on"] for item in sessions} == {today.isoformat(), exam.isoformat()}
    assert {item["focus"] for item in sessions} <= {"Virtual memory", "Address translation"}
    stored = db.scalars(select(StudySession)).all()
    assert len(stored) == 4

    done = client.post(f"/sessions/{sessions[0]['id']}/complete")
    assert done.status_code == 200
    assert done.json()["status"] == "COMPLETED"


def test_another_student_cannot_study_the_course(client, db):
    course_id = _ready_course(client, db)
    deck = client.post(f"/courses/{course_id}/decks", json={"focus": FOCUS}).json()["deck"]
    quiz = client.post(f"/courses/{course_id}/quizzes", json={"focus": FOCUS}).json()["quiz"]
    today = datetime.now(timezone.utc).date()
    plan = client.post(
        f"/courses/{course_id}/plans",
        json={
            "exam_title": "Virtual memory midterm",
            "exam_date": (today + timedelta(days=1)).isoformat(),
            "hours_per_day": 1,
        },
    ).json()
    client.post("/auth/logout")
    register(client, email="grace@university.edu", name="Grace Hopper")
    assert client.post(f"/courses/{course_id}/decks", json={"focus": FOCUS}).status_code == 404
    assert client.post(f"/decks/{deck['id']}/reviews", json={"card_id": deck["cards"][0]["id"], "rating": "KNOWN"}).status_code == 404
    assert client.get(f"/quizzes/{quiz['id']}").status_code == 404
    assert client.post(f"/sessions/{plan['sessions'][0]['id']}/complete").status_code == 404
