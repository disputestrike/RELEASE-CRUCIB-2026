"""
CrucibAI Database Initialization & Migration Script
Handles PostgreSQL setup, schema creation, and data initialization
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles database initialization and migrations"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Create connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=20,
                command_timeout=30,
                record_class=dict,
            )
            logger.info("✅ Database connection pool created")
        except Exception as e:
            logger.error(f"❌ Failed to create connection pool: {e}")
            raise

    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ Database connection pool closed")

    async def execute_migration(self, sql: str, description: str):
        """Execute a migration script"""
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(sql)
            logger.info(f"✅ Migration completed: {description}")
            return True
        except Exception as e:
            logger.error(f"❌ Migration failed ({description}): {e}")
            return False

    async def create_schema(self) -> bool:
        """Create all database tables"""

        migrations = [
            # Users table
            (
                """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255),
                oauth_provider VARCHAR(50),
                oauth_id VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                avatar_url TEXT,
                role VARCHAR(50) DEFAULT 'user',
                status VARCHAR(50) DEFAULT 'active',
                mfa_enabled BOOLEAN DEFAULT false,
                mfa_secret VARCHAR(255),
                backup_codes TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            """,
                "Create users table",
            ),
            # Projects table
            (
                """
            CREATE TABLE IF NOT EXISTS projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(50) DEFAULT 'draft',
                type VARCHAR(50),
                visibility VARCHAR(50) DEFAULT 'private',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deployed_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
            """,
                "Create projects table",
            ),
            # Builds table
            (
                """
            CREATE TABLE IF NOT EXISTS builds (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                status VARCHAR(50) DEFAULT 'pending',
                build_time_seconds FLOAT,
                files_generated INTEGER,
                tokens_used INTEGER,
                errors INTEGER DEFAULT 0,
                warnings INTEGER DEFAULT 0,
                quality_score FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_builds_project_id ON builds(project_id);
            CREATE INDEX IF NOT EXISTS idx_builds_user_id ON builds(user_id);
            CREATE INDEX IF NOT EXISTS idx_builds_status ON builds(status);
            """,
                "Create builds table",
            ),
            # API Keys table
            (
                """
            CREATE TABLE IF NOT EXISTS api_keys (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                key_hash VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255),
                last_used TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
            """,
                "Create api_keys table",
            ),
            # Audit logs table
            (
                """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                action VARCHAR(255) NOT NULL,
                resource_type VARCHAR(255),
                resource_id VARCHAR(255),
                details JSONB,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
            """,
                "Create audit_logs table",
            ),
            # Payments table
            (
                """
            CREATE TABLE IF NOT EXISTS payments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                stripe_payment_id VARCHAR(255) UNIQUE,
                amount DECIMAL(10, 2),
                currency VARCHAR(3) DEFAULT 'USD',
                status VARCHAR(50) DEFAULT 'pending',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
            CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
            """,
                "Create payments table",
            ),
            # Tokens/Credits table
            (
                """
            CREATE TABLE IF NOT EXISTS user_tokens (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                balance INTEGER DEFAULT 0,
                total_purchased INTEGER DEFAULT 0,
                total_used INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_user_tokens_user_id ON user_tokens(user_id);
            """,
                "Create user_tokens table",
            ),
            # Backups table
            (
                """
            CREATE TABLE IF NOT EXISTS backups (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                backup_type VARCHAR(50),
                status VARCHAR(50) DEFAULT 'pending',
                s3_path VARCHAR(255),
                size_bytes BIGINT,
                checksum VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                verified_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_backups_status ON backups(status);
            CREATE INDEX IF NOT EXISTS idx_backups_created_at ON backups(created_at);
            """,
                "Create backups table",
            ),
            # Email logs table
            (
                """
            CREATE TABLE IF NOT EXISTS email_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                recipient_email VARCHAR(255),
                subject VARCHAR(255),
                template_name VARCHAR(255),
                status VARCHAR(50) DEFAULT 'pending',
                sent_at TIMESTAMP,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_email_logs_user_id ON email_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status);
            """,
                "Create email_logs table",
            ),
        ]

        all_success = True
        for sql, description in migrations:
            success = await self.execute_migration(sql, description)
            if not success:
                all_success = False

        return all_success

    async def seed_data(self) -> bool:
        """Seed initial data"""
        try:
            async with self.pool.acquire() as conn:
                # Create admin user if not exists
                await conn.execute(
                    """
                    INSERT INTO users (email, username, role, status)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (email) DO NOTHING
                """,
                    "admin@crucibai.app",
                    "admin",
                    "admin",
                    "active",
                )

            logger.info("✅ Initial data seeded")
            return True
        except Exception as e:
            logger.error(f"❌ Seeding failed: {e}")
            return False

    async def verify_connection(self) -> bool:
        """Verify database connection"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                if result == 1:
                    logger.info("✅ Database connection verified")
                    return True
        except Exception as e:
            logger.error(f"❌ Database connection verification failed: {e}")
        return False

    async def get_database_stats(self) -> dict:
        """Get database statistics"""
        try:
            async with self.pool.acquire() as conn:
                stats = {
                    "users": await conn.fetchval("SELECT COUNT(*) FROM users"),
                    "projects": await conn.fetchval("SELECT COUNT(*) FROM projects"),
                    "builds": await conn.fetchval("SELECT COUNT(*) FROM builds"),
                    "backups": await conn.fetchval("SELECT COUNT(*) FROM backups"),
                    "timestamp": datetime.now().isoformat(),
                }
                return stats
        except Exception as e:
            logger.error(f"❌ Failed to get database stats: {e}")
            return {}

    async def initialize(self) -> bool:
        """Run full initialization"""
        logger.info("🚀 Starting database initialization...")

        try:
            # Connect
            await self.connect()

            # Verify connection
            if not await self.verify_connection():
                return False

            # Create schema
            if not await self.create_schema():
                return False

            # Seed data
            if not await self.seed_data():
                return False

            # Get stats
            stats = await self.get_database_stats()
            logger.info(f"📊 Database stats: {stats}")

            logger.info("✅ Database initialization complete!")
            return True

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
        finally:
            await self.disconnect()


async def main():
    """Main entry point"""
    logging.basicConfig(level=logging.INFO)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable not set")
        return False

    initializer = DatabaseInitializer(database_url)
    success = await initializer.initialize()

    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
