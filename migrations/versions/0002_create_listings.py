"""create listings table

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "listings",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("format", sa.Text(), nullable=False),
        sa.Column("genre", sa.Text(), nullable=False),
        sa.Column("mood", sa.Text(), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("logline", sa.Text(), nullable=False),
        sa.Column("synopsis", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("mediums", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("open_to_adaptation", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("open_to_collaboration", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("open_to_licensing", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cover_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("char_length(title) between 1 and 120", name="listings_title_check"),
        sa.CheckConstraint("char_length(logline) <= 160", name="listings_logline_check"),
        sa.CheckConstraint("char_length(synopsis) <= 2000", name="listings_synopsis_check"),
    )
    op.create_index("listings_owner_id_idx", "listings", ["owner_id"])
    op.create_index("listings_format_idx", "listings", ["format"])
    op.create_index("listings_genre_idx", "listings", ["genre"])


def downgrade():
    op.drop_index("listings_genre_idx", table_name="listings")
    op.drop_index("listings_format_idx", table_name="listings")
    op.drop_index("listings_owner_id_idx", table_name="listings")
    op.drop_table("listings")
