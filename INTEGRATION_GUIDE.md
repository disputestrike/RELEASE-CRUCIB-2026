# CrucibAI Integration Guide

Complete implementation guide for the CrucibAI Copilot system - connecting backend orchestration with VS Code extension.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     VS Code Extension                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  ChatPanel (WebView)  │  Agents Tree  │  Sessions Tree   │   │
│  └──────────────────────────────────────────────────────────┘   │
│           ↓                      ↓                    ↓           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │            CrucibAIClient & SessionManager               │   │
│  │  REST API + WebSocket Communication                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                           ↓ ↑
              HTTP REST + WebSocket (JSON)
                           ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Chat Routes  │  Agent Routes  │  Session Routes        │   │
│  └──────────────────────────────────────────────────────────┘   │
│              ↓              ↓              ↓                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Semantic Router  │  Sub-Agent Orchestrator             │    │
│  │  Context Manager  │  Tool Chain Executor                │    │
│  └────────────────────────────────────────────────────────┘    │
│              ↓              ↓              ↓                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │         DAG: 240 Specialized Agents                     │    │
│  │  Core Building │ Security │ ML │ Blockchain │ DevOps   │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Checklist

### ✅ Phase 1: Core Copilot Capabilities (COMPLETE)

- [x] **Code Analysis Agent** (`backend/agents/code_analysis_agent.py`)
  - AST parsing with complexity metrics
  - Code quality scoring
  - Pattern detection and suggestions
  - Issue identification

- [x] **Workspace Explorer Agent** (`backend/agents/workspace_explorer_agent.py`)
  - Recursive file discovery
  - Semantic search across codebase
  - Dependency analysis
  - Project structure mapping

- [x] **Terminal Agent** (`backend/tools/terminal_agent.py`)
  - Sandboxed command execution
  - Test running capability
  - Git command support
  - Build system integration

- [x] **Context Manager Service** (`backend/services/conversation_manager.py`)
  - Multi-turn conversation tracking
  - Sliding window memory management
  - Context enrichment with keyword extraction
  - Session timeout handling

- [x] **Semantic Router Service** (`backend/services/semantic_router.py`)
  - Intent classification (8 types)
  - Confidence-based agent routing
  - Parameter extraction
  - Learned routing pattern tracking

### ✅ Phase 2: Enhanced Orchestration (COMPLETE)

- [x] **Sub-Agent Orchestrator** (`backend/orchestration/sub_agent_orchestrator.py`)
  - Recursive multi-agent decomposition
  - Parallel and sequential execution modes
  - Execution tree tracking
  - Max depth limiting (5 levels)

- [x] **Tool Chain Executor** (`backend/services/tool_chain_executor.py`)
  - Multi-step tool orchestration
  - Sequential and parallel execution
  - Parameter resolution across steps
  - Tool result caching

- [x] **WebSocket Handler** (`backend/services/websocket_handler.py`)
  - Real-time streaming execution updates
  - 9+ message types (agent_start, agent_progress, etc.)
  - Connection lifecycle management
  - Progressive message streaming

### ✅ Phase 3: Conversational Interface (COMPLETE)

- [x] **Chat REST API** (`backend/routes/chat.py`)
  - Multi-turn conversation endpoint
  - Session management endpoints
  - Suggestion generation
  - Intent detection and routing

- [x] **Chat WebSocket API** (`backend/routes/chat_websocket.py`)
  - Real-time bidirectional streaming
  - Live agent execution updates
  - Connection management
  - Test HTML included

- [x] **Chat React Component** (`frontend/src/components/ChatInterface.tsx`)
  - Message rendering with auto-scroll
  - Typing indicators
  - Suggestion display
  - Responsive dark theme

- [x] **Chat Component Styling** (`frontend/src/components/ChatInterface.css`)
  - Premium dark-themed design
  - Gradient backgrounds and animations
  - Mobile-responsive layouts
  - Accessibility-focused contrast

### ✅ Phase 4: Advanced Reasoning (COMPLETE)

