import uuid
from datetime import datetime, timezone

from sqlalchemy import Enum, text

from app.extensions import db

ROLES = ("storyteller", "creative")


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
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return {
            "id": str(self.id),
            "email": self.email,
            "displayName": self.display_name,
            "role": self.role,
            "createdAt": created.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
