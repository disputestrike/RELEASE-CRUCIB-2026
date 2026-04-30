"""
Database Operations Agent - execute SQL queries.
Supports PostgreSQL, MySQL, SQLite.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

import aiomysql
import aiosqlite
import asyncpg

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from ....agents.base_agent import BaseAgent

class DatabaseOperationsAgent(BaseAgent):
    """Database operations agent"""

    def __init__(self, llm_client, config, db=None):
        super().__init__(llm_client=llm_client, config=config, db=db)
        self.name = "DatabaseOperationsAgent"

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute SQL query.

        Expected context:
        {
            "db_type": "postgres|mysql|sqlite",
            "connection": {"host": "localhost", "database": "mydb", ...},
            "query": "SELECT * FROM users WHERE id = $1",
            "params": [123]
        }
        Security: When connection is user-provided (from context), only SELECT is allowed (read-only).
        """
        query = (context.get("query") or "").strip()
        if not query:
            return {"error": "query is required", "success": False}
        # Remote DB with client-provided connection: read-only. Local SQLite file may run DDL/DML for tooling/tests.
        db_type = context.get("db_type", "postgres")
        if context.get("connection") and db_type in ("postgres", "mysql"):
            q = query.upper().lstrip()
            if not (
                q.startswith("SELECT") or q.startswith("WITH") and "SELECT" in q[:200]
            ):
                return {
                    "error": "Only SELECT queries are allowed when using client-provided connection",
                    "success": False,
                }

        try:
            if db_type == "postgres":
                result = await self._execute_postgres(context)
            elif db_type == "mysql":
                result = await self._execute_mysql(context)
            elif db_type == "sqlite":
                result = await self._execute_sqlite(context)
            else:
                result = {"error": f"Unknown db_type: {db_type}"}

            return result

        except Exception as e:
            return {"error": str(e), "success": False}

    async def _execute_postgres(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute PostgreSQL query"""
        conn_params = context.get("connection", {})
        query = context.get("query")
        params = context.get("params", [])

        conn = await asyncpg.connect(**conn_params)

        try:
            if query.strip().upper().startswith("SELECT"):
                rows = await conn.fetch(query, *params)
                result = {
                    "rows": [dict(row) for row in rows],
                    "row_count": len(rows),
                    "success": True,
                }
            else:
                status = await conn.execute(query, *params)
                result = {"status": status, "success": True}
        finally:
            await conn.close()

        return result

    async def _execute_mysql(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MySQL query"""
        conn_params = context.get("connection", {})
        query = context.get("query")
        params = context.get("params", [])

        conn = await aiomysql.connect(**conn_params)
        cursor = await conn.cursor(aiomysql.DictCursor)

        try:
            await cursor.execute(query, params)

            if query.strip().upper().startswith("SELECT"):
                rows = await cursor.fetchall()
                result = {"rows": rows, "row_count": len(rows), "success": True}
            else:
                await conn.commit()
                result = {"affected_rows": cursor.rowcount, "success": True}
        finally:
            await cursor.close()
            conn.close()

        return result

    async def _execute_sqlite(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute SQLite query"""
        db_path = context.get("connection", {}).get("database", "database.db")
        query = context.get("query")
        params = context.get("params", [])

        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, params)

            if query.strip().upper().startswith("SELECT"):
                rows = await cursor.fetchall()
                result = {
                    "rows": [dict(row) for row in rows],
                    "row_count": len(rows),
                    "success": True,
                }
            else:
                await conn.commit()
                result = {"affected_rows": cursor.rowcount, "success": True}

        return result
