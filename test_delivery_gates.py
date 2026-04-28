"""
Delivery Gate + Visual QA Tests
Covers all 5 items from the research hard-fix list:
  1. Export/download gate (BIV marker check)
  2. Published-preview gate (/published/ BIV + dist/index.html)
  3. Proof hard-block (low proof score blocks completion)
  4. Visual QA / route crawling
  5. BIV retry marker persistence
"""
import json, os, sys, tempfile, shutil
from pathlib import Path

sys.path.insert(0, "/tmp/crucib_repo")

# ── Minimal stubs ─────────────────────────────────────────────────────────────
import types
for mod in ["fastapi", "fastapi.responses", "fastapi.middleware", "fastapi.middleware.cors"]:
    if mod not in sys.modules:
        m = types.ModuleType(mod)
        if mod == "fastapi":
            class _HTTPException(Exception):
                def __init__(self, status_code=500, detail=""):
                    self.status_code = status_code
                    self.detail = detail
            m.HTTPException = _HTTPException
        sys.modules[mod] = m

# Import modules under test
from backend.orchestration.delivery_gate import (
    write_biv_marker, write_proof_summary,
    check_biv_marker, check_proof_score, check_dist_index,
    run_download_gate, run_publish_gate,
    BIV_MARKER_PATH, PROOF_MARKER_PATH,
)
from backend.orchestration.visual_qa import run_visual_qa

PASS = FAIL = 0

def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  PASS  {label}")
        PASS += 1
    else:
        print(f"  FAIL  {label}" + (f"\n        ↳ {detail}" if detail else ""))
        FAIL += 1

def ws():
    return tempfile.mkdtemp()

def biv_pass(score=88):
    return {"passed": True, "score": score, "profile": "saas", "phase": "final",
            "recommendation": "ship", "issues": [], "retry_targets": []}

def biv_fail(score=45):
    return {"passed": False, "score": score, "profile": "saas", "phase": "final",
            "recommendation": "retry", "issues": ["App.jsx is garbage"], "retry_targets": ["frontend"]}


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── write_biv_marker + check_biv_marker ───────────────────────────────")
w = ws()
# No marker yet
r = check_biv_marker(w)
check("no marker → blocked (423)",           not r.passed and r.status == 423)

# Write passing marker
write_biv_marker(w, biv_pass())
check("marker written to disk",              Path(w, BIV_MARKER_PATH).exists())
r = check_biv_marker(w)
check("passing marker → gate passes",        r.passed)
check("gate status 200",                     r.status == 200)
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── check_biv_marker: failing marker ──────────────────────────────────")
w = ws()
write_biv_marker(w, biv_fail(45))
r = check_biv_marker(w)
check("failed BIV → gate blocked",           not r.passed)
check("status 422",                          r.status == 422)
check("detail mentions score",               "45" in r.detail or "score" in r.detail.lower())
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── check_biv_marker: score below min ─────────────────────────────────")
w = ws()
# passed=True but score=65 < default min 70
write_biv_marker(w, {**biv_pass(65), "passed": True})
r = check_biv_marker(w)
check("score 65 < min 70 → blocked",         not r.passed)
check("status 422",                          r.status == 422)
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── write_proof_summary + check_proof_score ───────────────────────────")
w = ws()
# No proof summary → passes (advisory)
r = check_proof_score(w)
check("no proof summary → passes",           r.passed)

# Write proof with high score
flat_strong = [{"proof_type": "runtime", "payload": {"verification_class": "execution"}} for _ in range(8)]
flat_weak   = [{"proof_type": "structure", "payload": {"verification_class": "presence"}} for _ in range(2)]
proof = {"flat": flat_strong + flat_weak}
write_proof_summary(w, proof)
r = check_proof_score(w)
check("strong proof → passes",               r.passed, f"score={r.meta.get('proof_score')}")
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── check_proof_score: low score blocked ──────────────────────────────")
w = ws()
flat_weak = [{"proof_type": "structure", "payload": {"verification_class": "presence"}} for _ in range(10)]
proof = {"flat": flat_weak}
write_proof_summary(w, proof)
# Force proof_score = 0.0 by writing summary directly
meta = Path(w) / ".crucibai"
meta.mkdir(parents=True, exist_ok=True)
(meta / "proof_summary.json").write_text(
    json.dumps({"proof_score": 0.10, "total_items": 10, "strong_items": 1})
)
r = check_proof_score(w)
check("proof_score=0.10 < 0.40 → blocked",   not r.passed)
check("status 422",                          r.status == 422)
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── check_dist_index ──────────────────────────────────────────────────")
w = ws()
r = check_dist_index(w)
check("no dist/index.html → 404",            not r.passed and r.status == 404)

Path(w, "dist").mkdir()
Path(w, "dist", "index.html").write_text("<html></html>")
r = check_dist_index(w)
check("dist/index.html exists → passes",     r.passed)
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── run_download_gate composite ───────────────────────────────────────")
w = ws()
# Neither BIV nor proof
r = run_download_gate(w)
check("no markers → download blocked",       not r.passed)

# Pass BIV only
write_biv_marker(w, biv_pass(90))
r = run_download_gate(w)
check("BIV pass, no proof summary → allowed (proof optional)", r.passed)

