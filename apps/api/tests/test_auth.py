from app.config import get_settings


def register(client, email="ada@university.edu", name="Ada Lovelace", password="password123"):
    response = client.post(
        "/auth/register",
        json={"email": email, "name": name, "password": password},
    )
    return response


def test_register_login_me_and_logout(client):
    created = register(client)
    assert created.status_code == 201
    body = created.json()
    assert body["email"] == "ada@university.edu"
    assert "password" not in body

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["name"] == "Ada Lovelace"

    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401

    logged_in = client.post(
        "/auth/login",
        json={"email": "ada@university.edu", "password": "password123"},
    )
    assert logged_in.status_code == 200
    assert client.get("/auth/me").status_code == 200


def test_duplicate_email_is_rejected(client):
    assert register(client).status_code == 201
    client.post("/auth/logout")
    again = register(client)
    assert again.status_code == 409


def test_login_failure_is_generic(client):
    register(client)
    client.post("/auth/logout")
    wrong = client.post(
        "/auth/login",
        json={"email": "ada@university.edu", "password": "not-the-password"},
    )
    missing = client.post(
        "/auth/login",
        json={"email": "missing@university.edu", "password": "not-the-password"},
    )
    assert wrong.status_code == 401
    assert missing.status_code == 401
    assert wrong.json()["detail"] == missing.json()["detail"]


def test_repeated_login_is_rate_limited(client, monkeypatch):
    monkeypatch.setenv("AUTH_ATTEMPTS_PER_MINUTE", "2")
    get_settings.cache_clear()
    assert register(client).status_code == 201
    client.post("/auth/logout")
    body = {"email": "ada@university.edu", "password": "password123"}
    assert client.post("/auth/login", json=body).status_code == 200
    blocked = client.post("/auth/login", json=body)
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "Too many attempts. Try again shortly."
    assert int(blocked.headers["retry-after"]) >= 1


def test_weak_password_is_rejected(client):
    response = register(client, password="short")
    assert response.status_code == 422
