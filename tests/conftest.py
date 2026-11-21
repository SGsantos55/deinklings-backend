import os

import pytest
from sqlalchemy import text

from app import create_app
from app.extensions import db

TEST_SCHEMA = "test_auth"
SECRET = "test-secret-key-for-hs256-at-least-32-bytes"


@pytest.fixture()
def app():
    # Set TEST_DATABASE_URL to run against PostgreSQL (isolated schema); defaults to SQLite.
    pg_url = os.environ.get("TEST_DATABASE_URL")
    config = {"TESTING": True, "JWT_SECRET_KEY": SECRET}
    if pg_url:
        config["SQLALCHEMY_DATABASE_URI"] = pg_url
        config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"options": f"-csearch_path={TEST_SCHEMA}"}}
    else:
        config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app = create_app(config)

    with app.app_context():
        if pg_url:
            db.session.execute(text(f"drop schema if exists {TEST_SCHEMA} cascade"))
            db.session.execute(text(f"create schema {TEST_SCHEMA}"))
            db.session.execute(text("create type app_role as enum ('storyteller', 'creative')"))
            db.session.commit()
        db.create_all()
        yield app
        db.session.remove()
        if pg_url:
            db.session.execute(text(f"drop schema {TEST_SCHEMA} cascade"))
            db.session.commit()
        else:
            db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
