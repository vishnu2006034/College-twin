"""Immutable saved room-closure runs."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "simulation_run",
        sa.Column("id", sa.Uuid, primary_key=True),
        sa.Column("snapshot_id", sa.Uuid, sa.ForeignKey("state_snapshot.id"), nullable=False),
        sa.Column("edition_id", sa.Uuid, sa.ForeignKey("dataset_edition.id"), nullable=False),
        sa.Column("created_by", sa.Uuid, sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("canonical_inputs", JSONB, nullable=False),
        sa.Column("response", JSONB, nullable=False),
        sa.Column("sessions", JSONB, nullable=False),
        sa.UniqueConstraint("created_by", "idempotency_key"),
    )
    op.execute("""
        CREATE TRIGGER immutable_simulation BEFORE UPDATE OR DELETE ON simulation_run
        FOR EACH ROW EXECUTE FUNCTION reject_snapshot_mutation();
        CREATE FUNCTION check_simulation_edition() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM state_snapshot
                         WHERE id=NEW.snapshot_id AND edition_id=NEW.edition_id) THEN
            RAISE EXCEPTION 'Simulation snapshot edition mismatch';
          END IF;
          RETURN NEW;
        END; $$;
        CREATE TRIGGER simulation_edition BEFORE INSERT ON simulation_run
        FOR EACH ROW EXECUTE FUNCTION check_simulation_edition();
    """)


def downgrade():
    op.drop_table("simulation_run")
    op.execute("DROP FUNCTION check_simulation_edition()")
