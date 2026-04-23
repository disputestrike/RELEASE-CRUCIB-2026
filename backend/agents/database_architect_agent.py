# backend/agents/database_architect_agent.py
"""
DatabaseArchitectAgent analyzes user requirements and generates database schemas.
Creates table definitions, relationships, and RLS policies automatically.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from anthropic_models import ANTHROPIC_SONNET_MODEL, normalize_anthropic_model
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Schema Models
class ColumnDef(BaseModel):
    """Column definition for database table."""

    name: str
    type: str  # text, integer, boolean, uuid, timestamp, json, jsonb, array
    required: bool = True
    unique: bool = False
    primary_key: bool = False
    foreign_key: Optional[str] = None  # e.g., "users(id)"
    default: Optional[str] = None
    description: Optional[str] = None


class IndexDef(BaseModel):
    """Index definition."""

    name: str
    columns: List[str]
    unique: bool = False


class RLSPolicy(BaseModel):
    """Row-level security policy."""

    name: str
    using: str  # SQL condition
    with_check: Optional[str] = None


class TableDef(BaseModel):
    """Table definition for database schema."""

    name: str
    description: Optional[str] = None
    columns: List[ColumnDef]
    indexes: List[IndexDef] = Field(default_factory=list)
    rls_policies: List[RLSPolicy] = Field(default_factory=list)


class SchemaResponse(BaseModel):
    """Complete database schema response."""

    tables: List[TableDef]
    enums: Optional[Dict[str, List[str]]] = None  # Enum types
    extensions: List[str] = Field(default_factory=list)  # PostgreSQL extensions


def heuristic_schema_from_requirements(requirements: str) -> SchemaResponse:
    """
    Deterministic schema sketch for live builds when we want schema planning
    without depending on a remote LLM call.
    """
    goal = (requirements or "").lower()

    def std_columns(*extra: ColumnDef) -> List[ColumnDef]:
        return [
            ColumnDef(name="id", type="uuid", primary_key=True),
            *list(extra),
            ColumnDef(name="created_at", type="timestamp", default="now()"),
            ColumnDef(name="updated_at", type="timestamp", default="now()"),
        ]

    tables: List[TableDef] = []
    tables.append(
        TableDef(
            name="app_records",
            description="Default application records generated from the build goal",
            columns=std_columns(
                ColumnDef(name="title", type="text", required=True),
                ColumnDef(
                    name="status", type="text", required=False, default="'draft'"
                ),
                ColumnDef(
                    name="metadata", type="jsonb", required=False, default="'{}'::jsonb"
                ),
            ),
        )
    )

    if any(word in goal for word in ("account", "crm", "customer", "lead", "contact")):
        tables.extend(
            [
                TableDef(
                    name="accounts",
                    description="Customer or tenant accounts",
                    columns=std_columns(
                        ColumnDef(name="name", type="text", required=True),
                        ColumnDef(name="industry", type="text", required=False),
                    ),
                ),
                TableDef(
                    name="contacts",
                    description="Contacts linked to accounts",
                    columns=std_columns(
                        ColumnDef(
                            name="account_id",
                            type="uuid",
                            required=True,
                            foreign_key="accounts(id)",
                        ),
                        ColumnDef(
                            name="email", type="text", required=True, unique=True
                        ),
                        ColumnDef(name="full_name", type="text", required=True),
                    ),
                ),
            ]
        )

    if any(
        word in goal
        for word in ("quote", "pricing", "invoice", "subscription", "billing")
    ):
        tables.extend(
            [
                TableDef(
                    name="quotes",
                    description="Pricing quotes and approval state",
                    columns=std_columns(
                        ColumnDef(
                            name="account_id",
                            type="uuid",
                            required=False,
                            foreign_key="accounts(id)",
                        ),
                        ColumnDef(
                            name="status", type="text", required=True, default="'draft'"
                        ),
                        ColumnDef(
                            name="total_amount_cents",
                            type="integer",
                            required=False,
                            default="0",
                        ),
                    ),
                ),
                TableDef(
                    name="quote_line_items",
                    description="Line items belonging to a quote",
                    columns=std_columns(
                        ColumnDef(
                            name="quote_id",
                            type="uuid",
                            required=True,
                            foreign_key="quotes(id)",
                        ),
                        ColumnDef(name="label", type="text", required=True),
                        ColumnDef(
                            name="quantity", type="integer", required=True, default="1"
                        ),
                        ColumnDef(
                            name="unit_price_cents",
                            type="integer",
                            required=True,
                            default="0",
                        ),
                    ),
                ),
            ]
        )

    if any(word in goal for word in ("task", "workflow", "project", "schedule")):
        tables.extend(
            [
                TableDef(
                    name="projects",
                    description="Projects or workflow containers",
                    columns=std_columns(
                        ColumnDef(name="name", type="text", required=True),
                        ColumnDef(
                            name="status",
                            type="text",
                            required=True,
                            default="'planned'",
                        ),
                    ),
                ),
                TableDef(
                    name="tasks",
                    description="Tasks linked to projects",
                    columns=std_columns(
                        ColumnDef(
                            name="project_id",
                            type="uuid",
                            required=True,
                            foreign_key="projects(id)",
                        ),
                        ColumnDef(name="title", type="text", required=True),
                        ColumnDef(
                            name="priority",
                            type="text",
                            required=False,
                            default="'normal'",
                        ),
                    ),
                ),
            ]
        )

    if any(word in goal for word in ("audit", "policy", "compliance", "security")):
        tables.extend(
            [
                TableDef(
                    name="audit_events",
                    description="Append-only audit events",
                    columns=std_columns(
                        ColumnDef(name="entity_type", type="text", required=True),
                        ColumnDef(name="entity_id", type="uuid", required=False),
                        ColumnDef(name="event_name", type="text", required=True),
                        ColumnDef(
                            name="payload",
                            type="jsonb",
                            required=False,
                            default="'{}'::jsonb",
                        ),
                    ),
                ),
                TableDef(
                    name="policies",
                    description="Policy rules or compliance controls",
                    columns=std_columns(
                        ColumnDef(name="name", type="text", required=True, unique=True),
                        ColumnDef(
                            name="status", type="text", required=True, default="'draft'"
                        ),
                    ),
                ),
            ]
        )

    seen = set()
    deduped_tables: List[TableDef] = []
    for table in tables:
        if table.name in seen:
            continue
        seen.add(table.name)
        deduped_tables.append(table)

    return SchemaResponse(tables=deduped_tables, extensions=["uuid-ossp"])


class DatabaseArchitectAgent:
    """
    Analyzes requirements and generates database schemas.
    Integrates with LLM for intelligent schema generation.
    """

    def __init__(self, llm_client):
        self.llm = llm_client
        self.model = normalize_anthropic_model(ANTHROPIC_SONNET_MODEL)

    async def execute(self, context: Dict) -> Dict:
        """
        Generate database schema from user requirements.
        """
        try:
            user_requirements = context.get("user_requirements", "")
            existing_schema = context.get("existing_schema", "")
            project_id = context.get("project_id", "unknown")

            if not user_requirements:
                return {"status": "error", "reason": "No user requirements provided"}

            # Generate schema via LLM
            schema = await self._generate_schema(user_requirements, existing_schema)

            # Validate schema
            errors = self._validate_schema(schema)
            if errors:
                return {
                    "status": "error",
                    "reason": f"Schema validation failed: {errors}",
                }

            # Store schema in context for downstream use
            context["database_schema"] = schema

            return {
                "status": "success",
                "schema": schema.dict(),
                "table_count": len(schema.tables),
                "column_count": sum(len(t.columns) for t in schema.tables),
                "summary": self._summarize_schema(schema),
            }

        except Exception as e:
            logger.error(f"Error in DatabaseArchitectAgent: {e}")
            return {"status": "error", "reason": str(e)}

    async def _generate_schema(
        self, requirements: str, existing_schema: str
    ) -> SchemaResponse:
        """Generate schema using Claude."""

        prompt = f"""You are a database architect for web applications.

