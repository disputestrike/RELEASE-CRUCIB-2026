# Phase 3: Tool Integrations Documentation

## Overview

This document describes the 5 real tool agents implemented in Phase 3 of the CrucibAI project. These agents provide powerful automation capabilities matching Manus' 29 tools capability.

## Tool Agents

### 1. BrowserAgent

**Location:** `backend/tools/browser_agent.py`

**Purpose:** Real browser automation using Playwright.

**Capabilities:**
- Navigate to URLs
- Take screenshots
- Scrape content
- Fill forms
- Click elements
- Extract data

**API Endpoint:** `POST /api/tools/browser`

**Example Request:**
```json
{
  "action": "navigate",
  "url": "https://example.com"
}
```

**Supported Actions:**

#### Navigate
```json
{
  "action": "navigate",
  "url": "https://example.com"
}
```
Response:
```json
{
  "url": "https://example.com",
  "title": "Example Domain",
  "content_length": 1256,
  "success": true
}
```

#### Screenshot
```json
{
  "action": "screenshot",
  "url": "https://example.com",
  "screenshot_path": "screenshot.png"
}
```
Response:
```json
{
  "url": "https://example.com",
  "screenshot_path": "screenshot.png",
  "screenshot_base64": "iVBORw0KGg...",
  "success": true
}
```

#### Scrape
```json
{
  "action": "scrape",
  "url": "https://example.com",
  "selector": "h1"
}
```
Response:
```json
{
  "url": "https://example.com",
  "selector": "h1",
  "text": "Example Domain",
  "html": "<h1>Example Domain</h1>",
  "success": true
}
```

#### Fill Form
```json
{
  "action": "fill_form",
  "url": "https://example.com/form",
  "form_data": {
    "#username": "john_doe",
    "#password": "secret123"
  },
  "submit_selector": "button[type='submit']"
}
```
Response:
```json
{
  "url": "https://example.com/form",
  "form_filled": ["#username", "#password"],
  "current_url": "https://example.com/success",
  "success": true
}
```

#### Click
```json
{
  "action": "click",
  "url": "https://example.com",
  "selector": "button.submit"
}
```
Response:
```json
{
  "url": "https://example.com",
  "clicked": "button.submit",
  "current_url": "https://example.com/result",
  "success": true
}
```

---

### 2. FileAgent

**Location:** `backend/tools/file_agent.py`

**Purpose:** Real file system operations.

**Capabilities:**
- Read files
- Write files
- Move/rename files
- Delete files
- List directory contents
- Create directories

**API Endpoint:** `POST /api/tools/file`

**Configuration:**
- `workspace`: Base directory for file operations (default: `./workspace`)

**Supported Actions:**

#### Read
```json
{
  "action": "read",
  "path": "data/config.json"
}
```
Response:
```json
{
  "path": "/workspace/data/config.json",
  "content": "{\"setting\": \"value\"}",
  "size": 20,
  "success": true
}
```

#### Write
```json
{
  "action": "write",
  "path": "output/result.txt",
  "content": "Hello, World!"
}
```
Response:
```json
{
  "path": "/workspace/output/result.txt",
  "size": 13,
  "success": true
}
```

#### Move
```json
{
  "action": "move",
  "path": "old/file.txt",
  "destination": "new/file.txt"
}
```
Response:
```json
{
  "source": "/workspace/old/file.txt",
  "destination": "/workspace/new/file.txt",
  "success": true
}
```

#### Delete
```json
{
  "action": "delete",
  "path": "temp/unwanted.txt"
}
```
Response:
```json
{
  "path": "/workspace/temp/unwanted.txt",
  "success": true
}
```

#### List
```json
{
  "action": "list",
  "path": "data"
}
```
Response:
```json
{
  "path": "/workspace/data",
  "files": [
    {"name": "config.json", "type": "file", "size": 128},
    {"name": "logs", "type": "directory", "size": 0}
  ],
  "count": 2,
  "success": true
}
```

#### Mkdir
```json
{
  "action": "mkdir",
  "path": "new/nested/directory"
}
```
Response:
```json
{
  "path": "/workspace/new/nested/directory",
  "success": true
}
```

---

### 3. APIAgent

**Location:** `backend/tools/api_agent.py`

**Purpose:** Make HTTP requests and handle OAuth flows.

**Capabilities:**
- GET/POST/PUT/DELETE requests
- Handle authentication (Bearer, Basic, OAuth)
- Parse JSON/XML responses
- Handle rate limits

**API Endpoint:** `POST /api/tools/api`

**Supported Methods:**

#### GET Request
```json
{
  "method": "GET",
  "url": "https://api.example.com/users",
  "headers": {
    "Authorization": "Bearer token123"
  },
  "params": {
    "page": 1,
    "limit": 10
  }
}
```
Response:
```json
{
  "status_code": 200,
  "success": true,
  "headers": {
    "content-type": "application/json"
  },
  "data": {"users": [...]},
  "url": "https://api.example.com/users?page=1&limit=10"
}
```

#### POST Request
```json
{
  "method": "POST",
  "url": "https://api.example.com/users",
  "headers": {
    "Authorization": "Bearer token123",
    "Content-Type": "application/json"
  },
  "body": {
    "name": "John Doe",
    "email": "john@example.com"
  }
}
```
Response:
```json
{
  "status_code": 201,
  "success": true,
  "headers": {...},
  "data": {"id": 123, "name": "John Doe", "email": "john@example.com"},
  "url": "https://api.example.com/users"
}
```

#### PUT/DELETE
Similar to POST, but with `"method": "PUT"` or `"method": "DELETE"`.

---

### 4. DatabaseOperationsAgent

**Location:** `backend/tools/database_operations_agent.py`

