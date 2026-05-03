# ============================================================
# CrucibAI Makefile
# ============================================================
# Usage:
#   make deploy          — connect services + deploy to Railway
#   make push            — git push to main (triggers auto-deploy)
#   make push-deploy     — git push + run deploy script
#   make status          — check Railway deployment status
#   make vars            — show required env vars checklist
#   make dev             — start local dev (backend + frontend)
#   make build           — build frontend
#   make test            — run backend syntax check

.PHONY: deploy push push-deploy status vars dev build test help

# ── Deploy ────────────────────────────────────────────────────
deploy:
	@bash scripts/deploy.sh

# ── Git push (Railway auto-deploys on push to main) ──────────
push:
	@echo "Pushing to main..."
	@git add -A
	@git status --short
	@read -p "Commit message: " msg; \
	git commit -m "$$msg" 2>/dev/null || echo "Nothing new to commit"; \
	git push origin main
	@echo "✓ Pushed — Railway is deploying"
	@echo "  Watch at: https://railway.app/project/63be0bed-3be9-482e-849e-e2ec8b974543"

# ── Push then wire services ───────────────────────────────────
push-deploy:
	@$(MAKE) push
	@echo ""
	@$(MAKE) deploy

# ── Status check ─────────────────────────────────────────────
status:
	@python3 -c "
import urllib.request, json, os, sys
token = os.environ.get('RAILWAY_TOKEN','')
if not token:
    print('Set RAILWAY_TOKEN first')
    sys.exit(1)
data = json.dumps({'query': '''
  query { project(id: \"63be0bed-3be9-482e-849e-e2ec8b974543\") {
    name
    services { edges { node { id name
      serviceInstances { edges { node { latestDeployment {
        status createdAt
      }}}}
    }}}
  }}
'''}).encode()
req = urllib.request.Request(
    'https://backboard.railway.app/graphql/v2',
    data=data,
    headers={'Content-Type':'application/json','Authorization':f'Bearer {token}'}
)
with urllib.request.urlopen(req) as r:
    result = json.loads(r.read())
project = result['data']['project']
print(f'Project: {project[\"name\"]}')
for s in project['services']['edges']:
    svc = s['node']
    instances = svc['serviceInstances']['edges']
    status = 'unknown'
    if instances:
        deploy = instances[0]['node'].get('latestDeployment')
        if deploy:
            status = deploy.get('status','unknown')
    print(f'  {svc[\"name\"]}: {status}')
"

# ── Required vars checklist ───────────────────────────────────
vars:
	@echo ""
	@echo "CrucibAI Required Environment Variables"
	@echo "========================================"
	@echo ""
	@echo "CRITICAL (service won't start without these):"
	@echo "  DATABASE_URL           Auto-set by deploy script"
	@echo "  REDIS_URL              Auto-set by deploy script"
	@echo "  JWT_SECRET             openssl rand -base64 32"
	@echo "  ANTHROPIC_API_KEY      console.anthropic.com"
	@echo "  FRONTEND_URL           https://crucibai-production.up.railway.app"
	@echo ""
	@echo "AUTH:"
	@echo "  GOOGLE_CLIENT_ID       console.cloud.google.com"
	@echo "  GOOGLE_CLIENT_SECRET   console.cloud.google.com"
	@echo "  GOOGLE_REDIRECT_URI    https://crucibai-production.up.railway.app/api/auth/google/callback"
	@echo ""
	@echo "AI MODELS (add all 5 for full rotation):"
	@echo "  CEREBRAS_API_KEY_1     inference.cerebras.ai"
	@echo "  CEREBRAS_API_KEY_2     inference.cerebras.ai"
	@echo "  CEREBRAS_API_KEY_3     inference.cerebras.ai"
	@echo "  CEREBRAS_API_KEY_4     inference.cerebras.ai"
	@echo "  CEREBRAS_API_KEY_5     inference.cerebras.ai"
	@echo "  TAVILY_API_KEY         app.tavily.com"
	@echo "  OPENAI_API_KEY         platform.openai.com (for Whisper voice)"
	@echo ""
	@echo "PAYMENTS:"
	@echo "  PAYPAL_CLIENT_ID       developer.paypal.com"
	@echo "  PAYPAL_CLIENT_SECRET   developer.paypal.com"
	@echo "  PAYPAL_MODE            sandbox or live"
	@echo ""
	@echo "EMAIL:"
	@echo "  SMTP_HOST              e.g. smtp.gmail.com"
	@echo "  SMTP_PORT              587"
	@echo "  SMTP_USER              your@email.com"
	@echo "  SMTP_PASS              app password"
	@echo "  FROM_EMAIL             noreply@crucibai.com"
	@echo ""
	@echo "MONITORING:"
	@echo "  SENTRY_DSN             sentry.io"
	@echo "  ENCRYPTION_KEY         openssl rand -base64 32"

# ── Local dev ─────────────────────────────────────────────────
dev:
	@echo "Starting CrucibAI locally..."
	@echo ""
	@echo "Backend (port 8080):"
	@echo "  cd backend && uvicorn server:app --reload --port 8080"
	@echo ""
	@echo "Frontend (port 3000):"
	@echo "  cd frontend && npm start"
	@echo ""
	@echo "Or run in separate terminals:"
	@echo "  Terminal 1: make dev-backend"
	@echo "  Terminal 2: make dev-frontend"

dev-backend:
	@cd backend && uvicorn server:app --reload --port 8080

dev-frontend:
	@cd frontend && REACT_APP_API_URL=http://localhost:8080 npm start

# ── Build ─────────────────────────────────────────────────────
build:
	@echo "Building frontend..."
	@cd frontend && npm run build
	@echo "✓ Build complete"

# ── Test ─────────────────────────────────────────────────────
test:
	@echo "Checking backend syntax..."
	@python3 -m py_compile backend/server.py && echo "✓ server.py OK"
	@python3 -m py_compile backend/agent_dag.py && echo "✓ agent_dag.py OK"
	@python3 -m py_compile backend/iterative_builder.py && echo "✓ iterative_builder.py OK"
	@python3 -m py_compile backend/integrations/queue.py && echo "✓ queue.py OK"
	@python3 -m py_compile backend/automation_engine.py && echo "✓ automation_engine.py OK"
	@cd frontend && npm run build 2>&1 | grep -E "Compiled|error" | head -3

# ── Help ─────────────────────────────────────────────────────
help:
	@echo ""
	@echo "CrucibAI Make Commands"
	@echo "======================"
	@echo "  make deploy       Connect Redis+Postgres+CrucibAI, redeploy"
	@echo "  make push         Git push to main (auto-deploy)"
	@echo "  make push-deploy  Push + connect services"
	@echo "  make status       Check Railway deployment status"
	@echo "  make vars         Show required env vars"
	@echo "  make dev          Local dev instructions"
	@echo "  make build        Build frontend"
	@echo "  make test         Syntax check all backend files"
	@echo ""
