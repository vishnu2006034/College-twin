from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.schema import metadata


def test_constraint_names_are_unique_and_postgres_ddl_compiles():
    for table in metadata.sorted_tables:
        names = [constraint.name for constraint in table.constraints if constraint.name]
        assert len(names) == len(set(names)), f"Duplicate constraint names in {table.name}"
        assert str(CreateTable(table).compile(dialect=postgresql.dialect()))
