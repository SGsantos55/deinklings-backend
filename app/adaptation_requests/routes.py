import uuid
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError

from app.auth.decorators import login_required, role_required
from app.extensions import db
from app.models import AdaptationRequest, Listing

bp = Blueprint("adaptation_requests", __name__, url_prefix="/api/adaptation-requests")


def _error(message, status):
    return jsonify({"message": message}), status


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _serialize(items):
    return jsonify([i.to_dict() for i in items])


def _newest_first(query):
    return query.order_by(AdaptationRequest.created_at.desc(), AdaptationRequest.id)


@bp.post("")
@role_required("creative")
def create_request():
    data = _json_body()
    if data is None:
        return _error("Request body must be a JSON object", 400)

    raw_id, medium, message = data.get("listing_id"), data.get("medium"), data.get("message")
    try:
        listing_id = uuid.UUID(raw_id) if isinstance(raw_id, str) else None
    except ValueError:
        listing_id = None
    if listing_id is None:
        return _error("A valid listing_id is required", 400)
    if not isinstance(medium, str) or not medium.strip():
        return _error("Please choose a medium", 400)
    if not isinstance(message, str) or not 10 <= len(message.strip()) <= 1500:
        return _error("Your message must be between 10 and 1500 characters", 400)
    medium, message = medium.strip(), message.strip()

    listing = db.session.get(Listing, listing_id)
    if listing is None:
        return _error("Listing not found", 404)
    if not listing.open_to_adaptation:
        return _error("This story isn't open to adaptation requests", 400)

    duplicate = AdaptationRequest.query.filter_by(
        listing_id=listing.id, requester_id=g.current_user.id, medium=medium, status="pending"
    ).first()
    if duplicate:
        return _error("You already have a pending request for this story and medium", 409)

    item = AdaptationRequest(
        listing_id=listing.id,
        requester_id=g.current_user.id,
        owner_id=listing.owner_id,
        medium=medium,
        message=message,
    )
    db.session.add(item)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error("Could not create the request", 400)
    return jsonify(item.to_dict()), 201


@bp.get("/sent")
@login_required
def sent():
    query = AdaptationRequest.query.filter_by(requester_id=g.current_user.id)
    return _serialize(_newest_first(query).all())


@bp.get("/received")
@login_required
def received():
    query = AdaptationRequest.query.filter_by(owner_id=g.current_user.id)
    return _serialize(_newest_first(query).all())


@bp.patch("/<uuid:request_id>")
@login_required
def respond(request_id):
    item = db.session.get(AdaptationRequest, request_id)
    if item is None:
        return _error("Request not found", 404)
    if item.owner_id != g.current_user.id:
        return _error("Only the story's owner can respond to this request", 403)

    data = _json_body()
    if data is None:
        return _error("Request body must be a JSON object", 400)
    status = data.get("status")
    if status not in ("accepted", "declined"):
        return _error("Status must be 'accepted' or 'declined'", 400)
    if item.status != "pending":
        return _error("This request has already been answered", 409)

    item.status = status
    item.responded_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(item.to_dict())
