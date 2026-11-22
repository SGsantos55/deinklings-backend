import uuid
from datetime import datetime, timezone

from sqlalchemy import Enum, text
from sqlalchemy.dialects.postgresql import ARRAY

from app.extensions import db

ROLES = ("storyteller", "creative")


def _iso(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(
        db.Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    display_name = db.Column(db.Text, nullable=False, default="", server_default="")
    role = db.Column(Enum(*ROLES, name="app_role", create_type=False), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "email": self.email,
            "displayName": self.display_name,
            "role": self.role,
            "createdAt": _iso(self.created_at),
        }


# Postgres text[] in production; JSON so the same model works on SQLite in tests.
TextArray = ARRAY(db.Text).with_variant(db.JSON, "sqlite")


class Listing(db.Model):
    __tablename__ = "listings"

    id = db.Column(
        db.Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    owner_id = db.Column(
        db.Uuid, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = db.Column(db.Text, nullable=False)
    format = db.Column(db.Text, nullable=False)
    genre = db.Column(db.Text, nullable=False)
    mood = db.Column(db.Text, nullable=False, default="", server_default="")
    body = db.Column(db.Text, nullable=False)
    logline = db.Column(db.Text, nullable=False)
    synopsis = db.Column(db.Text, nullable=False)
    tags = db.Column(TextArray, nullable=False, default=list, server_default=text("'{}'"))
    mediums = db.Column(TextArray, nullable=False, default=list, server_default=text("'{}'"))
    open_to_adaptation = db.Column(db.Boolean, nullable=False, default=True, server_default=text("true"))
    open_to_collaboration = db.Column(
        db.Boolean, nullable=False, default=False, server_default=text("false")
    )
    open_to_licensing = db.Column(db.Boolean, nullable=False, default=False, server_default=text("false"))
    cover_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )

    owner = db.relationship("User", lazy="joined")

    __table_args__ = (
        db.Index("listings_owner_id_idx", "owner_id"),
        db.Index("listings_format_idx", "format"),
        db.Index("listings_genre_idx", "genre"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "ownerId": str(self.owner_id),
            "ownerName": self.owner.display_name,
            "ownerNote": "",
            "title": self.title,
            "format": self.format,
            "genre": self.genre,
            "mood": self.mood,
            "body": self.body,
            "logline": self.logline,
            "synopsis": self.synopsis,
            "tags": list(self.tags or []),
            "mediums": list(self.mediums or []),
            "openToAdaptation": self.open_to_adaptation,
            "openToCollaboration": self.open_to_collaboration,
            "openToLicensing": self.open_to_licensing,
            "coverUrl": self.cover_url,
            "createdAt": _iso(self.created_at),
        }


class AdaptationRequest(db.Model):
    __tablename__ = "adaptation_requests"

    id = db.Column(
        db.Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    listing_id = db.Column(
        db.Uuid, db.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False
    )
    requester_id = db.Column(
        db.Uuid, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    owner_id = db.Column(db.Uuid, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    medium = db.Column(db.Text, nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False, default="pending", server_default="pending")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
    )
    responded_at = db.Column(db.DateTime(timezone=True), nullable=True)

    listing = db.relationship("Listing", lazy="joined")
    requester = db.relationship("User", foreign_keys=[requester_id], lazy="joined")
    owner = db.relationship("User", foreign_keys=[owner_id], lazy="joined")

    __table_args__ = (
        db.Index("adaptation_requests_owner_id_idx", "owner_id"),
        db.Index("adaptation_requests_requester_id_idx", "requester_id"),
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "listingId": str(self.listing_id),
            "listingTitle": self.listing.title,
            "requesterId": str(self.requester_id),
            "requesterName": self.requester.display_name,
            "ownerId": str(self.owner_id),
            "ownerName": self.owner.display_name,
            "medium": self.medium,
            "message": self.message,
            "status": self.status,
            "createdAt": _iso(self.created_at),
            "respondedAt": _iso(self.responded_at) if self.responded_at else None,
        }
