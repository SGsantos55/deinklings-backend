import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/deinklings"
    )
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
    JWT_EXPIRES = timedelta(days=int(os.environ.get("JWT_EXPIRES_DAYS", 7)))
    CORS_ORIGINS = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
        if o.strip()
    ]
