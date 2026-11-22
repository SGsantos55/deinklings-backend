import uuid

import pytest

from app.extensions import db
from app.models import AdaptationRequest, Listing
from tests.helpers import auth, signup
from tests.test_listings import create, make_user

URL = "/api/adaptation-requests"
KEYS = {
    "id", "listingId", "listingTitle", "requesterId", "requesterName", "ownerId", "ownerName",
    "medium", "message", "status", "createdAt", "respondedAt",
}
MSG = "I would love to adapt this."


def send(client, headers, lid, **overrides):
    body = {"listing_id": lid, "medium": "Short film", "message": MSG}
    body.update(overrides)
    return client.post(URL, json=body, headers=headers)


@pytest.fixture()
def world(client):
    owner, owner_user = make_user(client, "owner@example.com", name="Olive")
    creative, creative_user = make_user(client, "c@example.com", role="creative", name="Cleo")
    other, _ = make_user(client, "o2@example.com", role="creative", name="Dan")
    listing = create(client, owner).get_json()
    return {"owner": owner, "creative": creative, "other": other, "listing": listing,
            "owner_user": owner_user, "creative_user": creative_user}


def test_create(client, world):
    res = send(client, world["creative"], world["listing"]["id"],
               owner_id=str(uuid.uuid4()), status="accepted")
    assert res.status_code == 201
    data = res.get_json()
    assert set(data) == KEYS
    assert data["status"] == "pending" and data["respondedAt"] is None
    assert data["ownerId"] == world["owner_user"]["id"]
    assert data["requesterId"] == world["creative_user"]["id"]
    assert (data["listingTitle"], data["ownerName"], data["requesterName"]) == (
        world["listing"]["title"], "Olive", "Cleo")


def test_create_auth_and_roles(client, world):
    lid = world["listing"]["id"]
    assert send(client, world["owner"], lid).status_code == 403
    assert client.post(URL, json={}).status_code == 401


@pytest.mark.parametrize(
    "overrides",
    [{"listing_id": "nope"}, {"listing_id": None}, {"medium": "  "}, {"message": "short"},
     {"message": "x" * 1501}, {"message": 5}],
)
def test_create_validation(client, world, overrides):
    res = send(client, world["creative"], world["listing"]["id"], **overrides)
    assert res.status_code == 400 and res.get_json()["message"]


def test_create_non_json_and_unknown_listing(client, world):
    assert client.post(URL, data="x", headers=world["creative"]).status_code == 400
    assert send(client, world["creative"], str(uuid.uuid4())).status_code == 404


def test_create_closed_listing(client, world):
    closed = create(client, world["owner"], openToAdaptation=False).get_json()
    assert send(client, world["creative"], closed["id"]).status_code == 400


def test_duplicate_pending(client, world):
    lid = world["listing"]["id"]
    assert send(client, world["creative"], lid).status_code == 201
    assert send(client, world["creative"], lid).status_code == 409
    assert send(client, world["creative"], lid, medium="Podcast").status_code == 201
    assert send(client, world["other"], lid).status_code == 201


def test_sent_and_received(client, world):
    lid = world["listing"]["id"]
    send(client, world["creative"], lid)
    send(client, world["other"], lid)
    sent = client.get(f"{URL}/sent", headers=world["creative"]).get_json()
    assert len(sent) == 1 and sent[0]["requesterName"] == "Cleo"
    received = client.get(f"{URL}/received", headers=world["owner"]).get_json()
    assert len(received) == 2
    assert client.get(f"{URL}/received", headers=world["creative"]).get_json() == []
    assert client.get(f"{URL}/sent", headers=world["owner"]).get_json() == []
    assert client.get(f"{URL}/sent").status_code == 401
    assert client.get(f"{URL}/received").status_code == 401


def test_respond(client, world):
    rid = send(client, world["creative"], world["listing"]["id"]).get_json()["id"]
    url = f"{URL}/{rid}"
    assert client.patch(url, json={"status": "accepted"}, headers=world["creative"]).status_code == 403
    assert client.patch(url, json={"status": "accepted"}, headers=world["other"]).status_code == 403
    assert client.patch(url, json={"status": "accepted"}).status_code == 401
    assert client.patch(f"{URL}/{uuid.uuid4()}", json={"status": "accepted"},
                        headers=world["owner"]).status_code == 404
    assert client.patch(f"{URL}/bad-id", json={"status": "accepted"},
                        headers=world["owner"]).status_code == 404
    for bad in ({}, {"status": "pending"}, {"status": "maybe"}):
        assert client.patch(url, json=bad, headers=world["owner"]).status_code == 400
    assert client.patch(url, data="x", headers=world["owner"]).status_code == 400

    res = client.patch(url, json={"status": "declined"}, headers=world["owner"])
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "declined" and data["respondedAt"]

    again = client.patch(url, json={"status": "accepted"}, headers=world["owner"])
    assert again.status_code == 409
    assert db.session.get(AdaptationRequest, uuid.UUID(rid)).status == "declined"


def test_listing_cascade(client, world):
    if db.engine.dialect.name != "postgresql":
        pytest.skip("FK cascade is enforced by PostgreSQL")
    send(client, world["creative"], world["listing"]["id"])
    db.session.delete(db.session.get(Listing, uuid.UUID(world["listing"]["id"])))
    db.session.commit()
    assert db.session.query(AdaptationRequest).count() == 0
