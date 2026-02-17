"""
DatabaseAgent: Designs database schema, migrations, and ORM models.
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry


@AgentRegistry.register
class DatabaseAgent(BaseAgent):
    """
    Designs database schema, migrations, and ORM models.
    
    Input:
        - user_prompt: str
        - stack_output: dict (optional, from StackSelectorAgent)
    
    Output:
        - schema: dict with tables, relationships
        - migrations: dict with migration files
        - orm_models: dict with ORM model code
    """
    
    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)
        
        if "user_prompt" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'user_prompt'")
        
        return True
    
    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        
        # Check required fields
        required = ["schema", "migrations", "orm_models"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing required field '{field}'")
        
        # Validate schema has tables
        if "tables" not in result["schema"]:
            raise AgentValidationError(f"{self.name}: schema must have 'tables' field")
        
        if not isinstance(result["schema"]["tables"], list):
            raise AgentValidationError(f"{self.name}: schema tables must be a list")
        
        # Validate at least one table
        if len(result["schema"]["tables"]) == 0:
            raise AgentValidationError(f"{self.name}: Must define at least one table")
        
        # Validate migrations is a dict
        if not isinstance(result["migrations"], dict):
            raise AgentValidationError(f"{self.name}: migrations must be a dictionary")
        
        # Validate orm_models is a dict
        if not isinstance(result["orm_models"], dict):
            raise AgentValidationError(f"{self.name}: orm_models must be a dictionary")
        
        return True
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_prompt = context.get("user_prompt", "")
        stack_output = context.get("stack_output", {})
        
        # Include stack context if available
        database_type = "PostgreSQL"
        orm_type = "SQLAlchemy"
        if stack_output:
            database = stack_output.get("database", {})
            database_type = database.get("primary", "PostgreSQL")
            backend = stack_output.get("backend", {})
            backend_lang = backend.get("language", "Python")
            
            # Determine ORM based on language
            if backend_lang == "Python":
                orm_type = "SQLAlchemy"
            elif backend_lang in ["Node.js", "TypeScript"]:
                orm_type = "Prisma"
            elif backend_lang == "Go":
                orm_type = "GORM"
        
        context_info = f"\n\nTechnology Context:\nDatabase: {database_type}\nORM: {orm_type}"
        
        system_prompt = f"""You are an expert Database Design agent. Your job is to design a comprehensive, normalized database schema with migrations and ORM models.

Project Requirements:
{user_prompt}{context_info}

Your task:
1. Design normalized database schema (3NF minimum)
2. Define tables with appropriate columns, types, and constraints
3. Create indexes for performance
4. Define relationships (one-to-many, many-to-many)
5. Write SQL migration files
6. Generate ORM model code

Output ONLY valid JSON in this exact format:
{{
  "schema": {{
    "tables": [
      {{
        "name": "users",
        "columns": [
          {{"name": "id", "type": "SERIAL PRIMARY KEY", "description": "Unique user identifier"}},
          {{"name": "email", "type": "VARCHAR(255) UNIQUE NOT NULL", "description": "User email"}},
          {{"name": "password_hash", "type": "VARCHAR(255) NOT NULL", "description": "Hashed password"}},
          {{"name": "created_at", "type": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "description": "Creation timestamp"}},
          {{"name": "updated_at", "type": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "description": "Last update timestamp"}}
        ],
        "indexes": [
          "CREATE INDEX idx_users_email ON users(email);",
          "CREATE INDEX idx_users_created_at ON users(created_at);"
        ]
      }}
    ],
    "relationships": [
      {{
        "from": "posts.user_id",
        "to": "users.id",
        "type": "many-to-one",
        "description": "Each post belongs to one user"
      }}
    ]
  }},
  "migrations": {{
    "001_initial_schema": "CREATE TABLE users (\\n  id SERIAL PRIMARY KEY,\\n  email VARCHAR(255) UNIQUE NOT NULL,\\n  password_hash VARCHAR(255) NOT NULL,\\n  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\\n  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\\n);\\n\\nCREATE INDEX idx_users_email ON users(email);",
    "002_add_posts": "CREATE TABLE posts (\\n  id SERIAL PRIMARY KEY,\\n  user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,\\n  title VARCHAR(255) NOT NULL,\\n  content TEXT,\\n  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\\n);"
  }},
  "orm_models": {{
    "prisma_schema": "model User {{\\n  id        Int      @id @default(autoincrement())\\n  email     String   @unique\\n  passwordHash String\\n  createdAt DateTime @default(now())\\n  updatedAt DateTime @updatedAt\\n  posts     Post[]\\n}}\\n\\nmodel Post {{\\n  id        Int      @id @default(autoincrement())\\n  userId    Int\\n  user      User     @relation(fields: [userId], references: [id], onDelete: Cascade)\\n  title     String\\n  content   String?\\n  createdAt DateTime @default(now())\\n}}",
    "sqlalchemy_models": "from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey\\nfrom sqlalchemy.ext.declarative import declarative_base\\nfrom sqlalchemy.orm import relationship\\nfrom datetime import datetime\\n\\nBase = declarative_base()\\n\\nclass User(Base):\\n    __tablename__ = 'users'\\n    id = Column(Integer, primary_key=True)\\n    email = Column(String(255), unique=True, nullable=False)\\n    password_hash = Column(String(255), nullable=False)\\n    created_at = Column(DateTime, default=datetime.utcnow)\\n    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)\\n    posts = relationship('Post', back_populates='user', cascade='all, delete-orphan')\\n\\nclass Post(Base):\\n    __tablename__ = 'posts'\\n    id = Column(Integer, primary_key=True)\\n    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)\\n    title = Column(String(255), nullable=False)\\n    content = Column(Text)\\n    created_at = Column(DateTime, default=datetime.utcnow)\\n    user = relationship('User', back_populates='posts')"
  }}
}}

Quality expectations:
- Use appropriate data types for each field
- Add NOT NULL constraints where appropriate
- Create proper indexes for foreign keys and frequently queried fields
- Follow naming conventions (snake_case for PostgreSQL/MySQL, camelCase for MongoDB)
- Include timestamps (created_at, updated_at) on all tables
- Design for scalability and query performance"""

        # Call LLM
        response, tokens = await self.call_llm(
            user_prompt=user_prompt + context_info,
            system_prompt=system_prompt,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=2000
        )
        
        # Parse JSON response
        data = self.parse_json_response(response)
        
        # Add metadata
        data["_tokens_used"] = tokens
        data["_model_used"] = "gpt-4o"
        data["_agent"] = self.name
        
        return data
