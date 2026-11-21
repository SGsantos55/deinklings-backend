from functools import wraps

from flask import g, jsonify, request

from app.auth.tokens import decode_access_token
from app.extensions import db
from app.models import User


def _unauthorized():
    return jsonify({"message": "Authentication required"}), 401


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return _unauthorized()
        user_id = decode_access_token(parts[1])
        if user_id is None:
            return _unauthorized()
        user = db.session.get(User, user_id)
        if user is None:
            return _unauthorized()
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapper


def role_required(*roles):
    def decorator(fn):
        @login_required
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if g.current_user.role not in roles:
                return jsonify({"message": "You do not have permission to do that"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator
