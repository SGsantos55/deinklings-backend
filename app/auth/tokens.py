import uuid
from datetime import datetime, timezone

import jwt
from flask import current_app


def create_access_token(user_id) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + current_app.config["JWT_EXPIRES"],
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_access_token(token: str):
    """Return the user UUID from a valid token, or None if invalid/expired."""
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
