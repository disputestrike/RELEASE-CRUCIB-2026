# CrucibAI VS Code Extension

Complete VS Code integration for CrucibAI - transforming the IDE into a powerful AI-assisted development environment with 240+ specialized agents.

**Works in both VS Code and Cursor!** Cursor is built on VS Code and uses the same extension API, so you only need to install once.

## Features

### 💬 Conversational Chat
- Real-time chat interface directly in VS Code
- Multi-turn conversations with context awareness
- Session management and history
- WebSocket streaming for live updates

### 🧠 240+ Specialized Agents
- Organized by domain (Core Building, Security, ML, Blockchain, 3D Graphics, DevOps, etc.)
- Tree view for easy agent discovery
- Agent capability details and documentation
- Quick-launch agent functionality

### 📝 Code Intelligence
- **Code Analysis**: Deep analysis with AST parsing and complexity metrics
- **Test Generation**: Automatic test creation for code snippets
- **Code Explanation**: Natural language code understanding
- **Refactoring**: Intelligent code improvement suggestions

### 🔧 Developer Tools
- **Terminal Integration**: Execute commands and scripts
- **Git Operations**: Version control assistance
- **Test Execution**: Run tests with summary reports
- **Deployment**: Automated deployment assistance

### 📊 Session Management
- Create and manage multiple conversations
- Persistent session history
- Quick access to recent sessions
- Session-specific metadata and context

## Quick Start

### Installation

#### From VS Code Marketplace
1. Open VS Code or Cursor
2. Go to Extensions (Cmd+Shift+X / Ctrl+Shift+X)
3. Search for "CrucibAI"
4. Click Install

#### From Source
```bash
git clone https://github.com/yourusername/crucibai-vscode.git
cd crucib/ide-extensions/vscode
npm install
npm run compile
code --install-extension crucibai-$(cat package.json | grep '"version"' | head -1 | awk -F: '{ print $2 }' | sed 's/[",]//g').vsix
```

### Configuration

1. Open VS Code Settings (Cmd+, / Ctrl+,)
2. Search for "CrucibAI"
3. Set your API endpoint and key:
   - `crucibai.apiEndpoint`: `http://localhost:8000` (or your server)
   - `crucibai.apiKey`: Your authentication token

### First Steps
1. Press `Cmd+Shift+K` (Mac) or `Ctrl+Shift+K` (Windows/Linux) to open chat
2. Type a question and hit Enter
3. Click "Agents" in the left sidebar to explore 240+ specialized agents
4. Try code commands: Select code and press `Cmd+Shift+A` to analyze

## Commands

| Command | Shortcut | Description |
|---------|----------|-------------|
| Open Chat | `Cmd+Shift+K` | Open chat interface |
| Analyze Code | `Cmd+Shift+A` | Analyze selected code |
| Generate Tests | - | Generate tests for code |
| Explain Code | - | Get explanation of code |
| Refactor Code | - | Get refactoring suggestions |
| Run Tests | - | Execute test suite |
| Deploy Project | - | Deploy current project |
| Fix Errors | - | Fix errors in code |
| List Agents | - | View all 240+ agents |

## Configuration

### Essential Settings

```json
{
  "crucibai.apiEndpoint": "http://localhost:8000",
  "crucibai.apiKey": "your-api-key",
  "crucibai.streamingMode": true,
  "crucibai.autoSave": true
}
```

### All Available Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `apiEndpoint` | string | `http://localhost:8000` | Backend API endpoint |
| `apiKey` | string | `""` | Authentication API key |
| `streamingMode` | boolean | `true` | Enable real-time streaming |
| `autoSave` | boolean | `true` | Auto-save sessions |
| `maxContextHistory` | number | `50` | Max conversation turns |
| `theme` | string | `auto` | UI theme (auto/light/dark) |
| `enableAnalytics` | boolean | `true` | Send usage analytics |
| `debug` | boolean | `false` | Enable debug logging |

## Architecture

### Components

- **ChatPanel** (`src/panels/ChatPanel.ts`): Webview UI for conversations
- **CrucibAIClient** (`src/client.ts`): API communication layer
- **AgentsProvider** (`src/providers/AgentsProvider.ts`): Agent discovery and details
- **SessionsProvider** (`src/providers/SessionsProvider.ts`): Session management
- **Main Extension** (`src/extension.ts`): Command registration and lifecycle

### Sidebar Panels

- **Chat**: Real-time conversation interface
- **Agents**: Browse and manage 240+ specialized agents
- **Sessions**: View and switch between conversation sessions

## Development

### Setup

```bash
npm install
npm run compile
npm run watch  # For real-time compilation
```

### Testing

```bash
npm test
npm run debug
```

### Building & Publishing

```bash
npm run package                    # Create VSIX
vsce publish                       # Publish to marketplace
```

## Backend Integration

### Required Endpoints

- `POST /api/chat/message` - Send message
- `POST /api/chat/session/create` - Create session
- `WS /api/chat/ws/{session_id}` - WebSocket stream
- `POST /api/chat/agents/list` - List 240+ agents

### Environment

```bash
CRUCIBAI_API_ENDPOINT=http://localhost:8000
CRUCIBAI_API_KEY=your-secret-key
```

## Performance

- Chat response: < 2 seconds
- Agent discovery: < 1 second
- WebSocket latency: < 100ms
- Memory footprint: ~50-80MB

## Troubleshooting

### Extension Not Showing
- Reload VS Code: `Cmd+R` (Mac) / `Ctrl+R` (Windows/Linux)
- Check Extension panel for "CrucibAI"
- Verify it's enabled (not disabled)

### Connection Issues
- Verify backend is running: `curl http://localhost:8000/health`
- Check API endpoint in settings
- Review backend logs

### Chat Not Responding
- Check WebSocket connection
- Verify session was created
- Restart extension
- Check browser console in DevTools

### Agents Not Loading
- Click "Refresh Agents" in Agents panel
- Check `/api/chat/agents/list` endpoint
- Verify 240 agents in backend DAG

## Support

- **Docs**: https://docs.crucibai.com
- **Issues**: GitHub Issues
- **Email**: support@crucibai.com

## License

MIT

Happy coding with CrucibAI! 🧠✨
