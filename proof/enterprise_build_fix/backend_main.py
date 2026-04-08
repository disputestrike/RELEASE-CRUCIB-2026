from datetime import datetime, timedelta, timezone
import hashlib
import os
from typing import Dict

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext

APP_NAME = "Helios Aegis Command"
COMPANY_NAME = "Helios Aegis"
DEMO_ORG_ID = "helios-aegis-command-org"
JWT_SECRET = os.getenv("JWT_SECRET", "development-only-change-me")
JWT_ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

app = FastAPI(title=APP_NAME, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

LEADS = [
    {"id": "LD-104", "org_id": DEMO_ORG_ID, "name": "Riverton Logistics", "score": 92, "status": "qualified", "owner": "Alex Chen"},
    {"id": "LD-118", "org_id": DEMO_ORG_ID, "name": "Summit Storage Group", "score": 84, "status": "proposal", "owner": "Jordan Lee"},
]
ACCOUNTS = [
    {"id": "AC-201", "org_id": DEMO_ORG_ID, "name": "Riverton Logistics", "segment": "Industrial", "region": "CA", "contracts": 3},
    {"id": "AC-214", "org_id": DEMO_ORG_ID, "name": "Northwind Senior Living", "segment": "Healthcare", "region": "AZ", "contracts": 2},
]
QUOTES = [
    {"id": "Q-1042", "org_id": DEMO_ORG_ID, "account": "Riverton Logistics", "status": "pending_review", "total": 184500, "expires_on": "2026-04-30", "approver": "Morgan Rivera", "ai_recommendation": "Reduce battery reserve by 3% after human review."},
    {"id": "Q-1047", "org_id": DEMO_ORG_ID, "account": "Northwind Senior Living", "status": "draft", "total": 94300, "expires_on": "2026-05-12", "approver": "Pending assignment", "ai_recommendation": "Block conversion until region eligibility is cleared."},
]
PROJECTS = [
    {"id": "PR-12", "org_id": DEMO_ORG_ID, "name": "Riverton West Campus", "status": "installation_ready", "timeline": "Apr 22 - Jun 14", "account": "Riverton Logistics"},
    {"id": "PR-18", "org_id": DEMO_ORG_ID, "name": "Northwind Expansion", "status": "planning", "timeline": "May 03 - Jul 18", "account": "Northwind Senior Living"},
]
TASKS = [
    {"id": "TS-301", "org_id": DEMO_ORG_ID, "title": "Review incentive region mismatch", "status": "open", "priority": "high", "owner": "Morgan Rivera", "source": "rule:region_eligibility"},
    {"id": "TS-309", "org_id": DEMO_ORG_ID, "title": "Approve quote Q-1042", "status": "open", "priority": "high", "owner": "Morgan Rivera", "source": "workflow:quote_review"},
]
POLICY_RECOMMENDATIONS = [
    {"id": "POL-01", "org_id": DEMO_ORG_ID, "title": "Escalate repeated webhook failures", "status": "PENDING", "recommended_action": "Require org_admin approval before re-enabling vendor webhook.", "trigger": "3 failed sync runs in 20 minutes"},
    {"id": "POL-02", "org_id": DEMO_ORG_ID, "title": "Geo-risk review on storage site", "status": "APPROVED", "recommended_action": "Limit remote dispatch until site inspection completes.", "trigger": "Repeated suspicious telemetry variance"},
]
AUDIT_EVENTS = [
    {"id": "AUD-001", "org_id": DEMO_ORG_ID, "action": "quote.pending_review", "actor": "alex.chen@heliosaegis.test", "prev_hash": "GENESIS", "current_hash": "4bd4bf1902c7c201", "entity": "Q-1042"},
    {"id": "AUD-002", "org_id": DEMO_ORG_ID, "action": "policy.recommendation_created", "actor": "system", "prev_hash": "4bd4bf1902c7c201", "current_hash": "e1529145233cf892", "entity": "POL-01"},
]
ANALYTICS = {
    "quote_conversion": {"approved": 14, "rejected": 2, "pending": 6},
    "operator_load": {"open_tasks": 17, "sla_watch": 3, "retrying_jobs": 1},
    "policy_disposition": {"pending": 1, "approved": 1, "rejected": 0, "enforced": 0},
    "ai_disposition": {"accepted": 12, "rejected": 4, "needs_human_review": 7},
}


def _scoped(rows, org_id: str):
    return [row for row in rows if row.get("org_id") == org_id]


def _find(rows, item_id: str):
    for row in rows:
      if row.get("id") == item_id:
        return row
    return None


def create_access_token(subject: str, org_id: str, token_type: str = "access") -> str:
    payload = {
        "sub": subject,
        "org_id": org_id,
        "type": token_type,
        "exp": (datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_org_id(x_org_id: str = Header(default=DEMO_ORG_ID, alias="X-Org-Id")) -> str:
    return x_org_id


def current_role(x_actor_role: str = Header(default="org_admin", alias="X-Actor-Role")) -> str:
    return x_actor_role


def require_review_role(role: str = Depends(current_role)) -> str:
    if role not in {"org_admin", "security_analyst", "global_admin"}:
        raise HTTPException(status_code=403, detail="Explicit human approval role required")
    return role


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME, "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/api/auth/login")
def login():
    return {
        "access_token": create_access_token("morgan-rivera", DEMO_ORG_ID),
        "refresh_token": create_access_token("morgan-rivera", DEMO_ORG_ID, token_type="refresh"),
        "token_type": "bearer",
    }


@app.post("/api/auth/refresh")
def refresh():
    return {
        "access_token": create_access_token("morgan-rivera", DEMO_ORG_ID),
        "refresh_token": create_access_token("morgan-rivera", DEMO_ORG_ID, token_type="refresh"),
        "token_type": "bearer",
    }


@app.get("/api/auth/me")
def me(org_id: str = Depends(current_org_id)):
    return {"id": "morgan-rivera", "email": "morgan@heliosaegis.test", "org_id": org_id, "roles": ["org_admin"]}


@app.get("/api/crm/leads")
def list_leads(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "leads": _scoped(LEADS, org_id)}


@app.get("/api/crm/accounts")
def list_accounts(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "accounts": _scoped(ACCOUNTS, org_id)}


@app.get("/api/quotes")
def list_quotes(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "quotes": _scoped(QUOTES, org_id)}


@app.post("/api/quotes/{quote_id}/recommendation")
def quote_recommendation(quote_id: str, org_id: str = Depends(current_org_id)):
    quote = _find(QUOTES, quote_id)
    if not quote or quote.get("org_id") != org_id:
        raise HTTPException(status_code=404, detail="Quote not found")
    return {"quote_id": quote_id, "mode": "recommendation_only", "suggestion": quote.get("ai_recommendation")}


@app.post("/api/quotes/{quote_id}/approve")
def approve_quote(quote_id: str, decision: Dict[str, str], org_id: str = Depends(current_org_id), _role: str = Depends(require_review_role)):
    quote = _find(QUOTES, quote_id)
    if not quote or quote.get("org_id") != org_id:
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote["status"] not in {"draft", "pending_review"}:
        raise HTTPException(status_code=409, detail="Quote can only be changed from draft or pending_review")
    status_value = str(decision.get("decision") or "").lower().strip()
    if status_value not in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail="decision must be approved or rejected")
    quote["status"] = status_value
    return {"quote_id": quote_id, "status": quote["status"], "approved_by_human": True}


@app.get("/api/projects")
def list_projects(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "projects": _scoped(PROJECTS, org_id)}


@app.get("/api/tasks")
def list_tasks(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "tasks": _scoped(TASKS, org_id)}


@app.get("/api/policies/recommendations")
def list_recommendations(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "recommendations": _scoped(POLICY_RECOMMENDATIONS, org_id)}


@app.post("/api/policies/{policy_id}/approve")
def approve_policy(policy_id: str, decision: Dict[str, str], org_id: str = Depends(current_org_id), _role: str = Depends(require_review_role)):
    policy = _find(POLICY_RECOMMENDATIONS, policy_id)
    if not policy or policy.get("org_id") != org_id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if policy["status"] != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending recommendations can be decided")
    value = str(decision.get("decision") or "").upper().strip()
    if value not in {"APPROVED", "REJECTED"}:
        raise HTTPException(status_code=400, detail="decision must be APPROVED or REJECTED")
    policy["status"] = value
    return {"policy_id": policy_id, "status": policy["status"], "decision_by_human": True}


@app.post("/api/policies/{policy_id}/enforce")
def enforce_policy(policy_id: str, org_id: str = Depends(current_org_id), _role: str = Depends(require_review_role)):
    policy = _find(POLICY_RECOMMENDATIONS, policy_id)
    if not policy or policy.get("org_id") != org_id:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if policy["status"] != "APPROVED":
        raise HTTPException(status_code=409, detail="Policy cannot be enforced before explicit approval")
    policy["status"] = "ENFORCED"
    return {"policy_id": policy_id, "status": policy["status"], "enforced": True}


@app.get("/api/audit/events")
def audit_events(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "events": _scoped(AUDIT_EVENTS, org_id)}


@app.get("/api/audit/chain/verify")
def audit_chain_verify(org_id: str = Depends(current_org_id)):
    events = _scoped(AUDIT_EVENTS, org_id)
    if not events:
        return {"org_id": org_id, "chain_valid": True, "total_logs": 0}
    first_ok = events[0]["prev_hash"] == "GENESIS"
    chain_ok = first_ok and all(events[index]["prev_hash"] == events[index - 1]["current_hash"] for index in range(1, len(events)))
    digest = hashlib.sha256(("".join(item["current_hash"] for item in events)).encode()).hexdigest()
    return {"org_id": org_id, "chain_valid": chain_ok, "total_logs": len(events), "digest": digest}


@app.get("/api/analytics/overview")
def analytics_overview(org_id: str = Depends(current_org_id)):
    return {"org_id": org_id, "analytics": ANALYTICS}

# CRUCIBAI_SECURITY_HEADERS - generated deploy hardening hook.
from fastapi import HTTPException, Request


@app.middleware("http")
async def crucibai_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-XSS-Protection"] = "0"
    return response
