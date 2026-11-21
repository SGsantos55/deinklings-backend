import re

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth.decorators import login_required
from app.auth.tokens import create_access_token
from app.extensions import db
from app.models import ROLES, User

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _error(message, status):
    return jsonify({"message": message}), status


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _str(data, key):
    value = data.get(key)
    return value.strip() if isinstance(value, str) else ""


def _auth_response(user):
    return jsonify({"accessToken": create_access_token(user.id), "user": user.to_dict()})


@bp.post("/signup")
def signup():
    data = _body()
    if data is None:
        return _error("Request body must be a JSON object", 400)

    name = _str(data, "name")
    email = _str(data, "email").lower()
    password = data.get("password")
    account_type = data.get("account_type")

    if not 1 <= len(name) <= 80:
        return _error("Name must be between 1 and 80 characters", 400)
    if not email or len(email) > 255 or not EMAIL_RE.match(email):
        return _error("Please enter a valid email address", 400)
    if not isinstance(password, str) or not 8 <= len(password) <= 72:
        return _error("Password must be between 8 and 72 characters", 400)
    if account_type not in ROLES:
        return _error("Account type must be 'storyteller' or 'creative'", 400)

    if User.query.filter_by(email=email).first():
        return _error("An account with this email already exists", 409)

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        display_name=name,
        role=account_type,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return _error("An account with this email already exists", 409)
    return _auth_response(user)


@bp.post("/login")
def login():
    data = _body()
    if data is None:
        return _error("Request body must be a JSON object", 400)

    email = _str(data, "email").lower()
    password = data.get("password")
    if not email or not isinstance(password, str) or not password:
        return _error("Email and password are required", 400)

    user = User.query.filter_by(email=email).first()
    if user is None or not check_password_hash(user.password_hash, password):
        return _error("Invalid email or password", 401)
    return _auth_response(user)


@bp.get("/me")
@login_required
def me():
    return jsonify(g.current_user.to_dict())
