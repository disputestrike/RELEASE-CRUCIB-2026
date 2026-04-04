---
name: ai-chatbot-builder
description: Build an AI-powered chatbot or conversational interface with multi-agent support, knowledge base integration, streaming responses, and embeddable chat widget. Use when the user wants to create a chatbot, AI assistant, customer support bot, conversational UI, or any LLM-powered chat interface. Triggers on phrases like "build a chatbot", "create an AI assistant", "I need a customer support bot", "build a chat interface with AI", "create an agent that answers questions".
metadata:
  version: '1.0'
  category: build
  icon: 🤖
  color: '#ec4899'
---

# AI Chatbot Builder

## When to Use This Skill

Apply this skill when the user wants to build a conversational AI interface:

- "Build me a chatbot for my website"
- "Create an AI customer support assistant"
- "I need a chat interface that uses GPT/Claude"
- "Build a knowledge base Q&A bot"
- Any request for a chatbot, AI assistant, conversational agent, or chat UI

## What This Skill Builds

A production-ready AI chatbot application:

**Chat Interface**
- Clean, modern chat UI (messages, typing indicator, timestamps)
- Streaming responses (real-time token-by-token output)
- Multi-turn conversation history
- Message copy, regenerate, and thumbs up/down feedback
- File/image attachment support
- Voice input via Web Speech API

**Agent System**
- Multiple persona/agent selection (e.g., Support, Sales, Technical)
- System prompt configuration per agent
- Conversation starters and suggested questions
- Agent handoff between specializations

**Knowledge Base (RAG)**
- Document upload (PDF, TXT, URL)
- Text chunking and embedding
- Vector search for relevant context
- Source citation in responses
- Confidence scoring

**Embeddable Widget**
- Copy-paste embed code (`<script>` tag)
- Configurable: colors, welcome message, position
- Minimizable chat bubble
- Mobile-responsive

**Backend**
- Streaming API endpoint (`/api/chat`)
- OpenAI / Anthropic / Cerebras LLM integration
- Conversation persistence in DB
- Rate limiting and abuse prevention
- Usage tracking per session/user

**Analytics**
- Message volume charts
- Popular questions report
- Escalation/unanswered rate
- Average conversation length

## Instructions

1. **Define the chatbot purpose** — extract: domain (support, sales, general), target users, tone (friendly/professional/technical), LLM preference, knowledge sources

2. **Build in 4 passes**:
   - Pass 1: Config + types + DB schema (conversations, messages, knowledge_sources)
   - Pass 2: Chat UI (message bubbles, input, streaming display, agent selector)
   - Pass 3: Backend API (streaming endpoint, RAG retrieval, conversation storage)
   - Pass 4: Knowledge base upload UI + embed widget + analytics

3. **Streaming implementation**:
   - Use Server-Sent Events (SSE) or chunked response
   - Frontend renders tokens as they arrive
   - Never buffer entire response before displaying

4. **RAG implementation**:
   - Chunk documents at ~500 tokens with overlap
   - Use OpenAI `text-embedding-3-small` for embeddings
   - Store vectors in PostgreSQL with pgvector (or use simple cosine similarity on JSONB)
   - Retrieve top-3 most relevant chunks and inject into system prompt

5. **Code must include** complete LLM provider setup with fallback chain

## Example Input → Output

Input: "Build a customer support chatbot for a SaaS product — it should answer questions from our docs, escalate to human if it can't help, and collect user satisfaction ratings"

Output includes:
- `/src/components/ChatWidget.tsx` — embeddable chat bubble + window
- `/src/pages/ChatPage.tsx` — full-page chat interface
- `/src/pages/KnowledgeBase.tsx` — admin doc upload + management
- `/src/pages/Analytics.tsx` — chat metrics dashboard
- `/server/routes/chat.ts` — streaming SSE endpoint with RAG
- `/server/services/rag.ts` — embedding + retrieval logic
- `/database/schema.sql` — conversations, messages, knowledge_docs, embeddings
