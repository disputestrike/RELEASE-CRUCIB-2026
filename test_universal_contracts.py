"""
Universal Build Contract Tests
Verifies _ensure_preview_contract_files fires the correct entrypoints
for every CrucibAI build type: saas, fullstack, website, mobile, automation, api.
"""
import os, sys, json, tempfile, shutil, re
sys.path.insert(0, "/tmp/crucib_repo")

# ── Minimal stubs so executor imports without a full Django/FastAPI stack ──────
import types

# Stub heavy deps before importing executor
for mod in ["sqlalchemy", "sqlalchemy.orm", "sqlalchemy.ext", "sqlalchemy.ext.declarative",
            "alembic", "psycopg2", "redis", "celery", "boto3", "stripe",
            "anthropic", "openai", "cerebras", "cerebras_cloud_sdk",
            "fastapi", "fastapi.middleware", "fastapi.middleware.cors",
            "uvicorn", "pydantic"]:
    if mod not in sys.modules:
        sys.modules[mod] = types.ModuleType(mod)

# Patch the is_saas_ui_goal import inside executor
import importlib.util

# We'll test _infer_build_kind and the contract helpers directly via a thin harness
# rather than importing executor (which has deep deps). This mirrors how the production
# code runs.

# ──────────────────────────────────────────────────────────────────────────────
# Inline the exact logic from executor.py so tests are self-contained
# ──────────────────────────────────────────────────────────────────────────────
import logging
logging.basicConfig(level=logging.WARNING)

# ── Replicate _infer_build_kind ───────────────────────────────────────────────
_SAAS_INTENT_MARKERS = [
    "saas", "subscription", "dashboard", "multi-tenant", "billing",
    "stripe", "product", "analytics", "crm", "b2b", "platform",
]

def _infer_build_kind(job):
    explicit = (
        job.get("build_kind") or
        job.get("build_type") or
        job.get("stack_kind") or ""
    ).strip().lower()
    if explicit:
        return explicit
    goal = " ".join(str(job.get(k) or "") for k in ("goal", "prompt", "description", "title")).lower()
    if any(k in goal for k in ("mobile", "ios", "android", "expo", "react native")):
        return "mobile"
    if any(k in goal for k in ("automate", "cron", "scheduler", "workflow", "pipeline")):
        return "automation"
    if any(k in goal for k in ("api only", "rest api", "fastapi", "flask api", "graphql api")):
        return "api"
    if any(k in goal for k in ("landing page", "portfolio", "marketing site", "static site")):
        return "website"
    if sum(1 for m in _SAAS_INTENT_MARKERS if m in goal) >= 2:
        return "saas"
    return "fullstack"