- [x] **Clarification Agent** (`backend/agents/clarification_agent.py`)
  - Ambiguity scoring (0-1 scale)
  - Intelligent question generation
  - Assumption tracking
  - Information gap identification

- [x] **Error Recovery System** (`backend/services/error_recovery_system.py`)
  - 5 recovery strategies implemented
  - Adaptive strategy selection
  - Success rate tracking
  - Actionable error insights

### ✅ Phase 5: VS Code Extension (COMPLETE)

- [x] **Extension Package Config** (`ide-extensions/vscode/package.json`)
  - 8+ command registrations
  - 3 sidebar panels (Chat, Agents, Sessions)
  - 10+ keybindings
  - Configuration schema

- [x] **Extension Entry Point** (`ide-extensions/vscode/src/extension.ts`)
  - Complete lifecycle management
  - Command handler registration
  - Configuration watching
  - Tree provider registration
  - Session and agent manager integration

- [x] **Chat Panel Component** (`ide-extensions/vscode/src/panels/ChatPanel.ts`)
  - Webview with embedded UI
  - Message rendering
  - Session management
  - Error handling
  - SessionManager integration

- [x] **CrucibAI Client** (`ide-extensions/vscode/src/client.ts`)
  - REST API methods for all endpoints
  - WebSocket connection manager
  - Session creation and management
  - Agent discovery
  - Suggestion fetching

- [x] **Agents Provider** (`ide-extensions/vscode/src/providers/AgentsProvider.ts`)
  - AgentsProvider tree view (240 agents)
  - Category-based organization
  - AgentDetailsPanel side view
  - Agent capability display

- [x] **Sessions Provider** (`ide-extensions/vscode/src/providers/SessionsProvider.ts`)
  - SessionsProvider tree view
  - SessionManager lifecycle
  - Message tracking per session
  - Active session highlighting

- [x] **VS Code Extension README** (`ide-extensions/vscode/README.md`)
  - Complete feature documentation
  - Configuration guide
  - Development setup
  - Troubleshooting section
  - API reference

- [x] **Integration Guide** (this file)
  - System architecture diagram
  - Component relationships
  - Data flow documentation

## Data Flow

### User Message Flow

```
1. User types message in ChatPanel
   └─> postMessage({ type: 'message', content: '...' })

2. ChatPanel._setupMessageHandling()
   └─> if (!sessionId) createSession()
   └─> client.sendMessage(sessionId, content)

3. CrucibAIClient.sendMessage()
   └─> HTTP POST to /api/chat/message
   └─> Returns response

4. Backend: chat.py::send_chat_message()
   ├─> Extract intent → Semantic Router
   ├─> Select agent(s) based on intent
   ├─> Add message to conversation context
   └─> Execute agent(s)

5. Backend: Sub-Agent Orchestrator
   ├─> If single agent: execute directly
   ├─> If multi-agent: spawn sub-agents
   └─> Handle parallel/sequential execution

6. Backend: Tool Chain Executor
   ├─> Break down into tool steps
   ├─> Execute tools in order
   ├─> Pass results between steps
   └─> Compile final response

7. WebSocket Streaming (if enabled)
   ├─> agent_start message
   ├─> Multiple agent_progress updates
   ├─> Tool execution messages
   └─> agent_complete with result

8. Response back to ChatPanel
   └─> postMessage({ type: 'response', content: '...' })

9. ChatPanel renders response
   └─> addMessage(text, 'assistant')
   └─> Scrolls to bottom
```

### Agent Discovery Flow

```
1. User clicks Agents panel
   └─> AgentsProvider.getChildren() called

2. AgentsProvider loads agents
   ├─> CrucibAIClient.listAgents()
   ├─> HTTP GET to /api/chat/agents/list
   └─> Groups by category

3. Backend: chat.py::get_agents_list()
   ├─> Read from agent_dag.py (240 agents)
   ├─> Organize by category
   └─> Return JSON with agent metadata

4. AgentsProvider organizes tree
   ├─> Create root category items
   ├─> Create agent items per category
   └─> Register click handlers

5. User clicks agent
   └─> AgentDetailsPanel.show() opens

6. AgentDetailsPanel displays
   ├─> Agent name, category, status
   ├─> Description and capabilities
   ├─> Parameters and dependencies
   └─> "Launch Agent" button
```

