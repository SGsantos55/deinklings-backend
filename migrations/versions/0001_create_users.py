"""create users table

Revision ID: 0001
Revises:
Create Date: 2026-11-21
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("create extension if not exists pgcrypto")
    app_role = postgresql.ENUM("storyteller", "creative", name="app_role")
    app_role.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "role", postgresql.ENUM("storyteller", "creative", name="app_role", create_type=False), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade():
    op.drop_table("users")
    postgresql.ENUM(name="app_role").drop(op.get_bind(), checkfirst=True)
