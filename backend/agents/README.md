# Specialized Agents System

This directory contains the implementation of 10 production-ready specialized agents that form the core of the CrucibAI project generation system.

## Overview

The specialized agents system provides a modular, extensible architecture for AI-powered project generation. Each agent is responsible for a specific aspect of software development, from planning to deployment.

## Architecture

### Base Components

- **BaseAgent** (`base_agent.py`): Abstract base class that all agents inherit from
- **AgentRegistry** (`registry.py`): Registry system for discovering and managing agents
- **AgentValidationError**: Exception raised when validation fails

### Key Features

1. **Input/Output Validation**: Every agent validates its inputs and outputs
2. **LLM Integration**: Built-in support for OpenAI and Anthropic models
3. **Agent Chaining**: Agents can pass context to each other
4. **Registry Pattern**: Dynamic agent discovery and instantiation
5. **Type Safety**: Full type hints for all methods

## The 10 Specialized Agents

### 1. PlannerAgent
**Purpose**: Analyzes requirements and creates structured execution plan with task dependencies.

**Input**: `user_prompt` (string, >10 characters)

**Output**: 
- Project summary and duration estimate
- Complexity level (low/medium/high)
- 5-15 tasks with dependencies

### 2. StackSelectorAgent
**Purpose**: Selects optimal technology stack based on requirements.

**Input**: `user_prompt`, optional `planner_output`

**Output**:
- Frontend stack (framework, language, styling, state management)
- Backend stack (framework, language)
- Database (primary, caching)
- Deployment platforms
- Additional tools

### 3. DesignAgent
**Purpose**: Creates UI/UX specifications and design system.

**Input**: `user_prompt`, optional `stack_output`

**Output**:
- Design system (colors, typography, spacing)
- Layout specifications
- Component definitions
- Mockup description

### 4. DatabaseAgent
**Purpose**: Designs database schema, migrations, and ORM models.

**Input**: `user_prompt`, optional `stack_output`

**Output**:
- Schema with tables and relationships
- Migration files
- ORM models (Prisma, SQLAlchemy, etc.)

### 5. BackendAgent
**Purpose**: Generates complete backend API code.

**Input**: `user_prompt`, optional `stack_output`, `database_output`

**Output**:
- Backend files (main, models, routes)
- API specification
- Setup instructions

### 6. FrontendAgent
**Purpose**: Generates complete frontend code.

**Input**: `user_prompt`, optional `stack_output`, `design_output`

**Output**:
- Frontend files (components, config, package.json)
- Architecture overview
- Setup instructions

### 7. TestGenerationAgent
**Purpose**: Generates unit, integration, and E2E tests.

**Input**: `user_prompt`, optional `frontend_output`, `backend_output`

**Output**:
- Test files (unit, integration, E2E)
- Test framework configuration
- Coverage config
- Run commands

### 8. SecurityAgent
**Purpose**: Security audit and vulnerability scanning.

**Input**: `user_prompt`, optional `frontend_output`, `backend_output`

**Output**:
- Vulnerability findings with fixes
- Security configurations
- Security score
- Recommendations

### 9. DeploymentAgent
**Purpose**: Creates deployment configurations.

**Input**: `user_prompt`, optional `stack_output`

**Output**:
- Deployment files (Dockerfile, CI/CD, etc.)
- Deployment targets and instructions
- Environment variables

### 10. DocumentationAgent
**Purpose**: Generates comprehensive documentation.

**Input**: `user_prompt`, optional outputs from all other agents

**Output**:
- Documentation files (README, API docs, etc.)
- OpenAPI specification
- Architecture diagrams
- Setup guide

## Usage

### Basic Usage

```python
from agents.registry import AgentRegistry

# Get an agent
PlannerAgent = AgentRegistry.get_agent("PlannerAgent")
planner = PlannerAgent(llm_client=None, config={})

# Prepare context
context = {
    "user_prompt": "Build a todo app with authentication"
}

# Run the agent
result = await planner.run(context)
print(result)
```

