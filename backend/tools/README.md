# CrucibAI Tool Agents

This directory contains 5 real tool agents that provide powerful automation capabilities:

## Agents

1. **BrowserAgent** (`browser_agent.py`) - Browser automation with Playwright
2. **FileAgent** (`file_agent.py`) - File system operations
3. **APIAgent** (`api_agent.py`) - HTTP requests
4. **DatabaseOperationsAgent** (`database_operations_agent.py`) - SQL queries
5. **DeploymentOperationsAgent** (`deployment_operations_agent.py`) - Cloud deployment

## Quick Start

All agents inherit from `BaseAgent` and provide an async `execute()` method.

### Example Usage

```python
from tools.file_agent import FileAgent

# Initialize agent
agent = FileAgent(llm_client=None, config={"workspace": "./workspace"})

# Execute action
result = await agent.execute({
    "action": "write",
    "path": "hello.txt",
    "content": "Hello, World!"
})

print(result)
# {'path': '/workspace/hello.txt', 'size': 13, 'success': True}
```

## API Endpoints

All agents are accessible via REST API:

- `POST /api/tools/browser` - Browser automation
- `POST /api/tools/file` - File operations
- `POST /api/tools/api` - HTTP requests
- `POST /api/tools/database` - SQL queries
- `POST /api/tools/deploy` - Cloud deployment

## Documentation

See [TOOL_AGENTS_DOCUMENTATION.md](../TOOL_AGENTS_DOCUMENTATION.md) for detailed documentation including:
- Complete API reference
- Request/response examples
- Configuration options
- Security considerations

## Testing

Run tests:
```bash
cd backend
python -m pytest tests/test_tool_agents.py -v
```

## Dependencies

Install required packages:
```bash
pip install -r requirements.txt
playwright install  # For BrowserAgent
```