# Pass BIV + failing proof
meta = Path(w, ".crucibai"); meta.mkdir(parents=True, exist_ok=True)
(meta / "proof_summary.json").write_text(json.dumps({"proof_score": 0.05}))
r = run_download_gate(w)
check("BIV pass, low proof → download blocked",  not r.passed)

# draft=True skips proof gate
r = run_download_gate(w, draft=True)
check("draft=True skips proof gate",         r.passed)
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── run_publish_gate composite ────────────────────────────────────────")
w = ws()
# No markers
r = run_publish_gate(w)
check("no markers → publish blocked",        not r.passed)

# BIV pass + no dist
write_biv_marker(w, biv_pass(90))
r = run_publish_gate(w)
check("BIV pass, no dist → publish blocked", not r.passed and r.status == 404)

# BIV pass + dist/index.html
Path(w, "dist").mkdir()
Path(w, "dist", "index.html").write_text("<html></html>")
r = run_publish_gate(w)
check("BIV pass + dist → publish allowed",   r.passed)
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── BIV retry: marker updated after retry ─────────────────────────────")
w = ws()
write_biv_marker(w, biv_fail(45))
marker_before = json.loads(Path(w, BIV_MARKER_PATH).read_text())
check("initial marker: passed=False",        not marker_before["passed"])

# Simulate retry improving the score
write_biv_marker(w, biv_pass(82))
marker_after = json.loads(Path(w, BIV_MARKER_PATH).read_text())
check("marker updated to passed=True after retry",  marker_after["passed"])
check("marker score updated to 82",          marker_after["score"] == 82)
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── visual_qa: empty workspace ────────────────────────────────────────")
w = ws()
result = run_visual_qa(w)
check("empty workspace → failed",            not result.passed)
check("score=0",                             result.score == 0)
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── visual_qa: valid SaaS workspace ───────────────────────────────────")
w = ws()
src_dir = Path(w, "src"); src_dir.mkdir()
pages_dir = Path(w, "src", "pages"); pages_dir.mkdir()
components_dir = Path(w, "src", "components"); components_dir.mkdir()

(src_dir / "App.jsx").write_text("""
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage.jsx';
import SettingsPage from './pages/SettingsPage.jsx';
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/settings" element={<SettingsPage />} />
    </Routes>
  );
}
""")
(src_dir / "main.jsx").write_text("""
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
""")
(pages_dir / "DashboardPage.jsx").write_text("""
import React from 'react';
export default function DashboardPage() {
  return <main><h1>Dashboard</h1><p>Your metrics here.</p></main>;
}
""")
(pages_dir / "SettingsPage.jsx").write_text("""
import React from 'react';
export default function SettingsPage() {
  return <main><h2>Settings</h2></main>;
}
""")
# Built dist
dist = Path(w, "dist"); dist.mkdir()
(dist / "index.html").write_text("""<!DOCTYPE html>
<html><head><title>My App</title></head>
<body><div id="root"></div><script src="/assets/main.js"></script></body>
</html>""")

result = run_visual_qa(w, goal="saas dashboard with analytics")
check("valid workspace → passed",            result.passed, f"score={result.score} issues={result.issues}")
check("score >= 60",                         result.score >= 60)
check("routes detected",                     len(result.routes) > 0)
check("reachable files > 0",                 result.reachable_count > 0)
check("html_issues empty (valid dist)",      len(result.html_issues) == 0, str(result.html_issues))
check("vqa marker written",                  Path(w, ".crucibai", "visual_qa.json").exists())
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── visual_qa: orphan detection ────────────────────────────────────────")
w = ws()
src_dir = Path(w, "src"); src_dir.mkdir()
components_dir = Path(w, "src", "components"); components_dir.mkdir()
(src_dir / "App.jsx").write_text("""
import React from 'react';
import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage.jsx';
export default function App() {
  return <Routes><Route path='/' element={<HomePage />} /></Routes>;
}
""")
pages_dir = Path(w, "src", "pages"); pages_dir.mkdir()
(pages_dir / "HomePage.jsx").write_text("<main><h1>Home</h1></main>")
# Orphan — not imported anywhere
(components_dir / "UnusedWidget.jsx").write_text("export default function UnusedWidget() { return null; }")

result = run_visual_qa(w)
check("orphan detected",                     len(result.orphans) > 0, str(result.orphans))
check("UnusedWidget in orphans",             any("UnusedWidget" in o for o in result.orphans))
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print("\n── visual_qa: bad dist HTML flagged ──────────────────────────────────")
w = ws()
src_dir = Path(w, "src"); src_dir.mkdir()
(src_dir / "App.jsx").write_text("import React from 'react'; export default function App(){ return <div>ok</div>; }")
dist = Path(w, "dist"); dist.mkdir()
# Bad HTML: no title, no root, no script
(dist / "index.html").write_text("<html><body><p>broken</p></body></html>")
result = run_visual_qa(w)
check("bad dist HTML flagged in html_issues", len(result.html_issues) > 0, str(result.html_issues))
shutil.rmtree(w)


# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'═'*60}")
print(f"  Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
if FAIL:
    print("  STATUS: FAIL")
    sys.exit(1)
else:
    print("  STATUS: ALL PASS ✓")
