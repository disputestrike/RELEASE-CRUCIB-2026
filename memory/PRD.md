# CrucibAI Platform - Product Requirements Document

## Project Overview
**Name:** CrucibAI  
**Type:** AI App Builder Platform (like Replit, Bolt, Lovable)  
**Created:** February 9, 2026  
**Last Updated:** February 9, 2026
**Status:** MVP Complete - Full Builder Workspace Implemented

---

## What CrucibAI Does
CrucibAI is an AI-powered app builder where users describe what they want in natural language, and AI agents automatically build it. Like Replit Agent, Bolt.new, and Lovable.

---

## Core Features Implemented

### ✅ Landing Page (Premium Dark Theme)
- Clean, minimal design with dark theme (#0A0A0B)
- Prompt input that redirects to workspace
- Quick suggestions (Task manager, Portfolio, etc.)
- FAQ section
- How it works section

### ✅ Full Builder Workspace (`/workspace`)
- **Monaco Code Editor**: Full-featured code editor with syntax highlighting
- **Sandpack Live Preview**: Real-time preview of React applications
- **File Explorer**: Navigate between App.js, index.js, styles.css
- **Console Panel**: Build logs and agent activity tracking
- **Version History**: Track and restore previous versions
- **Chat Interface**: Iterative modifications through natural language

### ✅ Multi-Input Capabilities
- **Text Input**: Standard chat-based prompts
- **Voice Input**: Record audio, transcribe via OpenAI Whisper
- **File Attachments**: Upload images, PDFs, text files for context

### ✅ LLM Model Selection
- Auto Select (best model for the task)
- GPT-4o (OpenAI)
- Claude 3.5 Sonnet (Anthropic)
- Gemini Flash (Google)

### ✅ Multi-Model AI Backend
- Real AI integration (multi-provider LLM)
- Auto-selection based on task type
- Code generation, analysis, RAG capabilities

### ✅ Export & Actions
- Download code as files
- GitHub push (UI ready)
- Deploy button (UI ready)

---

## API Endpoints

### AI/Chat
- `POST /api/ai/chat` - Multi-model AI chat
- `GET /api/ai/chat/history/{session_id}` - Chat history
- `POST /api/ai/analyze` - Document analysis
- `POST /api/rag/query` - RAG-style queries
- `POST /api/search` - Hybrid search

### Voice/Files
- `POST /api/voice/transcribe` - Voice to text (Whisper)
- `POST /api/files/analyze` - File analysis

### Auth
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

### Tokens
- `GET /api/tokens/bundles`
- `POST /api/tokens/purchase`
- `GET /api/tokens/history`
- `GET /api/tokens/usage`

### Projects
- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{id}`
- `GET /api/projects/{id}/logs`

---

## User Flow
1. User visits landing page
2. Types what they want to build OR uses voice input
3. Optionally attaches reference images/files
4. Clicks submit → Redirected to `/workspace?prompt=...`
5. Workspace loads with default template
6. AI generates code based on prompt
7. Code displayed in Monaco editor
8. Live preview shown in Sandpack
9. User iterates via chat
10. Download or deploy

---

## Tech Stack
- **Frontend**: React 19, Tailwind CSS, Framer Motion
- **Code Editor**: Monaco Editor
- **Live Preview**: Sandpack (CodeSandbox)
- **Backend**: Python FastAPI
- **Database**: MongoDB (via Motor)
- **AI**: Multi-model (GPT-4o, Claude, Gemini, Whisper)

---

## Files Structure
```
/app/
├── backend/
│   ├── server.py        # FastAPI with all endpoints
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── package.json
│   └── src/
│       ├── App.js           # Router
│       ├── pages/
│       │   ├── LandingPage.jsx   # Entry point
│       │   ├── Workspace.jsx     # Full builder
│       │   ├── AuthPage.jsx
│       │   └── Dashboard.jsx
│       └── components/ui/   # Shadcn components
└── memory/
    └── PRD.md
```

---

## Testing Status
- Backend: 100% (24/24 tests passed)
- Frontend: 95% (all features working)
- Test report: `/app/test_reports/iteration_4.json`

---

## Completed in This Session
1. ✅ Full Workspace page with Monaco + Sandpack
2. ✅ File explorer with syntax icons
3. ✅ Console panel for build logs
4. ✅ Version history with rollback
5. ✅ Voice input (Whisper integration)
6. ✅ File attachment support
7. ✅ LLM model selector (GPT-4o, Claude, Gemini)
8. ✅ Landing page → Workspace redirect flow
9. ✅ Backend voice transcription endpoint
10. ✅ Backend file analysis endpoint

---

## Upcoming/Future Tasks

### P1 - Next Phase
- [x] Real-time code streaming (character by character) – done via /api/ai/chat/stream
- [x] Error detection and auto-fix – Auto-fix button after failed build
- [x] Screenshot to code feature – /api/ai/image-to-code + Workspace flow
- [x] GitHub export – ZIP + README (create repo, upload); full OAuth push later
- [x] Vercel/Netlify deployment – ZIP + README for vercel.com/new and netlify.com/drop
- [ ] Actual GitHub OAuth + API push (optional)
- [ ] Vercel/Netlify API deploy with user token (optional)

### P2 - Later
- [ ] Figma import
- [ ] Custom domains
- [ ] Team collaboration
- [ ] Database integrations (Supabase)
- [ ] Payment integration (PayPal)

### P3 - Cleanup
- [ ] Remove legacy components (ProjectBuilder, AgentMonitor, etc.)
- [ ] Consolidate unused routes
- [ ] Performance optimization

---

*Last Updated: February 9, 2026*