USER REQUIREMENTS:
{requirements}

EXISTING SCHEMA (if any):
{existing_schema or '(none)'}

Based on the user requirements, generate a complete database schema.

IMPORTANT RULES:
1. Every table needs an id (uuid) primary key
2. Every table should have created_at (timestamp default now())
3. Every table should have updated_at (timestamp default now())
4. Use appropriate column types: text, integer, boolean, uuid, timestamp, json, jsonb
5. Add indexes on frequently-queried fields
6. Include RLS policies for data isolation
7. Use snake_case for table and column names
8. Include foreign key relationships
9. Add NOT NULL constraints where appropriate
10. Include description for each table

Return ONLY valid JSON matching this exact format:
{{
  "tables": [
    {{
      "name": "table_name",
      "description": "What this table stores",
      "columns": [
        {{"name": "id", "type": "uuid", "primary_key": true}},
        {{"name": "user_id", "type": "uuid", "required": true, "foreign_key": "users(id)"}},
        {{"name": "email", "type": "text", "required": true, "unique": true}},
        {{"name": "created_at", "type": "timestamp", "default": "now()"}}
      ],
      "indexes": [
        {{"name": "idx_user_email", "columns": ["user_id", "email"]}}
      ],
      "rls_policies": [
        {{"name": "users_own_data", "using": "(auth.uid() = user_id)"}}
      ]
    }}
  ],
  "extensions": ["uuid-ossp"]
}}