### Session Management Flow

```
1. ChatPanel constructor
   ├─> Check current session from SessionManager
   ├─> If none: call sessionManager.createSession()
   └─> SessionManager → CrucibAIClient.createSession()

2. Backend: chat.py::create_session()
   ├─> Generate unique session ID
   ├─> Create session in database
   └─> Return session_id

3. Frontend stores session
   ├─> SessionManager.sessionStorage[id] = session
   ├─> globalThis['crucibaiSessions'].push(session)
   └─> SessionsProvider.refresh()

4. SessionsProvider updates tree
   ├─> Retrieve stored sessions
   ├─> Sort by creation date (newest first)
   └─> Display with title and timestamps

5. User clicks session
   └─> Execute crucibai.openSession command
   └─> sessionManager.setCurrentSession(id)
   └─> ChatPanel loads session messages
```

## API Endpoints

### Chat Endpoints

#### POST /api/chat/message
Send a message to an agent.

**Request:**
```json
{
  "session_id": "session-uuid",
  "message": "Analyze this code function",
  "context": {}
}
```

**Response:**
```json
{
  "session_id": "session-uuid",
  "assistant_response": "The function...",
  "agent_used": "code_analysis_agent",
  "metadata": {
    "execution_time": 1.234,
    "tokens_used": 450
  }
}
```

#### POST /api/chat/session/create
Create a new conversation session.