### Chaining Agents

```python
# Step 1: Plan the project
planner_result = await planner.run({
    "user_prompt": "Build a todo app"
})

# Step 2: Select technology stack (uses planner output)
stack_selector = AgentRegistry.get_agent("StackSelectorAgent")()
stack_result = await stack_selector.run({
    "user_prompt": "Build a todo app",
    "planner_output": planner_result
})

# Step 3: Design database (uses stack output)
database_agent = AgentRegistry.get_agent("DatabaseAgent")()
database_result = await database_agent.run({
    "user_prompt": "Build a todo app",
    "stack_output": stack_result
})

# Continue chaining...
```

### API Endpoint

```bash
# List all registered agents
GET /api/agents/v2

# Response:
{
  "agents": [
    {
      "name": "PlannerAgent",
      "description": "Analyzes requirements and creates structured execution plan.",
      "class": "PlannerAgent"
    },
    ...
  ],
  "count": 10,
  "version": "v2"
}
```

## Development

### Creating a New Agent

1. **Inherit from BaseAgent**:
```python
from agents.base_agent import BaseAgent, AgentValidationError
from agents.registry import AgentRegistry

@AgentRegistry.register
class MyAgent(BaseAgent):
    """Agent description."""
    
    def validate_input(self, context):
        super().validate_input(context)
        # Add validation logic
        return True
    
    def validate_output(self, result):
        super().validate_output(result)
        # Add validation logic
        return True
    
    async def execute(self, context):
        # Agent logic
        response, tokens = await self.call_llm(
            user_prompt=context["user_prompt"],
            system_prompt="...",
            model="gpt-4o"
        )
        data = self.parse_json_response(response)
        return data
```

2. **Add to `__init__.py`**:
```python
from agents.my_agent import MyAgent

__all__ = [..., "MyAgent"]
```

3. **Write tests**:
```python
def test_my_agent():
    agent = MyAgent(llm_client=None, config={})
    assert agent.validate_input({"user_prompt": "test"})
```

### Running Tests

```bash
# Run all agent tests
pytest backend/tests/test_specialized_agents.py -v

# Run integration tests
pytest backend/tests/test_agent_integration.py -v

# Run specific agent tests
pytest backend/tests/test_planner_agent.py -v
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required for GPT models
- `ANTHROPIC_API_KEY`: Required for Claude models

### Model Selection

Each agent can use different models:
- GPT-4o: For complex code generation (Frontend, Backend, Database)
- GPT-4o-mini: For simpler tasks (Planning, Stack Selection)
- Claude models: Alternative to GPT models

## Error Handling

All agents follow consistent error handling:

```python
from agents.base_agent import AgentValidationError

try:
    result = await agent.run(context)
except AgentValidationError as e:
    print(f"Validation error: {e}")
except Exception as e:
    print(f"Execution error: {e}")
```

## Best Practices

1. **Always validate input**: Check required fields before execution
2. **Structured output**: Return well-defined JSON structures
3. **Error messages**: Provide clear, actionable error messages
4. **Context passing**: Use previous agent outputs as context
5. **Documentation**: Document input/output schemas in docstrings
6. **Testing**: Write comprehensive tests for each agent

## Token Usage Estimates

- **PlannerAgent**: 1500-2000 tokens
- **StackSelectorAgent**: 1000-1500 tokens
- **DesignAgent**: 1000-1500 tokens
- **DatabaseAgent**: 1500-2000 tokens
- **BackendAgent**: 3000-4000 tokens
- **FrontendAgent**: 4000-6000 tokens (largest)
- **TestGenerationAgent**: 2000-3000 tokens
- **SecurityAgent**: 1500-2000 tokens
- **DeploymentAgent**: 1000-1500 tokens
- **DocumentationAgent**: 2000-3000 tokens

**Total per full generation**: ~20,000-30,000 tokens

## Examples

See `example_agent_usage.py` for complete examples of:
- Individual agent usage
- Agent chaining
- Context passing
- Error handling

## License

Part of the CrucibAI project.
