---
name: web-app-builder
description: Build production-ready full-stack web applications from a plain-language description. Use when the user wants to create a web app, SaaS product, dashboard, CRUD app, portal, or any browser-based application. Triggers on phrases like "build me a web app", "create a platform", "I need a website that does X", "build a full-stack app". Generates TypeScript React frontend + Express/Node backend + PostgreSQL schema + auth + API routes + deployment config.
metadata:
  version: '1.0'
  category: build
  icon: 🌐
  color: '#3b82f6'
---

# Web App Builder

## When to Use This Skill

Apply this skill when the user wants to build any browser-based application:

- "Build me a web app for managing X"
- "Create a platform where users can Y"
- "I need a full-stack application with auth and a dashboard"
- "Build a React app with a backend"
- Any request for a web application, portal, or browser-based tool

## What This Skill Builds

A production-ready full-stack web application:

**Frontend (React + TypeScript)**
- Multi-page app with React Router
- Authentication UI (login, register, protected routes)
- Dashboard with metric cards, charts (recharts), data tables
- Responsive design with Tailwind CSS
- Dark/light mode support
- Form validation and error states

**Backend (Node.js + Express + TypeScript)**
- REST API with JWT authentication
- User management endpoints (register, login, profile)
- Resource CRUD endpoints specific to the app domain
- Input validation with Zod
- Error handling middleware
- CORS configuration

**Database (PostgreSQL)**
- Full schema with users table + app-specific tables
- Proper indexes and foreign keys
- Row-level security policies
- Migration files

**Infrastructure**
- docker-compose.yml (frontend + backend + postgres)
- .github/workflows/deploy.yml (CI/CD)
- .env.example with all required variables
- README.md with setup instructions

## Instructions

1. **Parse the user's description** — extract: app name, core features, user roles, data entities, integrations needed (PayPal, email, etc.)

2. **Generate a build plan first** — list the pages, API endpoints, and database tables before writing any code. Show this plan to the user.

3. **Build in 6 passes**:
   - Pass 1: Config files (package.json, tsconfig, vite.config, docker-compose, CI/CD)
   - Pass 2: Types + constants + app shell (App.tsx, Router, Layout, Nav)
   - Pass 3: Auth flow (login, register, protected routes, JWT handling)
   - Pass 4: Core feature pages (dashboard, main CRUD views, forms)
   - Pass 5: Backend API (routes, middleware, services, DB queries)
   - Pass 6: Integration + README

4. **Code quality rules**:
   - TypeScript everywhere — no `any` types
   - MemoryRouter for Sandpack preview compatibility
   - All imports resolved — no missing dependencies
   - Real data, not Lorem ipsum
   - Mobile responsive

5. **After build**: Show quality score summary covering frontend, backend, database, tests, security

## Output Format

Each file in its own fenced code block with path:
```tsx:/src/components/Dashboard.tsx
// complete code
```

## Example Input → Output

Input: "Build a project management tool where teams can create projects, assign tasks, set deadlines, and track progress"

Output includes:
- `/src/pages/Dashboard.tsx` — project overview with stats
- `/src/pages/Projects.tsx` — project list + create modal
- `/src/pages/Tasks.tsx` — kanban board or list view
- `/server/routes/projects.ts` — CRUD API
- `/database/schema.sql` — projects, tasks, team_members, assignments tables
- `docker-compose.yml`, `README.md`, CI/CD config

