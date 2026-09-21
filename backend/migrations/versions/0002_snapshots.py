"""Frozen M2 snapshot storage."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "state_snapshot",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("edition_id", sa.Uuid, sa.ForeignKey("dataset_edition.id"), nullable=False),
        sa.Column("created_by", sa.Uuid, sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("canonical_inputs", JSONB, nullable=False),
        sa.Column("response", JSONB, nullable=False),
        sa.UniqueConstraint("created_by", "idempotency_key"),
    )
    op.execute("""
        CREATE FUNCTION reject_snapshot_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Snapshots are immutable'; END; $$;
        CREATE TRIGGER immutable_snapshot BEFORE UPDATE OR DELETE ON state_snapshot
        FOR EACH ROW EXECUTE FUNCTION reject_snapshot_mutation();
    """)


def downgrade():
    op.drop_table("state_snapshot")
    op.execute("DROP FUNCTION reject_snapshot_mutation()")
