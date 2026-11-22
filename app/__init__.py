from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from app.config import Config
from app.extensions import db, migrate

DEFAULT_MESSAGES = {
    400: "Bad request",
    401: "Authentication required",
    403: "You do not have permission to do that",
    404: "Resource not found",
    405: "Method not allowed",
}


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    db.init_app(app)
    migrate.init_app(app, db)
    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        allow_headers=["Authorization", "Content-Type"],
        methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    )

    from app import models  # noqa: F401
    from app.adaptation_requests.routes import bp as requests_bp
    from app.auth.routes import bp as auth_bp
    from app.listings.routes import bp as listings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(listings_bp)
    app.register_blueprint(requests_bp)

    @app.errorhandler(HTTPException)
    def handle_http(err):
        return jsonify({"message": DEFAULT_MESSAGES.get(err.code, err.name)}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        app.logger.exception(err)
        db.session.rollback()
        return jsonify({"message": "Internal server error"}), 500

    return app
