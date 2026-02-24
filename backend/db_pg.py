"""
PostgreSQL connection layer for CrucibAI - Motor-compatible wrapper.
Provides Motor-like API (db.users.find_one(), db.projects.find(), etc.)
backed by PostgreSQL with JSONB document storage.
"""
import os
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)
_pool = None
_db = None


async def get_pg_pool():
    """Return asyncpg pool, creating if needed."""
    global _pool
    if _pool is not None:
        return _pool
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL not set")
    try:
        import asyncpg
        _pool = await asyncpg.create_pool(url, min_size=2, max_size=10, command_timeout=60)
        logger.info("✅ PostgreSQL pool created")
        return _pool
    except Exception as e:
        logger.error(f"❌ PostgreSQL pool failed: {e}")
        raise


async def close_pg_pool():
    """Close the global asyncpg pool."""
    global _pool, _db
    if _pool is not None:
        await _pool.close()
        _pool = None
        _db = None
        logger.info("✅ PostgreSQL pool closed")


def is_pg_available() -> bool:
    """Return True if DATABASE_URL is set."""
    return bool(os.environ.get("DATABASE_URL", "").strip())


class PGCollection:
    """Motor-like collection wrapper for a PostgreSQL table."""
    
    def __init__(self, pool, table_name: str):
        self.pool = pool
        self.table_name = table_name
        self._sort_spec = None
        self._skip_count = 0
        self._limit_count = None
    
    async def _ensure_table(self):
        """Ensure table exists with doc JSONB column."""
        async with self.pool.acquire() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id SERIAL PRIMARY KEY,
                    _id TEXT UNIQUE,
                    doc JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_id ON {self.table_name}(_id);
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_doc ON {self.table_name} USING GIN(doc);
            """)
    
    async def find_one(self, query: Dict[str, Any] = None, projection: Dict = None) -> Optional[Dict]:
        """Find one document matching query."""
        await self._ensure_table()
        query = query or {}
        
        async with self.pool.acquire() as conn:
            where_clause, params = self._build_where(query)
            sql = f"SELECT doc FROM {self.table_name} WHERE {where_clause} LIMIT 1"
            row = await conn.fetchrow(sql, *params)
            
            if row:
                doc = row['doc']
                if projection:
                    doc = self._apply_projection(doc, projection)
                return doc
            return None
    
    async def find(self, query: Dict[str, Any] = None, projection: Dict = None):
        """Return self for chaining (sort, skip, limit, to_list)."""
        await self._ensure_table()
        self._query = query or {}
        self._projection = projection
        return self
    
    def sort(self, key_or_list, direction=1):
        """Set sort order."""
        if isinstance(key_or_list, list):
            self._sort_spec = key_or_list
        else:
            self._sort_spec = [(key_or_list, direction)]
        return self
    
    def skip(self, count: int):
        """Set skip count."""
        self._skip_count = count
        return self
    
    def limit(self, count: int):
        """Set limit count."""
        self._limit_count = count
        return self
    
    async def to_list(self, length: int = None) -> List[Dict]:
        """Execute query and return list of documents."""
        if not hasattr(self, '_query'):
            return []
        
        async with self.pool.acquire() as conn:
            where_clause, params = self._build_where(self._query)
            sql = f"SELECT doc FROM {self.table_name} WHERE {where_clause}"
            
            # Add sorting
            if self._sort_spec:
                order_parts = []
                for key, direction in self._sort_spec:
                    dir_str = "DESC" if direction == -1 else "ASC"
                    order_parts.append(f"doc->'{key}' {dir_str}")
                sql += " ORDER BY " + ", ".join(order_parts)
            
            # Add skip and limit
            if self._skip_count:
                sql += f" OFFSET {self._skip_count}"
            if self._limit_count:
                sql += f" LIMIT {self._limit_count}"
            elif length:
                sql += f" LIMIT {length}"
            
            rows = await conn.fetch(sql, *params)
            docs = [row['doc'] for row in rows]
            
            if self._projection:
                docs = [self._apply_projection(doc, self._projection) for doc in docs]
            
            return docs
    
    async def insert_one(self, document: Dict[str, Any]) -> Dict:
        """Insert a document."""
        await self._ensure_table()
        _id = document.get('_id', self._generate_id())
        doc_json = json.dumps(document)
        
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    f"INSERT INTO {self.table_name} (_id, doc) VALUES ($1, $2::jsonb)",
                    _id, doc_json
                )
            except Exception as e:
                if "duplicate" in str(e).lower():
                    raise ValueError(f"Duplicate _id: {_id}")
                raise
        
        return {"_id": _id, "inserted_id": _id}
    
    async def insert_many(self, documents: List[Dict[str, Any]]) -> Dict:
        """Insert multiple documents."""
        await self._ensure_table()
        ids = []
        
        async with self.pool.acquire() as conn:
            for doc in documents:
                _id = doc.get('_id', self._generate_id())
                doc_json = json.dumps(doc)
                try:
                    await conn.execute(
                        f"INSERT INTO {self.table_name} (_id, doc) VALUES ($1, $2::jsonb)",
                        _id, doc_json
                    )
                    ids.append(_id)
                except Exception as e:
                    if "duplicate" not in str(e).lower():
                        raise
        
        return {"inserted_ids": ids}
    
    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]) -> Dict:
        """Update one document."""
        await self._ensure_table()
        
        # Get the document first
        doc = await self.find_one(query)
        if not doc:
            return {"matched_count": 0, "modified_count": 0}
        
        # Apply update operators
        updated_doc = self._apply_update_operators(doc, update)
        updated_doc['updated_at'] = datetime.utcnow().isoformat()
        
        doc_json = json.dumps(updated_doc)
        _id = doc.get('_id')
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE {self.table_name} SET doc = $1::jsonb, updated_at = NOW() WHERE _id = $2",
                doc_json, _id
            )
        
        return {"matched_count": 1, "modified_count": 1}
    
    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]) -> Dict:
        """Update multiple documents."""
        await self._ensure_table()
        
        docs = await self.find(query).to_list()
        if not docs:
            return {"matched_count": 0, "modified_count": 0}
        
        modified = 0
        async with self.pool.acquire() as conn:
            for doc in docs:
                updated_doc = self._apply_update_operators(doc, update)
                updated_doc['updated_at'] = datetime.utcnow().isoformat()
                doc_json = json.dumps(updated_doc)
                _id = doc.get('_id')
                
                await conn.execute(
                    f"UPDATE {self.table_name} SET doc = $1::jsonb, updated_at = NOW() WHERE _id = $2",
                    doc_json, _id
                )
                modified += 1
        
        return {"matched_count": len(docs), "modified_count": modified}
    
    async def delete_one(self, query: Dict[str, Any]) -> Dict:
        """Delete one document."""
        await self._ensure_table()
        
        doc = await self.find_one(query)
        if not doc:
            return {"deleted_count": 0}
        
        _id = doc.get('_id')
        async with self.pool.acquire() as conn:
            await conn.execute(f"DELETE FROM {self.table_name} WHERE _id = $1", _id)
        
        return {"deleted_count": 1}
    
    async def delete_many(self, query: Dict[str, Any]) -> Dict:
        """Delete multiple documents."""
        await self._ensure_table()
        
        docs = await self.find(query).to_list()
        if not docs:
            return {"deleted_count": 0}
        
        async with self.pool.acquire() as conn:
            for doc in docs:
                _id = doc.get('_id')
                await conn.execute(f"DELETE FROM {self.table_name} WHERE _id = $1", _id)
        
        return {"deleted_count": len(docs)}
    
    async def count_documents(self, query: Dict[str, Any] = None) -> int:
        """Count documents matching query."""
        await self._ensure_table()
        query = query or {}
        
        async with self.pool.acquire() as conn:
            where_clause, params = self._build_where(query)
            sql = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE {where_clause}"
            row = await conn.fetchrow(sql, *params)
            return row['count'] if row else 0
    
    async def replace_one(self, query: Dict[str, Any], replacement: Dict[str, Any]) -> Dict:
        """Replace one document."""
        await self._ensure_table()
        
        doc = await self.find_one(query)
        if not doc:
            return {"matched_count": 0, "modified_count": 0}
        
        _id = doc.get('_id')
        replacement['_id'] = _id
        replacement['updated_at'] = datetime.utcnow().isoformat()
        doc_json = json.dumps(replacement)
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                f"UPDATE {self.table_name} SET doc = $1::jsonb, updated_at = NOW() WHERE _id = $2",
                doc_json, _id
            )
        
        return {"matched_count": 1, "modified_count": 1}
    
    def _build_where(self, query: Dict[str, Any]) -> tuple:
        """Build WHERE clause from query dict."""
        if not query:
            return "TRUE", []
        
        conditions = []
        params = []
        param_idx = 1
        
        for key, value in query.items():
            if isinstance(value, dict):
                # Handle operators like $eq, $gte, $in, etc.
                for op, op_value in value.items():
                    if op == "$eq":
                        conditions.append(f"doc->'{key}' = ${param_idx}::jsonb")
                        params.append(json.dumps(op_value))
                        param_idx += 1
                    elif op == "$gte":
                        conditions.append(f"(doc->>'{key}')::numeric >= ${param_idx}::numeric")
                        params.append(op_value)
                        param_idx += 1
                    elif op == "$lte":
                        conditions.append(f"(doc->>'{key}')::numeric <= ${param_idx}::numeric")
                        params.append(op_value)
                        param_idx += 1
                    elif op == "$gt":
                        conditions.append(f"(doc->>'{key}')::numeric > ${param_idx}::numeric")
                        params.append(op_value)
                        param_idx += 1
                    elif op == "$lt":
                        conditions.append(f"(doc->>'{key}')::numeric < ${param_idx}::numeric")
                        params.append(op_value)
                        param_idx += 1
                    elif op == "$in":
                        placeholders = ", ".join([f"${param_idx + i}::jsonb" for i in range(len(op_value))])
                        conditions.append(f"doc->'{key}' IN ({placeholders})")
                        params.extend([json.dumps(v) for v in op_value])
                        param_idx += len(op_value)
                    elif op == "$nin":
                        placeholders = ", ".join([f"${param_idx + i}::jsonb" for i in range(len(op_value))])
                        conditions.append(f"doc->'{key}' NOT IN ({placeholders})")
                        params.extend([json.dumps(v) for v in op_value])
                        param_idx += len(op_value)
            else:
                # Simple equality
                conditions.append(f"doc->'{key}' = ${param_idx}::jsonb")
                params.append(json.dumps(value))
                param_idx += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        return where_clause, params
    
    def _apply_update_operators(self, doc: Dict, update: Dict) -> Dict:
        """Apply MongoDB-style update operators ($set, $inc, etc.)."""
        result = doc.copy()
        
        for op, changes in update.items():
            if op == "$set":
                result.update(changes)
            elif op == "$inc":
                for key, value in changes.items():
                    result[key] = result.get(key, 0) + value
            elif op == "$unset":
                for key in changes.keys():
                    result.pop(key, None)
            elif op == "$push":
                for key, value in changes.items():
                    if key not in result:
                        result[key] = []
                    if isinstance(result[key], list):
                        result[key].append(value)
            elif op == "$pull":
                for key, value in changes.items():
                    if key in result and isinstance(result[key], list):
                        result[key] = [v for v in result[key] if v != value]
        
        return result
    
    def _apply_projection(self, doc: Dict, projection: Dict) -> Dict:
        """Apply projection to document."""
        if not projection:
            return doc
        
        # If projection has 1s, include only those fields
        include_fields = [k for k, v in projection.items() if v == 1]
        if include_fields:
            return {k: doc.get(k) for k in include_fields if k in doc}
        
        # If projection has 0s, exclude those fields
        exclude_fields = [k for k, v in projection.items() if v == 0]
        return {k: v for k, v in doc.items() if k not in exclude_fields}
    
    def _generate_id(self) -> str:
        """Generate a unique _id."""
        import uuid
        return str(uuid.uuid4())


class PGDatabase:
    """Motor-like database wrapper for PostgreSQL."""
    
    def __init__(self, pool):
        self.pool = pool
        self._collections = {}
    
    def __getattr__(self, name: str) -> PGCollection:
        """Get or create a collection."""
        if name not in self._collections:
            self._collections[name] = PGCollection(self.pool, name)
        return self._collections[name]


async def get_db() -> PGDatabase:
    """Get Motor-like database instance."""
    global _db
    if _db is None:
        pool = await get_pg_pool()
        _db = PGDatabase(pool)
    return _db
