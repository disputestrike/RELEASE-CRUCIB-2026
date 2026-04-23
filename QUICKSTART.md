# CrucibAI: Quick Start Guide

Get up and running with CrucibAI in 5 minutes.

## 1. Install Backend (2 minutes)

```bash
# Navigate to project
cd crucib

# Install Python dependencies
pip install -r requirements.txt

# Create database
python -c "from alembic.config import Config; from alembic.script import ScriptDirectory; from alembic.runtime.migration import MigrationContext; from alembic.operations import Operations; ..."

# Start backend server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 2. Verify Backend is Working

```bash
# In another terminal
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "agents": 240, "uptime": 0.123}
```

## 3. Install VS Code Extension (2 minutes)

### Option A: From Source

```bash
cd crucib/ide-extensions/vscode

# Install dependencies
npm install

# Build
npm run compile

# Install in VS Code
code --install-extension crucibai-1.0.0.vsix
```

### Option B: From Marketplace

1. Open VS Code
2. Press `Cmd+Shift+X` (Mac) / `Ctrl+Shift+X` (Windows/Linux)
3. Search "CrucibAI"
4. Click "Install"

## 4. Configure Extension (1 minute)

1. Open VS Code Settings: `Cmd+,` (Mac) / `Ctrl+,` (Windows/Linux)
2. Search "CrucibAI"
3. Set these values:

```json
{
  "crucibai.apiEndpoint": "http://localhost:8000",
  "crucibai.apiKey": "",
  "crucibai.streamingMode": true
}
```

## 5. Launch Chat (0 minutes)

1. Press `Cmd+Shift+K` (Mac) / `Ctrl+Shift+K` (Windows/Linux)
2. Type a message
3. Press Enter
4. Enjoy! 🚀

---

## First Things to Try

### Analyze Code

```python
# Select this code in VS Code:
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Press Cmd+Shift+A (Mac) / Ctrl+Shift+A (Windows/Linux)
# Command: "Analyze Code"
# AI will explain complexity, suggest optimizations
```

### Explore Agents

1. Look at left sidebar
2. Click "Agents" panel
3. Browse 240+ agents by category
4. Click any agent to see details

### Manage Sessions

1. Click "Sessions" panel in sidebar
2. Create new conversation
3. Switch between sessions
4. See conversation history

---

## Troubleshooting

### "Connection refused" error

**Problem:** Backend not running
**Solution:**
```bash
# In backend directory
python -m uvicorn main:app --port 8000 --reload
```

### "Extension not found" 

**Problem:** Extension not installed
**Solution:**
```bash
# Reload VS Code
Cmd+R (Mac) / Ctrl+R (Windows/Linux)

# Check Extensions panel
Make sure CrucibAI is enabled
```

### Chat shows "Loading..." forever

**Problem:** Backend API endpoint wrong
**Solution:**
1. Open Settings: `Cmd+,`
2. Search "crucibai.apiEndpoint"
3. Set to: `http://localhost:8000`

### "Cannot find 240 agents"

**Problem:** Backend not fully loaded
**Solution:**
```bash
# Check backend has agents
curl http://localhost:8000/api/chat/agents/list

# Should return ~240 agents
# If less, restart backend
```

---

## Common Commands

| Command | Shortcut |
|---------|----------|
| Open Chat | `Cmd+Shift+K` |
| Analyze Code | `Cmd+Shift+A` |
| Send Message | `Enter` |
| New Line | `Shift+Enter` |

---

## Architecture

```
┌─────────────┐
│  VS Code    │  ← You are here
│  Extension  │
└──────┬──────┘
       │ REST + WebSocket
       ↓
┌─────────────────────┐
│  FastAPI Backend    │
│  (Port 8000)        │
└──────┬──────────────┘
       │
       ↓
┌─────────────────────┐
│  240 Agents DAG     │
│  + LLM Integration  │
└─────────────────────┘
```

---

## Next Steps

1. ✅ Backend server running
2. ✅ Extension installed
3. ✅ Sent first chat message
4. Next: Explore agent capabilities
5. Then: Try code analysis, testing, deployment

---

## Documentation

| Document | Purpose |
|----------|---------|
| [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) | Full project overview |
| [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) | System architecture & APIs |
| [ide-extensions/vscode/README.md](ide-extensions/vscode/README.md) | Extension documentation |

---

## Performance Tips

1. **Enable Streaming**: Fastest real-time updates
   ```json
   "crucibai.streamingMode": true
   ```

2. **Limit Context**: Free up memory
   ```json
   "crucibai.maxContextHistory": 25
   ```

3. **Close Unused Sessions**: Reduce backend load
   - Sessions Panel → Right-click → Delete

---

## Getting Help

- 🐛 **Bugs**: GitHub Issues
- 💬 **Questions**: GitHub Discussions  
- 📖 **Docs**: See documentation files above
- 📧 **Email**: support@crucibai.com

---

## You're All Set! 🎉

Start using CrucibAI to:
- ✨ Analyze code instantly
- 🧪 Generate tests automatically
- 🚀 Deploy with confidence
- 📚 Understand complex projects
- 🔧 Refactor code intelligently

**Enjoy your AI development assistant!**
