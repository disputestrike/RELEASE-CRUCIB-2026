"""Add database indexes

Revision ID: 002_add_indexes
Revises: 001_add_foreign_keys
Create Date: 2026-03-02

"""
from alembic import op

revision = "002_add_indexes"
down_revision = "001_add_foreign_keys"

def upgrade() -> None:
    op.execute("CREATE INDEX idx_users_email ON users(email);")
    op.execute("CREATE INDEX idx_users_google_id ON users(google_id);")
    op.execute("CREATE INDEX idx_projects_user_id ON projects(user_id);")
    op.execute("CREATE INDEX idx_builds_project_id ON builds(project_id);")
    op.execute("CREATE INDEX idx_builds_user_id ON builds(user_id);")
    op.execute("CREATE INDEX idx_builds_status ON builds(status);")
    op.execute("CREATE INDEX idx_payments_user_id ON payments(user_id);")
    op.execute("CREATE INDEX idx_payments_stripe_session ON payments(stripe_session_id);")
    op.execute("CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);")
    op.execute("CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);")

def downgrade() -> None:
    op.execute("DROP INDEX idx_users_email;")
    op.execute("DROP INDEX idx_users_google_id;")
    op.execute("DROP INDEX idx_projects_user_id;")
    op.execute("DROP INDEX idx_builds_project_id;")
    op.execute("DROP INDEX idx_builds_user_id;")
    op.execute("DROP INDEX idx_builds_status;")
    op.execute("DROP INDEX idx_payments_user_id;")
    op.execute("DROP INDEX idx_payments_stripe_session;")
    op.execute("DROP INDEX idx_audit_logs_user_id;")
    op.execute("DROP INDEX idx_audit_logs_created_at;")