**Purpose:** Execute real SQL queries.

**Capabilities:**
- PostgreSQL support
- MySQL support
- SQLite support
- SELECT queries
- INSERT/UPDATE/DELETE operations

**API Endpoint:** `POST /api/tools/database`

**Supported Database Types:**

#### PostgreSQL
```json
{
  "db_type": "postgres",
  "connection": {
    "host": "localhost",
    "port": 5432,
    "database": "mydb",
    "user": "postgres",
    "password": "secret"
  },
  "query": "SELECT * FROM users WHERE id = $1",
  "params": [123]
}
```
Response:
```json
{
  "rows": [
    {"id": 123, "name": "John Doe", "email": "john@example.com"}
  ],
  "row_count": 1,
  "success": true
}
```

#### MySQL
```json
{
  "db_type": "mysql",
  "connection": {
    "host": "localhost",
    "port": 3306,
    "database": "mydb",
    "user": "root",
    "password": "secret"
  },
  "query": "INSERT INTO users (name, email) VALUES (%s, %s)",
  "params": ["Jane Doe", "jane@example.com"]
}
```
Response:
```json
{
  "affected_rows": 1,
  "success": true
}
```

#### SQLite
```json
{
  "db_type": "sqlite",
  "connection": {
    "database": "/path/to/database.db"
  },
  "query": "SELECT * FROM users",
  "params": []
}
```
Response:
```json
{
  "rows": [
    {"id": 1, "name": "John Doe"},
    {"id": 2, "name": "Jane Doe"}
  ],
  "row_count": 2,
  "success": true
}
```

---

### 5. DeploymentOperationsAgent

**Location:** `backend/tools/deployment_operations_agent.py`

**Purpose:** Deploy to cloud platforms.

**Capabilities:**
- Vercel deployment
- Railway deployment
- Netlify deployment

**API Endpoint:** `POST /api/tools/deploy`

**Supported Platforms:**

#### Vercel
```json
{
  "platform": "vercel",
  "project_path": "./my-app",
  "config": {
    "env": {
      "API_KEY": "secret123"
    }
  }
}
```
Response:
```json
{
  "platform": "vercel",
  "url": "https://my-app-abc123.vercel.app",
  "success": true,
  "output": "Deployed to production..."
}
```

#### Railway
```json
{
  "platform": "railway",
  "project_path": "./my-backend"
}
```
Response:
```json
{
  "platform": "railway",
  "success": true,
  "output": "Deployment successful..."
}
```

#### Netlify
```json
{
  "platform": "netlify",
  "project_path": "./dist"
}
```
Response:
```json
{
  "platform": "netlify",
  "url": "https://my-site-abc123.netlify.app",
  "success": true,
  "output": "Deployed to production..."
}
```

---

## Agent DAG Integration

All tool agents are registered in `AGENT_DAG` in `backend/agent_dag.py`:

- **Browser Tool Agent** - depends on `Stack Selector`
- **File Tool Agent** - depends on `Stack Selector`
- **API Tool Agent** - depends on `API Integration`
- **Database Tool Agent** - depends on `Database Agent`
- **Deployment Tool Agent** - depends on `Deployment Agent`

---

## Testing

Run tests with:
```bash
cd backend
python -m pytest tests/test_tool_agents.py -v
```

Test coverage:
- 23 tests passed
- 2 tests skipped (require external resources)
- All core functionality tested:
  - Agent initialization
  - File operations (read, write, delete, list, mkdir)
  - Database operations (SQLite)
  - Error handling
  - AGENT_DAG integration

---

## Dependencies

Required packages (in `requirements.txt`):
- `playwright==1.49.1` - Browser automation
- `httpx==0.28.1` - HTTP requests (already included)
- `asyncpg==0.30.0` - PostgreSQL async driver
- `aiomysql==0.2.0` - MySQL async driver
- `aiosqlite==0.20.0` - SQLite async driver

Install Playwright browsers (for BrowserAgent):
```bash
playwright install
```

---

## Security Considerations

1. **File Operations**: All file operations are scoped to a configurable workspace directory
2. **Database Access**: Requires explicit connection credentials
3. **API Requests**: No built-in rate limiting (implement at application level)
4. **Deployment**: Requires CLI tools (vercel, railway, netlify) to be installed

---

## Error Handling

All agents follow a consistent error response format:
```json
{
  "error": "Error message",
  "success": false,
  "agent": "AgentName"
}
```

---

## Future Enhancements

1. **BrowserAgent**: Add support for authentication flows, cookie management
2. **FileAgent**: Add file watching, compression/decompression
3. **APIAgent**: Add OAuth2 flow helpers, retry mechanisms
4. **DatabaseOperationsAgent**: Add connection pooling, transaction support
5. **DeploymentOperationsAgent**: Add rollback support, environment management

---

## Usage Examples

### Complete Workflow Example

```python
# 1. Scrape data from a website
browser_result = await browser_agent.execute({
    "action": "scrape",
    "url": "https://example.com/data",
    "selector": ".data-table"
})

# 2. Save scraped data to file
file_result = await file_agent.execute({
    "action": "write",
    "path": "scraped_data.html",
    "content": browser_result["html"]
})

# 3. Process and store in database
db_result = await db_agent.execute({
    "db_type": "sqlite",
    "connection": {"database": "app.db"},
    "query": "INSERT INTO scraped_data (content) VALUES (?)",
    "params": [browser_result["text"]]
})

# 4. Deploy application
deploy_result = await deploy_agent.execute({
    "platform": "vercel",
    "project_path": "./my-app"
})
```

---

## Support

For issues or questions, refer to:
- Agent source code in `backend/tools/`
- Test examples in `backend/tests/test_tool_agents.py`
- API documentation at `/docs` endpoint
