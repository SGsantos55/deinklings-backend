"""create adaptation_requests table

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-22
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "adaptation_requests",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("listing_id", sa.Uuid(), sa.ForeignKey("listings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requester_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("medium", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "char_length(message) between 10 and 1500", name="adaptation_requests_message_check"
        ),
        sa.CheckConstraint(
            "status in ('pending', 'accepted', 'declined')", name="adaptation_requests_status_check"
        ),
    )
    op.create_index("adaptation_requests_owner_id_idx", "adaptation_requests", ["owner_id"])
    op.create_index("adaptation_requests_requester_id_idx", "adaptation_requests", ["requester_id"])


def downgrade():
    op.drop_index("adaptation_requests_requester_id_idx", table_name="adaptation_requests")
    op.drop_index("adaptation_requests_owner_id_idx", table_name="adaptation_requests")
    op.drop_table("adaptation_requests")