**Response:**
```json
{
  "session_id": "session-uuid",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### GET /api/chat/session/{id}
Get session details and history.

**Response:**
```json
{
  "session_id": "session-uuid",
  "created_at": "2024-01-15T10:30:00Z",
  "messages": [
    {
      "id": "msg-1",
      "role": "user",
      "content": "...",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

#### POST /api/chat/agents/list
List all 240 available agents.

**Response:**
```json
{
  "categories": {
    "Core Building": [
      {
        "id": "code_analysis",
        "name": "Code Analysis Agent",
        "description": "...",
        "capabilities": ["code_analysis", "quality_scoring"]
      }
    ]
  },
  "total": 240
}
```

#### WS /api/chat/ws/{session_id}
WebSocket for real-time streaming.

**Incoming Messages:**
```json
{
  "type": "message",
  "content": "Your prompt here"
}
```

**Outgoing Messages:**
```json
{
  "type": "agent_start",
  "agent_name": "code_analysis_agent",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Component Interfaces

### CrucibAIClient

```typescript
class CrucibAIClient {
  constructor(endpoint: string, apiKey?: string)
  
  async sendMessage(sessionId: string, message: string): Promise<any>
  async createSession(): Promise<string>
  async getSession(sessionId: string): Promise<any>
  async listAgents(): Promise<any[]>
  async getAgentDefinition(agentName: string): Promise<any>
  async getSuggestions(sessionId: string, input: string): Promise<string[]>
  
  connectWebSocket(sessionId: string, onMessage: Function): WebSocket
}
```

### SessionManager

```typescript
class SessionManager {
  static getInstance(client: CrucibAIClient): SessionManager
  
  async createSession(title?: string): Promise<string>
  async getCurrentSession(): Promise<SessionData>
  async setCurrentSession(id: string): Promise<void>
  
  addMessageToSession(sessionId: string, message: MessageData): void
  getSessionMessages(sessionId: string): MessageData[]
  getAllSessions(): SessionData[]
  deleteSession(sessionId: string): void
}

interface SessionData {
  id: string
  title: string
  created_at: string
  messages: MessageData[]
  metadata: Record<string, any>
}

interface MessageData {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  agentUsed?: string
}
```

## Environment Configuration

### Backend (.env)

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=false

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/crucibai
REDIS_URL=redis://localhost:6379

# LLM Configuration
CEREBRAS_API_KEY=your-key
ANTHROPIC_API_KEY=your-key

# Agents
AGENT_MAX_DEPTH=5
AGENT_TIMEOUT=30
TOOL_TIMEOUT=15

# Session
SESSION_TIMEOUT=3600
MAX_CONTEXT_WINDOW=50
```

### Extension (settings.json)

```json
{
  "crucibai.apiEndpoint": "http://localhost:8000",
  "crucibai.apiKey": "",
  "crucibai.streamingMode": true,
  "crucibai.autoSave": true,
  "crucibai.maxContextHistory": 50,
  "crucibai.theme": "auto",
  "crucibai.enableAnalytics": true,
  "crucibai.debug": false
}
```

## Testing Strategy

### Backend Tests

```python
# test_chat_endpoints.py
def test_send_message()
def test_create_session()
def test_get_session()
def test_agent_routing()
def test_websocket_streaming()

# test_agents.py
def test_code_analysis_agent()
def test_workspace_explorer_agent()
def test_semantic_router()
```

### Frontend Tests

```typescript
// src/__tests__/ChatPanel.test.ts
describe('ChatPanel', () => {
  test('sends message to backend')
  test('displays response from agent')
  test('handles WebSocket errors')
})

// src/__tests__/SessionManager.test.ts
describe('SessionManager', () => {
  test('creates new session')
  test('persists messages')
  test('retrieves session history')
})
```

### Integration Tests

```bash
# Full end-to-end flow
1. Start backend server
2. Install extension in VS Code
3. Configure API endpoint
4. Send chat message
5. Verify agent execution
6. Check WebSocket streaming
7. Validate session persistence
```

## Performance Optimization

### Caching Strategy

- **Agent List**: Cache for 30 minutes (240 agents)
- **Session History**: Cache last 50 messages per session
- **Tool Results**: Cache for 5 minutes per tool
- **Semantic Routing**: Cache intent patterns

### Batch Operations

- Group multiple tool calls into one request
- Batch WebSocket message delivery
- Debounce rapid chat messages

### Resource Limits

- Max 5 concurrent agent executions
- Max 30 second agent timeout
- Max 15 second tool timeout
- Max 80MB extension memory

## Deployment

### Docker Deployment

```bash
# Backend
docker build -t crucibai-backend .
docker run -p 8000:8000 crucibai-backend

# Extension: Distribute VSIX manually or via marketplace
```

### Production Checklist

- [ ] environment variables configured
- [ ] SSL/TLS enabled for WebSocket (wss://)
- [ ] Database backups configured
- [ ] Rate limiting enabled
- [ ] Error monitoring set up
- [ ] Performance metrics logged
- [ ] Extension published to marketplace
- [ ] Documentation updated
- [ ] User onboarding completed

## Troubleshooting

### Extension Issues

| Problem | Solution |
|---------|----------|
| Chat not responding | Verify backend `/health` endpoint |
| Agents not loading | Check API endpoint and network |
| WebSocket timeout | Enable streaming mode in settings |
| Session not saving | Check browser developer tools for errors |

### Backend Issues

| Problem | Solution |
|---------|----------|
| Agent timeout | Increase `AGENT_TIMEOUT` variable |
| Route not matching | Check semantic router intent patterns |
| Memory leak | Monitor subprocess cleanup |
| Database connection | Verify `DATABASE_URL` connection string |

## Future Enhancements

- [ ] Voice input/output
- [ ] Code lens integration
- [ ] Inline suggestions
- [ ] Custom agent creation
- [ ] Plugin system
- [ ] Workflow automation
- [ ] Team collaboration
- [ ] Analytics dashboard

## Support

For issues or questions:
- Check logs: `crucibai.logLevel` = debug
- Review backend API routes
- Verify network connectivity
- Check documentation at docs.crucibai.com
