import uuid

from sqlalchemy import select

from app.models import CourseMember, CourseRole, User
from tests.test_auth import register


def _create_course(client, name="Operating Systems", code="CS301"):
    return client.post("/courses", json={"name": name, "code": code, "description": "Processes and memory"})


def test_course_is_private_to_its_members(client):
    register(client, email="ada@university.edu")
    created = _create_course(client)
    assert created.status_code == 201
    course_id = created.json()["id"]
    assert created.json()["role"] == "OWNER"
    assert created.json()["document_count"] == 0

    listed = client.get("/courses")
    assert listed.status_code == 200
    assert [course["id"] for course in listed.json()] == [course_id]

    client.post("/auth/logout")
    register(client, email="alan@university.edu", name="Alan Turing")
    assert client.get("/courses").json() == []
    assert client.get(f"/courses/{course_id}").status_code == 404
    assert client.patch(f"/courses/{course_id}", json={"name": "Stolen"}).status_code == 404
    assert client.delete(f"/courses/{course_id}").status_code == 404


def test_member_cannot_rename_or_delete(client, db):
    register(client, email="ada@university.edu")
    course_id = _create_course(client).json()["id"]

    client.post("/auth/logout")
    register(client, email="alan@university.edu", name="Alan Turing")
    member = db.scalar(select(User).where(User.email == "alan@university.edu"))
    db.add(CourseMember(course_id=uuid.UUID(course_id), user_id=member.id, role=CourseRole.MEMBER))
    db.commit()

    assert client.get(f"/courses/{course_id}").status_code == 200
    assert client.patch(f"/courses/{course_id}", json={"name": "Renamed"}).status_code == 403
    assert client.delete(f"/courses/{course_id}").status_code == 403


def test_owner_can_update_and_delete(client):
    register(client)
    course_id = _create_course(client).json()["id"]
    updated = client.patch(f"/courses/{course_id}", json={"name": "Operating Systems II", "code": ""})
    assert updated.status_code == 200
    assert updated.json()["name"] == "Operating Systems II"
    assert updated.json()["code"] is None

    assert client.delete(f"/courses/{course_id}").status_code == 204
    assert client.get(f"/courses/{course_id}").status_code == 404


def test_blank_course_name_is_rejected(client):
    register(client)
    response = client.post("/courses", json={"name": "   "})
    assert response.status_code == 422
