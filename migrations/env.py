"""Alembic environment configuration"""
import os
from alembic import context

def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = os.getenv('DATABASE_URL')
    context.configure(url=url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
