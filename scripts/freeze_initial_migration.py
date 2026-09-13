"""Development helper: capture immutable M1 DDL from the initial metadata once."""
from pathlib import Path

from sqlalchemy import create_mock_engine

from app.schema import DOMAIN_TABLES, metadata

target = Path("migrations/versions/0001_foundation.py")
if target.exists():
    raise SystemExit("Initial migration already exists; create a new revision instead")
statements = []
mock = create_mock_engine("postgresql://", lambda sql, *args, **kwargs: statements.append(str(sql.compile(dialect=mock.dialect))))
metadata.create_all(mock)
domain_names = [table.name for table in DOMAIN_TABLES]
body = '''"""M1 foundation: frozen DDL, independent of future application metadata."""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
'''
for statement in statements:
    body += f"    op.execute({statement!r})\n"
freeze_function = """
CREATE FUNCTION protect_frozen_domain() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE target_edition uuid;
BEGIN
    IF TG_OP = 'DELETE' THEN target_edition := OLD.edition_id;
    ELSE target_edition := NEW.edition_id; END IF;
    IF EXISTS (SELECT 1 FROM dataset_edition WHERE id=target_edition AND frozen_at IS NOT NULL)
       OR (TG_OP='UPDATE' AND EXISTS (SELECT 1 FROM dataset_edition WHERE id=OLD.edition_id AND frozen_at IS NOT NULL)) THEN
        RAISE EXCEPTION 'Frozen edition is immutable';
    END IF;
    IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$
"""
body += f"    op.execute({freeze_function!r})\n"
for name in domain_names:
    trigger = f"CREATE TRIGGER freeze_{name} BEFORE INSERT OR UPDATE OR DELETE ON {name} FOR EACH ROW EXECUTE FUNCTION protect_frozen_domain()"
    body += f"    op.execute({trigger!r})\n"
edition_function = """
CREATE FUNCTION protect_frozen_edition() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.frozen_at IS NOT NULL THEN RAISE EXCEPTION 'Frozen edition is immutable'; END IF;
    IF TG_OP='DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
END $$
"""
body += f"    op.execute({edition_function!r})\n"
body += "    op.execute('CREATE TRIGGER freeze_edition BEFORE UPDATE OR DELETE ON dataset_edition FOR EACH ROW EXECUTE FUNCTION protect_frozen_edition()')\n"
body += "\ndef downgrade():\n"
for table in reversed(metadata.sorted_tables):
    body += f"    op.drop_table({table.name!r})\n"
body += "    op.execute('DROP FUNCTION protect_frozen_domain()')\n"
body += "    op.execute('DROP FUNCTION protect_frozen_edition()')\n"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(body, encoding="utf-8")
print(f"Created {target}")
