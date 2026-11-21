from flask import Blueprint, g, jsonify, request
from sqlalchemy import Text, cast, exists, func, or_, select, text

from app.auth.decorators import login_required, role_required
from app.extensions import db
from app.listings.validation import validate_listing
from app.models import Listing, User

bp = Blueprint("listings", __name__, url_prefix="/api/listings")


def _error(message, status):
    return jsonify({"message": message}), status


def _json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _escape_like(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _medium_filter(value):
    if db.engine.dialect.name == "postgresql":
        sql = "EXISTS (SELECT 1 FROM unnest(listings.mediums) m WHERE lower(m) = :v)"
    else:
        sql = "EXISTS (SELECT 1 FROM json_each(listings.mediums) je WHERE lower(je.value) = :v)"
    return text(sql).bindparams(v=value.lower())


def _search_filter(term):
    pattern = f"%{_escape_like(term)}%"
    if db.engine.dialect.name == "postgresql":
        tags = func.array_to_string(Listing.tags, " ")
    else:
        tags = cast(Listing.tags, Text)
    columns = (Listing.title, Listing.logline, Listing.synopsis, tags, User.display_name)
    return or_(*(c.ilike(pattern, escape="\\") for c in columns))


def _serialize(listings):
    return jsonify([item.to_dict() for item in listings])


def _newest_first(query):
    return query.order_by(Listing.created_at.desc(), Listing.id)


@bp.get("")
def list_listings():
    args = request.args
    query = Listing.query.join(User, Listing.owner_id == User.id)

    q = args.get("q", "").strip()
    if q:
        query = query.filter(_search_filter(q))
    for param, column in (("format", Listing.format), ("genre", Listing.genre), ("mood", Listing.mood)):
        value = args.get(param, "").strip()
        if value:
            query = query.filter(func.lower(column) == value.lower())
    medium = args.get("adaptation_type", "").strip()
    if medium:
        query = query.filter(_medium_filter(medium))

    return _serialize(_newest_first(query).all())


@bp.get("/mine")
@login_required
def my_listings():
    query = Listing.query.filter(Listing.owner_id == g.current_user.id)
    return _serialize(_newest_first(query).all())


@bp.get("/<uuid:listing_id>")
def get_listing(listing_id):
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        return _error("Listing not found", 404)
    return jsonify(listing.to_dict())


@bp.post("")
@role_required("storyteller")
def create_listing():
    data = _json_body()
    if data is None:
        return _error("Request body must be a JSON object", 400)
    clean, err = validate_listing(data)
    if err:
        return _error(err, 400)

    listing = Listing(owner_id=g.current_user.id, **clean)
    db.session.add(listing)
    db.session.commit()
    return jsonify(listing.to_dict()), 201


def _owned_listing(listing_id):
    """Return (listing, error_response); enforces 404 then 403."""
    listing = db.session.get(Listing, listing_id)
    if listing is None:
        return None, _error("Listing not found", 404)
    if listing.owner_id != g.current_user.id:
        return None, _error("You can only change your own listings", 403)
    return listing, None


@bp.patch("/<uuid:listing_id>")
@login_required
def update_listing(listing_id):
    listing, error = _owned_listing(listing_id)
    if error:
        return error
    data = _json_body()
    if data is None:
        return _error("Request body must be a JSON object", 400)
    clean, err = validate_listing(data, partial=True)
    if err:
        return _error(err, 400)

    for column, value in clean.items():
        setattr(listing, column, value)
    db.session.commit()
    return jsonify(listing.to_dict())


@bp.delete("/<uuid:listing_id>")
@login_required
def delete_listing(listing_id):
    listing, error = _owned_listing(listing_id)
    if error:
        return error
    db.session.delete(listing)
    db.session.commit()
    return "", 204
