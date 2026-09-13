from alembic import context

from app.db import engine
from app.schema import metadata

if context.is_offline_mode():
    context.configure(url="postgresql://", target_metadata=metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine().connect() as connection:
        context.configure(connection=connection, target_metadata=metadata)
        with context.begin_transaction():
            context.run_migrations()