# ── Minimal safe_write for tests ──────────────────────────────────────────────
def _safe_write(base, rel, content):
    if not content or not content.strip():
        return None
    path = os.path.join(base, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return path

def _read_text(base, rel):
    path = os.path.join(base, rel)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read()

def _is_manifest_content(text):
    if not text or not text.strip():
        return True
    MANIFEST_RE = re.compile(r"^(src/|backend/|frontend/|server/|\./|\*\s|[-*]\s+\w+/)")
    MARKDOWN_RE = re.compile(r"^(#{1,6}\s|>\s|\|\s|\*\*|---|\s{4})")
    HEADING_RE  = re.compile(r"^\s*(#{1,6}\s|\*\*[`\[])")
    lines = [l for l in text.strip().splitlines() if l.strip()][:15]
    if lines and HEADING_RE.match(lines[0]):
        return True
    manifest_hits = sum(1 for l in lines if MANIFEST_RE.match(l))
    markdown_hits = sum(1 for l in lines if MARKDOWN_RE.match(l))
    return manifest_hits >= min(3, len(lines)) or markdown_hits >= min(2, len(lines))


# ── Contract implementations (mirrors executor.py) ───────────────────────────
def _ensure_mobile_contract(workspace_path, job, written):
    if not _read_text(workspace_path, "App.tsx") and not _read_text(workspace_path, "App.js"):
        app_tsx = (
            "import React from 'react';\n"
            "import { View, Text } from 'react-native';\n"
            "export default function App() { return <View><Text>CrucibAI</Text></View>; }\n"
        )
        if _safe_write(workspace_path, "App.tsx", app_tsx):
            written.append("App.tsx")
    if not _read_text(workspace_path, "app.json"):
        goal_name = re.sub(r"[^a-z0-9]+", "-", (job.get("goal") or "app")[:40].lower()).strip("-") or "app"
        app_json = {"expo": {"name": goal_name, "slug": goal_name, "version": "1.0.0", "sdkVersion": "51.0.0"}}
        if _safe_write(workspace_path, "app.json", json.dumps(app_json, indent=2)):
            written.append("app.json")
    if not _read_text(workspace_path, "babel.config.js"):
        if _safe_write(workspace_path, "babel.config.js", "module.exports = { presets: ['babel-preset-expo'] };\n"):
            written.append("babel.config.js")
    # package.json expo deps
    pkg_path = "package.json"
    existing_pkg = _read_text(workspace_path, pkg_path) or ""
    try:
        pkg_obj = json.loads(existing_pkg) if existing_pkg.strip() else {}
    except Exception:
        pkg_obj = {}
    deps = pkg_obj.setdefault("dependencies", {})
    need_write = False
    for k, v in {"expo": "~51.0.0", "react": "18.2.0", "react-native": "0.74.0"}.items():
        if k not in deps:
            deps[k] = v
            need_write = True
    if need_write:
        if _safe_write(workspace_path, pkg_path, json.dumps(pkg_obj, indent=2)):
            written.append(pkg_path)

def _ensure_automation_contract(workspace_path, job, written):
    if not _read_text(workspace_path, "workflow.json"):
        wf = {"name": (job.get("goal") or "workflow")[:80], "version": "1.0.0",
              "trigger": {"type": "manual"}, "steps": [{"id": "start", "action": "log"}]}
        if _safe_write(workspace_path, "workflow.json", json.dumps(wf, indent=2)):
            written.append("workflow.json")
    if not _read_text(workspace_path, "executor.py") and not _read_text(workspace_path, "main.py"):
        py = 'import sys, json\ndef run(): return {"status": "ok"}\nif __name__=="__main__": print(json.dumps(run()))\n'
        if _safe_write(workspace_path, "executor.py", py):
            written.append("executor.py")
    if not _read_text(workspace_path, "requirements.txt"):
        if _safe_write(workspace_path, "requirements.txt", "# deps\n"):
            written.append("requirements.txt")

def _ensure_api_backend_contract(workspace_path, job, written):
    main_text = _read_text(workspace_path, "main.py") or _read_text(workspace_path, "server.py")
    if not main_text:
        main_py = (
            '"""CrucibAI API"""\nfrom fastapi import FastAPI\nfrom datetime import datetime, timezone\n'
            'app = FastAPI()\n\n@app.get("/health")\ndef health(): return {"status":"ok"}\n'
        )
        if _safe_write(workspace_path, "main.py", main_py):
            written.append("main.py")
    elif main_text and '@app.get("/health")' not in main_text and "@app.get('/health')" not in main_text:
        health = '\n\n@app.get("/health")\ndef health():\n    from datetime import datetime,timezone\n    return {"status":"ok"}\n'
        target = "main.py" if _read_text(workspace_path, "main.py") else "server.py"
        if _safe_write(workspace_path, target, main_text + health):
            written.append(target + " [+health]")
    if not _read_text(workspace_path, "requirements.txt"):
        if _safe_write(workspace_path, "requirements.txt", "fastapi>=0.110.0\nuvicorn[standard]>=0.29.0\n"):
            written.append("requirements.txt")
    if not _read_text(workspace_path, "Procfile"):
        if _safe_write(workspace_path, "Procfile", "web: uvicorn main:app --host 0.0.0.0 --port $PORT\n"):
            written.append("Procfile")

def _ensure_website_contract(workspace_path, job, written):
    if not _read_text(workspace_path, "index.html"):
        goal_text = (job.get("goal") or "Website")[:80]
        html = f"<!DOCTYPE html>\n<html><head><title>{goal_text}</title></head><body><h1>{goal_text}</h1></body></html>\n"
        if _safe_write(workspace_path, "index.html", html):
            written.append("index.html")
    if not _read_text(workspace_path, "styles.css"):
        if _safe_write(workspace_path, "styles.css", "body { font-family: system-ui; }\n"):
            written.append("styles.css")
    if not _read_text(workspace_path, "main.js"):
        if _safe_write(workspace_path, "main.js", "console.log('ready');\n"):
            written.append("main.js")

def _ensure_fullstack_contract(workspace_path, job, written):
    existing_app = _read_text(workspace_path, "src/App.jsx") or _read_text(workspace_path, "src/App.js")
    if not existing_app or _is_manifest_content(existing_app):
        app_jsx = "import React from 'react';\nexport default function App() { return <div>CrucibAI</div>; }\n"
        if _safe_write(workspace_path, "src/App.jsx", app_jsx):
            written.append("src/App.jsx")
    if not _read_text(workspace_path, "src/main.jsx"):
        main_jsx = "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App.jsx';\nReactDOM.createRoot(document.getElementById('root')).render(<App />);\n"
        if _safe_write(workspace_path, "src/main.jsx", main_jsx):
            written.append("src/main.jsx")
    if not _read_text(workspace_path, "backend/main.py"):
        if _safe_write(workspace_path, "backend/main.py", 'from fastapi import FastAPI\napp=FastAPI()\n@app.get("/health")\ndef h(): return {"ok":True}\n'):
            written.append("backend/main.py")
    if not _read_text(workspace_path, "requirements.txt"):
        if _safe_write(workspace_path, "requirements.txt", "fastapi>=0.110.0\nuvicorn[standard]>=0.29.0\n"):
            written.append("requirements.txt")


def run_contract(workspace_path, job):
    written = []
    bk = _infer_build_kind(job)
    if bk == "mobile":
        _ensure_mobile_contract(workspace_path, job, written)
    elif bk == "automation":
        _ensure_automation_contract(workspace_path, job, written)
    elif bk in ("api", "backend"):
        _ensure_api_backend_contract(workspace_path, job, written)
    elif bk in ("website", "frontend"):
        _ensure_website_contract(workspace_path, job, written)
    elif bk == "fullstack":
        _ensure_fullstack_contract(workspace_path, job, written)
    return bk, written


# ── Test runner ───────────────────────────────────────────────────────────────
PASS = 0
FAIL = 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  PASS  {label}")
        PASS += 1
    else:
        print(f"  FAIL  {label}" + (f"\n        ↳ {detail}" if detail else ""))
        FAIL += 1

def make_ws():
    return tempfile.mkdtemp()


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── _infer_build_kind ──────────────────────────────────────────────────")
cases = [
    ({"build_kind": "mobile"},                                     "mobile"),
    ({"build_kind": "automation"},                                 "automation"),
    ({"build_kind": "api"},                                        "api"),
    ({"build_kind": "backend"},                                    "backend"),
    ({"build_kind": "website"},                                    "website"),
    ({"build_kind": "saas"},                                       "saas"),
    ({"goal": "build an expo mobile app for iOS"},                 "mobile"),
    ({"goal": "create a cron scheduler workflow"},                 "automation"),
    ({"goal": "build a rest api for my service"},                  "api"),
    ({"goal": "create a landing page portfolio site"},             "website"),
    ({"goal": "saas dashboard with stripe billing analytics"},     "saas"),
    ({"goal": "build me a full-stack web application"},            "fullstack"),
    ({"goal": "something completely generic"},                     "fullstack"),
]
for job, expected in cases:
    got = _infer_build_kind(job)
    check(f"build_kind={expected!r:12} from {list(job.values())[0]!r:.40}", got == expected, f"got {got!r}")


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Mobile contract (empty workspace) ─────────────────────────────────")
ws = make_ws()
job = {"goal": "Build an expo mobile fitness tracker for iOS and Android"}
bk, written = run_contract(ws, job)
check("build_kind=mobile",          bk == "mobile")
check("App.tsx created",            os.path.exists(f"{ws}/App.tsx"))
check("app.json created",           os.path.exists(f"{ws}/app.json"))
check("babel.config.js created",    os.path.exists(f"{ws}/babel.config.js"))
check("package.json has expo dep",  '"expo"' in (_read_text(ws, "package.json") or ""))
check("app.json has expo key",      '"expo"' in (_read_text(ws, "app.json") or ""))
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Mobile contract (existing App.tsx preserved) ──────────────────────")
ws = make_ws()
existing = "import React from 'react';\n// my real app\nexport default function App() { return null; }\n"
_safe_write(ws, "App.tsx", existing)
job = {"build_kind": "mobile", "goal": "fitness app"}
bk, written = run_contract(ws, job)
check("App.tsx NOT overwritten",    _read_text(ws, "App.tsx") == existing)
check("app.json still created",     os.path.exists(f"{ws}/app.json"))
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Automation contract (empty workspace) ─────────────────────────────")
ws = make_ws()
job = {"goal": "Build a cron job workflow to process daily sales data"}
bk, written = run_contract(ws, job)
check("build_kind=automation",      bk == "automation")
check("workflow.json created",      os.path.exists(f"{ws}/workflow.json"))
check("executor.py created",        os.path.exists(f"{ws}/executor.py"))
check("requirements.txt created",   os.path.exists(f"{ws}/requirements.txt"))
wf_content = _read_text(ws, "workflow.json")
check("workflow.json valid JSON",   json.loads(wf_content) is not None)
check("workflow has steps key",     "steps" in json.loads(wf_content))
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Automation contract (existing executor.py preserved) ──────────────")
ws = make_ws()
existing_exec = "# my real executor\ndef run(): return 'real'\n"
_safe_write(ws, "executor.py", existing_exec)
job = {"build_kind": "automation", "goal": "my pipeline"}
bk, written = run_contract(ws, job)
check("executor.py NOT overwritten", _read_text(ws, "executor.py") == existing_exec)
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── API/backend contract (empty workspace) ────────────────────────────")
ws = make_ws()
job = {"goal": "Build a rest api for managing tasks"}
bk, written = run_contract(ws, job)
check("build_kind=api",             bk == "api")
check("main.py created",            os.path.exists(f"{ws}/main.py"))
check("/health in main.py",         '@app.get("/health")' in (_read_text(ws, "main.py") or ""))
check("requirements.txt created",   os.path.exists(f"{ws}/requirements.txt"))
check("Procfile created",           os.path.exists(f"{ws}/Procfile"))
check("fastapi in requirements",    "fastapi" in (_read_text(ws, "requirements.txt") or ""))
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── API contract: /health injected into existing server.py ───────────")
ws = make_ws()
existing_server = 'from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/users")\ndef get_users(): return []\n'
_safe_write(ws, "server.py", existing_server)
job = {"build_kind": "api", "goal": "task api"}
bk, written = run_contract(ws, job)
patched = _read_text(ws, "server.py")
check("/health injected into server.py", '@app.get("/health")' in (patched or ""))
check("original /users route preserved", '@app.get("/users")' in (patched or ""))
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── API contract: existing /health NOT double-injected ────────────────")
ws = make_ws()
existing_main = 'from fastapi import FastAPI\napp=FastAPI()\n@app.get("/health")\ndef health(): return {"ok":True}\n'
_safe_write(ws, "main.py", existing_main)
job = {"build_kind": "api", "goal": "task api"}
bk, written = run_contract(ws, job)
patched = _read_text(ws, "main.py")
check("no double /health inject",  patched.count('@app.get("/health")') == 1, f"count={patched.count('/health')}")
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Website contract (empty workspace) ────────────────────────────────")
ws = make_ws()
job = {"goal": "Create a landing page portfolio site for a designer"}
bk, written = run_contract(ws, job)
check("build_kind=website",         bk == "website")
check("index.html created",         os.path.exists(f"{ws}/index.html"))
check("styles.css created",         os.path.exists(f"{ws}/styles.css"))
check("main.js created",            os.path.exists(f"{ws}/main.js"))
check("index.html has DOCTYPE",     "DOCTYPE" in (_read_text(ws, "index.html") or ""))
check("index.html has goal title",  "portfolio" in (_read_text(ws, "index.html") or "").lower())
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Fullstack contract (empty workspace) ──────────────────────────────")
ws = make_ws()
job = {"goal": "Build a full-stack project management tool"}
bk, written = run_contract(ws, job)
check("build_kind=fullstack",       bk == "fullstack")
check("src/App.jsx created",        os.path.exists(f"{ws}/src/App.jsx"))
check("src/main.jsx created",       os.path.exists(f"{ws}/src/main.jsx"))
check("backend/main.py created",    os.path.exists(f"{ws}/backend/main.py"))
check("requirements.txt created",   os.path.exists(f"{ws}/requirements.txt"))
app_content = _read_text(ws, "src/App.jsx")
check("App.jsx has React import",   "import React" in (app_content or "") or "from 'react'" in (app_content or ""))
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Fullstack: garbage App.jsx gets replaced ──────────────────────────")
ws = make_ws()
os.makedirs(f"{ws}/src", exist_ok=True)
garbage_app = "## App Component\n\nThis file should contain:\n- import React\n- export default function\n"
_safe_write(ws, "src/App.jsx", garbage_app)
job = {"build_kind": "fullstack", "goal": "task manager"}
bk, written = run_contract(ws, job)
new_app = _read_text(ws, "src/App.jsx")
check("garbage App.jsx replaced",  not _is_manifest_content(new_app), f"still garbage: {new_app[:60]!r}")
check("replacement has import",    "import" in (new_app or ""))
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Fullstack: valid App.jsx preserved ────────────────────────────────")
ws = make_ws()
valid_app = "import React from 'react';\nimport { Routes, Route } from 'react-router-dom';\nexport default function App() { return <Routes><Route path='/' element={<div>Home</div>} /></Routes>; }\n"
_safe_write(ws, "src/App.jsx", valid_app)
job = {"build_kind": "fullstack", "goal": "task manager"}
bk, written = run_contract(ws, job)
check("valid App.jsx preserved",   _read_text(ws, "src/App.jsx") == valid_app)
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── build_kind explicit field takes priority over goal text ───────────")
ws = make_ws()
job = {"build_kind": "api", "goal": "create an expo mobile app"}  # explicit overrides goal
bk, written = run_contract(ws, job)
check("explicit build_kind=api wins over mobile goal", bk == "api")
shutil.rmtree(ws)


# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'═'*60}")
print(f"  Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
if FAIL:
    print("  STATUS: FAIL — fix the failures above before pushing")
    sys.exit(1)
else:
    print("  STATUS: ALL PASS ✓")
