"""Reviewed, edition-scoped campus room mappings."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "room_mapping",
        sa.Column("edition_id", sa.Uuid, sa.ForeignKey("dataset_edition.id"), primary_key=True),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("bindings", JSONB, nullable=False),
        sa.Column("reviewed_by", sa.Uuid, sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_note", sa.String(1000), nullable=False),
        sa.CheckConstraint("version > 0", name="positive_version"),
    )


def downgrade():
    op.drop_table("room_mapping")
