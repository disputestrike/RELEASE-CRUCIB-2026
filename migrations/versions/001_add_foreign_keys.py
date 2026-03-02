"""Add foreign key constraints

Revision ID: 001_add_foreign_keys
Revises: None
Create Date: 2026-03-02

"""
from alembic import op

revision = "001_add_foreign_keys"
down_revision = None

def upgrade() -> None:
    op.execute("""
        ALTER TABLE projects ADD CONSTRAINT fk_projects_user 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    """)
    op.execute("""
        ALTER TABLE builds ADD CONSTRAINT fk_builds_project 
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;
    """)
    op.execute("""
        ALTER TABLE builds ADD CONSTRAINT fk_builds_user 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    """)
    op.execute("""
        ALTER TABLE payments ADD CONSTRAINT fk_payments_user 
        FOREIGN KEY (user_id) REFERENCES users(id);
    """)
    op.execute("""
        ALTER TABLE api_keys ADD CONSTRAINT fk_api_keys_user 
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    """)

def downgrade() -> None:
    op.execute("ALTER TABLE projects DROP CONSTRAINT fk_projects_user;")
    op.execute("ALTER TABLE builds DROP CONSTRAINT fk_builds_project;")
    op.execute("ALTER TABLE builds DROP CONSTRAINT fk_builds_user;")
    op.execute("ALTER TABLE payments DROP CONSTRAINT fk_payments_user;")
    op.execute("ALTER TABLE api_keys DROP CONSTRAINT fk_api_keys_user;")
