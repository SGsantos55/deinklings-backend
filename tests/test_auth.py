import time
import uuid

import jwt
import pytest
from flask import jsonify

from app.auth.decorators import role_required
from app.extensions import db
from app.models import User
from tests.conftest import SECRET
from tests.helpers import SIGNUP, auth, signup  # noqa: F401

ORIGIN = "http://localhost:5173"


@pytest.fixture()
def app(app):
    @app.get("/_creative_only")
    @role_required("creative")
    def creative_only():
        return jsonify({"ok": True})

    return app


def test_signup_success(client, app):
    res = signup(client)
    assert res.status_code == 200
    data = res.get_json()
    user = data["user"]
    assert set(user) == {"id", "email", "displayName", "role", "createdAt"}
    assert user["email"] == "ada@example.com"
    assert user["displayName"] == "Ada" and user["role"] == "storyteller"
    claims = jwt.decode(data["accessToken"], SECRET, algorithms=["HS256"])
    assert claims["sub"] == user["id"]
    stored = db.session.get(User, uuid.UUID(user["id"]))
    assert stored.password_hash != "password123"


def test_signup_duplicate_email_case_insensitive(client):
    assert signup(client).status_code == 200
    res = signup(client, email="ADA@example.com")
    assert res.status_code == 409
    assert "message" in res.get_json()


@pytest.mark.parametrize(
    "overrides",
    [
        {"password": "short"},
        {"password": "x" * 73},
        {"name": "   "},
        {"email": "not-an-email"},
        {"account_type": "admin"},
    ],
)
def test_signup_validation(client, overrides):
    res = signup(client, **overrides)
    assert res.status_code == 400
    assert res.get_json()["message"]


def test_signup_non_json(client):
    res = client.post("/api/auth/signup", data="nope")
    assert res.status_code == 400
    assert "message" in res.get_json()


def test_login(client):
    signup(client)
    res = client.post("/api/auth/login", json={"email": " ADA@example.com ", "password": "password123"})
    assert res.status_code == 200
    token = res.get_json()["accessToken"]
    assert client.get("/api/auth/me", headers=auth(token)).status_code == 200


def test_login_failures_same_message(client):
    signup(client)
    bad_pw = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "wrongpass1"})
    unknown = client.post("/api/auth/login", json={"email": "who@example.com", "password": "password123"})
    assert bad_pw.status_code == unknown.status_code == 401
    assert bad_pw.get_json() == unknown.get_json() == {"message": "Invalid email or password"}
    assert client.post("/api/auth/login", json={"email": "a@b.co"}).status_code == 400


def test_me(client):
    token = signup(client).get_json()["accessToken"]
    res = client.get("/api/auth/me", headers=auth(token))
    assert res.status_code == 200
    assert res.get_json()["email"] == "ada@example.com"


def test_me_unauthorized_cases(client, app):
    token = signup(client).get_json()["accessToken"]
    expired = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": int(time.time()) - 10}, SECRET, algorithm="HS256"
    )
    ghost = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": int(time.time()) + 100}, SECRET, algorithm="HS256"
    )
    cases = [
        {},
        {"Authorization": token},
        {"Authorization": "Basic abc"},
        auth(token[:-2] + "xx"),
        auth(expired),
        auth(ghost),
    ]
    for headers in cases:
        res = client.get("/api/auth/me", headers=headers)
        assert res.status_code == 401, headers
        assert "message" in res.get_json()


def test_me_deleted_user(client):
    data = signup(client).get_json()
    db.session.delete(db.session.get(User, uuid.UUID(data["user"]["id"])))
    db.session.commit()
    assert client.get("/api/auth/me", headers=auth(data["accessToken"])).status_code == 401


def test_json_errors(client):
    res = client.get("/nope")
    assert res.status_code == 404 and "message" in res.get_json()
    res = client.get("/api/auth/login")
    assert res.status_code == 405 and "message" in res.get_json()


def test_cors_preflight(client):
    res = client.options(
        "/api/auth/me",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert res.status_code == 200
    assert res.headers["Access-Control-Allow-Origin"] == ORIGIN
    assert "authorization" in res.headers["Access-Control-Allow-Headers"].lower()


def test_role_required(client):
    token = signup(client).get_json()["accessToken"]
    assert client.get("/_creative_only", headers=auth(token)).status_code == 403
    assert client.get("/_creative_only").status_code == 401
    creative = signup(client, email="c@example.com", account_type="creative").get_json()
    assert client.get("/_creative_only", headers=auth(creative["accessToken"])).status_code == 200
