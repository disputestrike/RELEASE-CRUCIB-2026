"""
CrucibAI Backup System
Daily database backups to S3 with verification and recovery
"""

import os
import logging
import asyncio
import hashlib
import gzip
import io
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import asyncpg
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BackupSystem:
    """Handles database backups to S3"""

    def __init__(self):
        self.s3_client = None
        self.db_pool = None
        self.bucket_name = os.getenv("AWS_S3_BUCKET", "crucibai-backups")
        self.backup_prefix = os.getenv("AWS_S3_BACKUP_PREFIX", "daily-backups/")
        self.retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        self.configured = False

        self._initialize_s3()

    def _initialize_s3(self):
        """Initialize S3 client"""
        try:
            self.s3_client = boto3.client(
                "s3",
                region_name=os.getenv("AWS_REGION", "us-east-1"),
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            )

            # Test connection
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.configured = True
            logger.info("✅ S3 backup system initialized")

        except ClientError as e:
            logger.error(f"❌ Failed to initialize S3: {e}")
            self.configured = False
        except Exception as e:
            logger.error(f"❌ S3 initialization error: {e}")
            self.configured = False

    async def set_db_pool(self, pool: asyncpg.Pool):
        """Set database connection pool"""
        self.db_pool = pool

    async def create_backup(
        self, backup_type: str = "full"
    ) -> Optional[Dict[str, Any]]:
        """Create database backup"""

        if not self.configured or not self.db_pool:
            logger.error("❌ Backup system not configured")
            return None

        try:
            timestamp = datetime.now().isoformat()
            backup_filename = f"{self.backup_prefix}{backup_type}-{timestamp}.sql.gz"

            logger.info(f"🔄 Starting backup: {backup_filename}")

            # Export database
            sql_data = await self._export_database()

            if not sql_data:
                logger.error("❌ Database export failed")
                return None

            # Compress
            compressed_data = self._compress_data(sql_data)

            # Calculate checksum
            checksum = hashlib.sha256(compressed_data).hexdigest()

            # Upload to S3
            success = await self._upload_to_s3(backup_filename, compressed_data)

            if not success:
                logger.error("❌ S3 upload failed")
                return None

            # Verify upload
            verified = await self._verify_backup(backup_filename, checksum)

            if not verified:
                logger.error("❌ Backup verification failed")
                return None

            backup_info = {
                "filename": backup_filename,
                "size_bytes": len(compressed_data),
                "checksum": checksum,
                "timestamp": timestamp,
                "type": backup_type,
                "status": "verified",
            }

            logger.info(f"✅ Backup completed: {backup_filename}")
            return backup_info

        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return None

    async def _export_database(self) -> Optional[str]:
        """Export database to SQL"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get all tables
                tables = await conn.fetch("""
                    SELECT tablename FROM pg_tables
                    WHERE schemaname = 'public'
                """)

                sql_lines = []
                sql_lines.append("-- CrucibAI Database Backup")
                sql_lines.append(f"-- Generated: {datetime.now().isoformat()}")
                sql_lines.append("")

                # Export each table
                for table in tables:
                    table_name = table["tablename"]

                    # Get table structure
                    structure = await conn.fetchval(f"""
                        SELECT pg_get_ddl('pg_class'::regclass, '{table_name}'::regclass)
                    """)

                    if structure:
                        sql_lines.append(f"-- Table: {table_name}")
                        sql_lines.append(structure)
                        sql_lines.append("")

                    # Get table data
                    rows = await conn.fetch(f"SELECT * FROM {table_name}")

                    for row in rows:
                        columns = list(row.keys())
                        values = [self._format_value(row[col]) for col in columns]
                        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});"
                        sql_lines.append(insert_sql)

                return "\n".join(sql_lines)

        except Exception as e:
            logger.error(f"❌ Database export failed: {e}")
            return None

    def _format_value(self, value) -> str:
        """Format value for SQL"""
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            return f"'{value.replace(chr(39), chr(39)*2)}'"
        elif isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return f"'{str(value)}'"

    def _compress_data(self, data: str) -> bytes:
        """Compress data with gzip"""
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb") as gz:
            gz.write(data.encode("utf-8"))
        return buffer.getvalue()

    async def _upload_to_s3(self, filename: str, data: bytes) -> bool:
        """Upload backup to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=data,
                ContentType="application/gzip",
                Metadata={
                    "backup-date": datetime.now().isoformat(),
                    "checksum": hashlib.sha256(data).hexdigest(),
                },
            )
            logger.info(f"✅ Uploaded to S3: {filename}")
            return True
        except ClientError as e:
            logger.error(f"❌ S3 upload failed: {e}")
            return False

    async def _verify_backup(self, filename: str, expected_checksum: str) -> bool:
        """Verify backup integrity"""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=filename)

            data = response["Body"].read()
            actual_checksum = hashlib.sha256(data).hexdigest()

            if actual_checksum == expected_checksum:
                logger.info(f"✅ Backup verified: {filename}")
                return True
            else:
                logger.error(f"❌ Checksum mismatch: {filename}")
                return False

        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False

    async def list_backups(self) -> List[Dict[str, Any]]:
        """List all backups"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name, Prefix=self.backup_prefix
            )

            backups = []
            for obj in response.get("Contents", []):
                backups.append(
                    {
                        "filename": obj["Key"],
                        "size_bytes": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                    }
                )

            return sorted(backups, key=lambda x: x["last_modified"], reverse=True)

        except Exception as e:
            logger.error(f"❌ Failed to list backups: {e}")
            return []

    async def cleanup_old_backups(self):
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            backups = await self.list_backups()

            deleted_count = 0
            for backup in backups:
                last_modified = datetime.fromisoformat(
                    backup["last_modified"].replace("Z", "+00:00")
                )

                if last_modified < cutoff_date:
                    self.s3_client.delete_object(
                        Bucket=self.bucket_name, Key=backup["filename"]
                    )
                    deleted_count += 1
                    logger.info(f"🗑️ Deleted old backup: {backup['filename']}")

            logger.info(f"✅ Cleanup complete: {deleted_count} backups deleted")

        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")

    async def restore_backup(self, backup_filename: str) -> bool:
        """Restore database from backup"""
        try:
            logger.info(f"🔄 Restoring backup: {backup_filename}")

            # Download from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name, Key=backup_filename
            )

            compressed_data = response["Body"].read()

            # Decompress
            with gzip.GzipFile(fileobj=io.BytesIO(compressed_data)) as gz:
                sql_data = gz.read().decode("utf-8")

            # Execute SQL
            async with self.db_pool.acquire() as conn:
                await conn.execute(sql_data)

            logger.info(f"✅ Restore complete: {backup_filename}")
            return True

        except Exception as e:
            logger.error(f"❌ Restore failed: {e}")
            return False


# Global instance
backup_system = BackupSystem()


def get_backup_system() -> BackupSystem:
    """Get backup system instance"""
    return backup_system
