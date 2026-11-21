import uuid

import pytest

from app.extensions import db
from app.models import Listing, User
from tests.helpers import auth, signup

LISTING_KEYS = {
    "id", "ownerId", "ownerName", "ownerNote", "title", "format", "genre", "mood", "body",
    "logline", "synopsis", "tags", "mediums", "openToAdaptation", "openToCollaboration",
    "openToLicensing", "coverUrl", "createdAt",
}


def payload(**overrides):
    data = {
        "title": "The Last Bus Home",
        "format": "Short Story",
        "genre": "Drama",
        "mood": "Tender",
        "body": "The 11:40 is never full. " * 20,
        "logline": "Two strangers share one final journey.",
        "synopsis": "A quiet story about two strangers on the last bus home. " * 3,
        "tags": ["Character-driven", "Family"],
        "mediums": ["Short film", "Podcast"],
        "openToAdaptation": True,
        "openToCollaboration": False,
        "openToLicensing": False,
    }
    data.update(overrides)
    return data


def make_user(client, email, role="storyteller", name="Ada"):
    data = signup(client, email=email, account_type=role, name=name).get_json()
    return auth(data["accessToken"]), data["user"]


def create(client, headers, **overrides):
    return client.post("/api/listings", json=payload(**overrides), headers=headers)


def test_create_listing(client):
    headers, user = make_user(client, "a@example.com")
    res = create(client, headers, ownerId=str(uuid.uuid4()))
    assert res.status_code == 201
    data = res.get_json()
    assert set(data) == LISTING_KEYS
    assert data["ownerId"] == user["id"] and data["ownerName"] == "Ada"
    assert data["ownerNote"] == "" and data["coverUrl"] is None
    assert data["tags"] == ["Character-driven", "Family"]
    assert data["createdAt"].endswith("Z")


def test_create_defaults(client):
    headers, _ = make_user(client, "a@example.com")
    body = payload()
    for key in ("mood", "tags", "openToAdaptation", "openToCollaboration", "openToLicensing"):
        del body[key]
    data = client.post("/api/listings", json=body, headers=headers).get_json()
    assert data["mood"] == "" and data["tags"] == []
    assert (data["openToAdaptation"], data["openToCollaboration"], data["openToLicensing"]) == (True, False, False)


def test_create_requires_storyteller(client):
    creative, _ = make_user(client, "c@example.com", role="creative")
    assert create(client, creative).status_code == 403
    assert client.post("/api/listings", json=payload()).status_code == 401


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": "  "},
        {"title": "x" * 121},
        {"format": ""},
        {"body": "short"},
        {"logline": "tiny"},
        {"logline": "x" * 161},
        {"synopsis": "too short"},
        {"synopsis": "x" * 2001},
        {"mediums": []},
        {"tags": ["t"] * 7},
        {"tags": "not-a-list"},
        {"tags": ["x" * 41]},
        {"openToAdaptation": "yes"},
        {"mood": 5},
    ],
)
def test_create_validation(client, overrides):
    headers, _ = make_user(client, "a@example.com")
    res = create(client, headers, **overrides)
    assert res.status_code == 400
    assert res.get_json()["message"]


def test_create_non_json(client):
    headers, _ = make_user(client, "a@example.com")
    assert client.post("/api/listings", data="nope", headers=headers).status_code == 400


def test_get_listing_public(client):
    headers, _ = make_user(client, "a@example.com")
    listing_id = create(client, headers).get_json()["id"]
    res = client.get(f"/api/listings/{listing_id}")
    assert res.status_code == 200 and res.get_json()["id"] == listing_id
    assert client.get(f"/api/listings/{uuid.uuid4()}").status_code == 404
    bad = client.get("/api/listings/not-a-uuid")
    assert bad.status_code == 404 and "message" in bad.get_json()