Respond with ONLY the JSON, no markdown, no preamble.
"""

        try:
            response = await self.llm.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text.strip()

            # Parse JSON response
            schema_dict = json.loads(response_text)
            schema = SchemaResponse(**schema_dict)

            return schema

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from LLM: {e}")
            # Return default schema
            return self._create_default_schema()

        except Exception as e:
            logger.error(f"Error generating schema: {e}")
            raise

    def _validate_schema(self, schema: SchemaResponse) -> Optional[str]:
        """Validate schema structure."""
        # Check for duplicate table names
        table_names = [t.name for t in schema.tables]
        if len(table_names) != len(set(table_names)):
            return "Duplicate table names found"

        # Check each table
        for table in schema.tables:
            # Check for duplicate column names
            col_names = [c.name for c in table.columns]
            if len(col_names) != len(set(col_names)):
                return f"Duplicate columns in table {table.name}"

            # Check for primary key
            has_pk = any(c.primary_key for c in table.columns)
            if not has_pk:
                return f"Table {table.name} has no primary key"

        return None

    def _summarize_schema(self, schema: SchemaResponse) -> str:
        """Create human-readable summary of schema."""
        table_list = ", ".join([t.name for t in schema.tables])
        total_cols = sum(len(t.columns) for t in schema.tables)
        return f"Generated {len(schema.tables)} tables ({total_cols} columns): {table_list}"

    def _create_default_schema(self) -> SchemaResponse:
        """Create a simple default schema."""
        return SchemaResponse(
            tables=[
                TableDef(
                    name="public_schema",
                    columns=[
                        ColumnDef(name="id", type="uuid", primary_key=True),
                        ColumnDef(name="created_at", type="timestamp", default="now()"),
                    ],
                )
            ]
        )


# Schema to SQL converter
class SchemaToSQL:
    """Convert SchemaResponse to SQL DDL statements."""

    @staticmethod
    def generate_sql(schema: SchemaResponse) -> List[str]:
        """Generate SQL statements from schema."""
        statements = []

        # Create extensions
        for ext in schema.extensions or []:
            statements.append(f"CREATE EXTENSION IF NOT EXISTS {ext};")

        # Create tables
        for table in schema.tables:
            sql = SchemaToSQL._generate_table_sql(table)
            statements.append(sql)

        return statements

    @staticmethod
    def _generate_table_sql(table: TableDef) -> str:
        """Generate CREATE TABLE statement."""
        lines = [f"CREATE TABLE {table.name} ("]

        # Add columns
        for col in table.columns:
            col_sql = SchemaToSQL._column_to_sql(col)
            lines.append(f"  {col_sql},")

        # Remove trailing comma from last line
        lines[-1] = lines[-1].rstrip(",")
        lines.append(");")

        sql = "\n".join(lines)

        # Add indexes
        for idx in table.indexes:
            unique = "UNIQUE" if idx.unique else ""
            cols = ", ".join(idx.columns)
            sql += f"\nCREATE {unique} INDEX {idx.name} ON {table.name}({cols});"

        # Add RLS policies
        sql += f"\nALTER TABLE {table.name} ENABLE ROW LEVEL SECURITY;"
        for policy in table.rls_policies:
            sql += (
                f"\nCREATE POLICY {policy.name} ON {table.name} USING ({policy.using})"
            )
            if policy.with_check:
                sql += f" WITH CHECK ({policy.with_check})"
            sql += ";"

        return sql

    @staticmethod
    def _column_to_sql(col: ColumnDef) -> str:
        """Convert ColumnDef to SQL."""
        parts = [col.name]

        # Type mapping
        type_map = {
            "text": "TEXT",
            "integer": "INTEGER",
            "boolean": "BOOLEAN",
            "uuid": "UUID",
            "timestamp": "TIMESTAMP",
            "json": "JSON",
            "jsonb": "JSONB",
            "array": "ARRAY",
        }

        parts.append(type_map.get(col.type, col.type))

        if col.primary_key:
            parts.append("PRIMARY KEY")
        elif not col.required:
            parts.append("NULL")
        else:
            parts.append("NOT NULL")

        if col.unique:
            parts.append("UNIQUE")

        if col.default:
            parts.append(f"DEFAULT {col.default}")

        if col.foreign_key:
            parts.append(f"REFERENCES {col.foreign_key}")

        return " ".join(parts)