def test_list_filters(client):
    headers, _ = make_user(client, "a@example.com", name="Ada Lovelace")
    create(client, headers, title="Bus Story", format="Short Story", genre="Drama", mood="Tender",
           mediums=["Short film"], tags=["Family"])
    create(client, headers, title="Robot 100% Heart", format="Novel", genre="Science fiction",
           mood="Dark", mediums=["Anime", "Game"], tags=[], logline="A robot learns to feel again.")

    def titles(query=""):
        res = client.get(f"/api/listings{query}")
        assert res.status_code == 200
        return [item["title"] for item in res.get_json()]

    assert titles() == ["Robot 100% Heart", "Bus Story"]  # newest first
    assert titles("?format=novel") == ["Robot 100% Heart"]
    assert titles("?genre=drama") == ["Bus Story"]
    assert titles("?mood=DARK") == ["Robot 100% Heart"]
    assert titles("?adaptation_type=game") == ["Robot 100% Heart"]
    assert titles("?adaptation_type=Short film") == ["Bus Story"]
    assert titles("?q=robot") == ["Robot 100% Heart"]
    assert titles("?q=family") == ["Bus Story"]
    assert titles("?q=lovelace") == ["Robot 100% Heart", "Bus Story"]
    assert titles("?q=100%25") == ["Robot 100% Heart"]
    assert titles("?q=%25") == ["Robot 100% Heart"]
    assert titles("?format=Novel&genre=Drama") == []
    assert titles("?format=&q=") == ["Robot 100% Heart", "Bus Story"]


def test_mine(client):
    a, _ = make_user(client, "a@example.com")
    b, _ = make_user(client, "b@example.com")
    creative, _ = make_user(client, "c@example.com", role="creative")
    create(client, a, title="Mine")
    create(client, b, title="Theirs")
    res = client.get("/api/listings/mine?genre=nothing", headers=a)
    assert [i["title"] for i in res.get_json()] == ["Mine"]
    assert client.get("/api/listings/mine", headers=creative).get_json() == []
    assert client.get("/api/listings/mine").status_code == 401


def test_patch(client):
    owner, _ = make_user(client, "a@example.com")
    other, _ = make_user(client, "b@example.com")
    listing = create(client, owner).get_json()
    url = f"/api/listings/{listing['id']}"

    res = client.patch(url, json={"title": "New Title", "openToLicensing": True, "ownerId": "x"}, headers=owner)
    assert res.status_code == 200
    data = res.get_json()
    assert data["title"] == "New Title" and data["openToLicensing"] is True
    assert data["genre"] == listing["genre"] and data["ownerId"] == listing["ownerId"]

    assert client.patch(url, json={}, headers=owner).status_code == 200
    assert client.patch(url, json={"mediums": []}, headers=owner).status_code == 400
    assert client.patch(url, json={"logline": "x"}, headers=owner).status_code == 400
    assert client.patch(url, json={"title": "Hack"}, headers=other).status_code == 403
    assert client.patch(url, json={"title": "Hack"}).status_code == 401
    assert client.patch(f"/api/listings/{uuid.uuid4()}", json={}, headers=owner).status_code == 404


def test_delete(client):
    owner, _ = make_user(client, "a@example.com")
    other, _ = make_user(client, "b@example.com")
    listing_id = create(client, owner).get_json()["id"]
    url = f"/api/listings/{listing_id}"

    assert client.delete(url, headers=other).status_code == 403
    assert client.delete(url).status_code == 401
    res = client.delete(url, headers=owner)
    assert res.status_code == 204 and res.data == b""
    assert client.get(url).status_code == 404
    assert client.delete(url, headers=owner).status_code == 404


def test_owner_cascade(client):
    if db.engine.dialect.name != "postgresql":
        pytest.skip("FK cascade is enforced by PostgreSQL (SQLite needs a pragma)")
    headers, user = make_user(client, "a@example.com")
    create(client, headers)
    db.session.delete(db.session.get(User, uuid.UUID(user["id"])))
    db.session.commit()
    assert db.session.query(Listing).count() == 0
