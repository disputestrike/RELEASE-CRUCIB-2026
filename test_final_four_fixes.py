"""
Final Four Fixes — Test Suite
Covers all 4 remaining research hard-fixes:
  1. Artifact reconciliation hard block
  2. Live proof separation enforcement
  3. Visual QA blocking (not advisory)
  4. Browser QA (headless route validation)
"""
import json, os, sys, shutil, tempfile, hashlib, re
from pathlib import Path

sys.path.insert(0, "/tmp/crucib_repo")

import types
for mod in ["fastapi","fastapi.responses","fastapi.middleware","fastapi.middleware.cors"]:
    if mod not in sys.modules:
        m = types.ModuleType(mod)
        if mod == "fastapi":
            class _E(Exception):
                def __init__(self,status_code=500,detail=""): self.status_code=status_code;self.detail=detail
            m.HTTPException = _E
        sys.modules[mod] = m

from backend.orchestration.delivery_gate import (
    write_biv_marker, write_proof_summary,
    check_artifact_reconciliation, check_live_proof_separation,
    check_visual_qa, check_browser_qa,
    run_download_gate, run_publish_gate,
)
from backend.orchestration.visual_qa import run_visual_qa
from backend.orchestration.browser_qa import (
    run_browser_qa, _check_html_contracts, _ContractParser,
)

PASS = FAIL = 0
def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  PASS  {label}"); PASS += 1
    else:
        print(f"  FAIL  {label}" + (f"\n        ↳ {detail}" if detail else "")); FAIL += 1

def ws(): return tempfile.mkdtemp()

def sha256(b): return hashlib.sha256(b).hexdigest()

def write_biv_pass(w, score=88):
    write_biv_marker(w, {"passed":True,"score":score,"profile":"saas","phase":"final",
                         "recommendation":"ship","issues":[],"retry_targets":[]})

def write_good_proof(w):
    write_proof_summary(w, {"flat":[
        {"proof_type":"runtime","payload":{"verification_class":"execution"}} for _ in range(15)
    ]})

# ════════════════════════════════════════════════════════════════════════════
print("\n── FIX 1: Artifact Reconciliation ────────────────────────────────────")

# 1a: No seal → allowed (seal not required by default)
w = ws()
r = check_artifact_reconciliation(w)
check("no seal.json → allowed (not required by default)", r.passed)
shutil.rmtree(w)

# 1b: Seal present, no files mutated → passes
w = ws()
Path(w, "src").mkdir()
content = b"import React from 'react';\nexport default function App(){return <div/>}\n"
Path(w, "src", "App.jsx").write_bytes(content)
meta = Path(w, ".crucibai"); meta.mkdir()
manifest = {
    "files": [
        {"path": "src/App.jsx", "sha256": sha256(content), "bytes": len(content)}
    ]
}
seal = {"manifest_sha256": sha256(json.dumps(manifest["files"], sort_keys=True).encode())}
(meta / "seal.json").write_text(json.dumps(seal))
(meta / "artifact_manifest.json").write_text(json.dumps(manifest))
r = check_artifact_reconciliation(w)
check("intact files → reconciliation passes", r.passed, r.detail)
shutil.rmtree(w)

# 1c: File mutated after seal → 409
w = ws()
Path(w, "src").mkdir()
original = b"import React from 'react';\nexport default function App(){return <div/>}\n"
Path(w, "src", "App.jsx").write_bytes(original)
meta = Path(w, ".crucibai"); meta.mkdir()
manifest = {"files": [{"path": "src/App.jsx", "sha256": sha256(original), "bytes": len(original)}]}
seal = {"manifest_sha256": sha256(json.dumps(manifest["files"], sort_keys=True).encode())}
(meta / "seal.json").write_text(json.dumps(seal))
(meta / "artifact_manifest.json").write_text(json.dumps(manifest))
# Mutate the file after sealing
Path(w, "src", "App.jsx").write_bytes(b"// TAMPERED\n" + original)
r = check_artifact_reconciliation(w)
check("mutated file → 409 blocked", not r.passed and r.status == 409)
check("detail mentions changed file",  "src/App.jsx" in r.detail or "changed" in r.detail.lower())
shutil.rmtree(w)

# 1d: File missing from disk after seal → 409
w = ws()
meta = Path(w, ".crucibai"); meta.mkdir()
manifest = {"files": [{"path": "src/App.jsx", "sha256": "abc123", "bytes": 100}]}
seal = {"manifest_sha256": sha256(json.dumps(manifest["files"], sort_keys=True).encode())}
(meta / "seal.json").write_text(json.dumps(seal))
(meta / "artifact_manifest.json").write_text(json.dumps(manifest))
r = check_artifact_reconciliation(w)
check("missing file → 409 blocked", not r.passed and r.status == 409)
shutil.rmtree(w)

# 1e: Seal has no manifest_sha256 (legacy) → passes
w = ws()
meta = Path(w, ".crucibai"); meta.mkdir()
(meta / "seal.json").write_text(json.dumps({"job_id": "test"}))
r = check_artifact_reconciliation(w)
check("legacy seal (no manifest_sha256) → passes", r.passed)
shutil.rmtree(w)

# 1f: Full download gate with reconciliation
w = ws()
write_biv_pass(w)
write_good_proof(w)
content = b"import React from 'react'; export default function App(){ return <div/>; }\n"
Path(w, "src").mkdir()
Path(w, "src", "App.jsx").write_bytes(content)
meta = Path(w, ".crucibai"); meta.mkdir(exist_ok=True)
manifest = {"files":[{"path":"src/App.jsx","sha256":sha256(content),"bytes":len(content)}]}
seal = {"manifest_sha256": sha256(json.dumps(manifest["files"],sort_keys=True).encode())}
(Path(w,".crucibai","seal.json")).write_text(json.dumps(seal))
(Path(w,".crucibai","artifact_manifest.json")).write_text(json.dumps(manifest))
# VQA marker (pass) so gate doesn't block on VQA
(Path(w,".crucibai","visual_qa.json")).write_text(json.dumps({"passed":True,"score":80,"orphans":[],"issues":[]}))
r = run_download_gate(w)
check("download gate: intact seal → passes", r.passed, r.detail)
# Now mutate
Path(w,"src","App.jsx").write_bytes(b"// tampered\n")
r2 = run_download_gate(w)
check("download gate: tampered file → 409", not r2.passed and r2.status == 409)
shutil.rmtree(w)


# ════════════════════════════════════════════════════════════════════════════
print("\n── FIX 2: Live Proof Separation ───────────────────────────────────────")

# 2a: No DELIVERY_CLASSIFICATION.md → passes
w = ws()
r = check_live_proof_separation(w)
check("no DELIVERY_CLASSIFICATION → passes", r.passed)
shutil.rmtree(w)

# 2b: Implemented section with no live claims → passes
w = ws()
proof_dir = Path(w, "proof"); proof_dir.mkdir()
(proof_dir / "DELIVERY_CLASSIFICATION.md").write_text(
    "## Implemented\n\n- Dark mode toggle\n- Responsive layout\n\n## Mocked\n\n(none)\n"
)
r = check_live_proof_separation(w)
check("non-live Implemented claims → passes", r.passed)
shutil.rmtree(w)

# 2c: Stripe in Implemented, no proof → strict mode blocks
w = ws()
os.environ["CRUCIBAI_ENFORCEMENT_GATE"] = "strict"
proof_dir = Path(w, "proof"); proof_dir.mkdir()
(proof_dir / "DELIVERY_CLASSIFICATION.md").write_text(
    "## Implemented\n\n- Stripe payment integration (live)\n- Checkout flow\n\n## Mocked\n\n(none)\n"
)
r = check_live_proof_separation(w)
check("stripe in Implemented, no proof → 422 blocked", not r.passed and r.status == 422)
check("detail mentions stripe/payment",
      "stripe" in r.detail.lower() or "payment" in r.detail.lower())
# Check that DELIVERY_CLASSIFICATION.md was downgraded
dc_text = (Path(w, "proof", "DELIVERY_CLASSIFICATION.md")).read_text()
check("stripe claim auto-downgraded to Mocked in DC.md",
      "mocked" in dc_text.lower() and "auto-downgraded" in dc_text.lower())
shutil.rmtree(w)

# 2d: Stripe in Implemented WITH verified proof → passes
w = ws()
os.environ["CRUCIBAI_ENFORCEMENT_GATE"] = "strict"
proof_dir = Path(w, "proof"); proof_dir.mkdir()
(proof_dir / "DELIVERY_CLASSIFICATION.md").write_text(
    "## Implemented\n\n- Stripe payment integration\n\n## Mocked\n\n(none)\n"
)
# Write a proof index with strong stripe proof
proof_index = {
    "flat": [
        {"proof_type": "integration", "title": "stripe webhook idempotency proven",
         "payload": {"check": "stripe_webhook_idempotency_proven", "verification_class": "behavior_assertion"}}
    ]
}
(proof_dir / "proof_index.json").write_text(json.dumps(proof_index))
r = check_live_proof_separation(w)
check("stripe in Implemented WITH behavior_assertion proof → passes", r.passed, r.detail)
shutil.rmtree(w)

# 2e: Advisory mode → warns but doesn't block
w = ws()
os.environ["CRUCIBAI_ENFORCEMENT_GATE"] = "advisory"
proof_dir = Path(w, "proof"); proof_dir.mkdir()
(proof_dir / "DELIVERY_CLASSIFICATION.md").write_text(
    "## Implemented\n\n- Twilio SMS integration\n\n## Mocked\n\n(none)\n"
)
r = check_live_proof_separation(w)
check("advisory mode with unverified claim → passes (advisory)", r.passed)
os.environ["CRUCIBAI_ENFORCEMENT_GATE"] = "strict"
shutil.rmtree(w)


# ════════════════════════════════════════════════════════════════════════════
print("\n── FIX 3: Visual QA Blocking ──────────────────────────────────────────")

# 3a: VQA score < 55 → delivery gate blocks
w = ws()
write_biv_pass(w)
write_good_proof(w)
meta = Path(w, ".crucibai"); meta.mkdir(exist_ok=True)
(meta/"visual_qa.json").write_text(json.dumps({
    "passed": False, "score": 30, "orphans": [], "issues": ["no routes","no heading"]
}))
r = check_visual_qa(w)
check("VQA score=30 < 55 → blocked", not r.passed and r.status == 422)
check("detail mentions score", "30" in r.detail)
shutil.rmtree(w)

# 3b: VQA score >= 55 → passes
w = ws()
meta = Path(w, ".crucibai"); meta.mkdir()
(meta/"visual_qa.json").write_text(json.dumps({
    "passed": True, "score": 78, "orphans": [], "issues": []
}))
r = check_visual_qa(w)
check("VQA score=78 → passes", r.passed)
shutil.rmtree(w)

# 3c: Orphan count > 10 → blocked even if score ok
w = ws()
meta = Path(w, ".crucibai"); meta.mkdir()
orphans = [f"src/components/Orphan{i}.jsx" for i in range(12)]
(meta/"visual_qa.json").write_text(json.dumps({
    "passed": False, "score": 65, "orphans": orphans, "issues": []
}))
r = check_visual_qa(w)
check("12 orphans > max 10 → blocked", not r.passed and r.status == 422)
check("detail mentions orphans", "orphan" in r.detail.lower())
shutil.rmtree(w)

# 3d: No VQA marker → gate skipped (passes)
w = ws()
r = check_visual_qa(w)
check("no VQA marker → gate skipped (passes)", r.passed)
shutil.rmtree(w)

# 3e: Full VQA run on a workspace with valid code → passes gate
w = ws()
src_dir = Path(w, "src"); src_dir.mkdir()
pages = Path(w, "src", "pages"); pages.mkdir()
(src_dir/"App.jsx").write_text(
    "import React from 'react';\nimport{Routes,Route}from'react-router-dom';\n"
    "import HomePage from './pages/HomePage.jsx';\n"
    "export default function App(){return<Routes><Route path='/' element={<HomePage/>}/></Routes>;}\n"
)
(src_dir/"main.jsx").write_text(
    "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App.jsx';\n"
    "ReactDOM.createRoot(document.getElementById('root')).render(<App/>);\n"
)
(pages/"HomePage.jsx").write_text("<main><h1>Home</h1></main>")
dist = Path(w,"dist"); dist.mkdir()
(dist/"index.html").write_text("<html><head><title>App</title></head><body><div id='root'></div><script src='/app.js'></script></body></html>")
write_biv_pass(w); write_good_proof(w)
vqa = run_visual_qa(w)
r = check_visual_qa(w)
check("valid workspace VQA run + gate → passes", r.passed, f"score={vqa.score}")
shutil.rmtree(w)


# ════════════════════════════════════════════════════════════════════════════
print("\n── FIX 4: Browser QA (Headless Route Validation) ─────────────────────")

# 4a: HTML contract parser — good HTML
good_html = """<!DOCTYPE html>
<html><head><title>My App</title></head>
<body><div id="root"></div><script src="/assets/app.js"></script></body></html>"""
ok, issues = _check_html_contracts(good_html, "/")
check("good HTML passes contracts", ok, str(issues))

# 4b: Bad HTML — missing title
bad_html = "<html><body><div id='root'></div><script src='/app.js'></script></body></html>"
ok, issues = _check_html_contracts(bad_html, "/")
check("missing <title> → contract issue", not ok and any("title" in i for i in issues))

# 4c: Bad HTML — missing root
bad_html2 = "<html><head><title>X</title></head><body><script src='/app.js'></script></body></html>"
ok, issues = _check_html_contracts(bad_html2, "/")
check("missing #root → contract issue", not ok and any("root" in i for i in issues))

# 4d: Bad HTML — missing script
bad_html3 = "<html><head><title>X</title></head><body><div id='root'></div></body></html>"
ok, issues = _check_html_contracts(bad_html3, "/")
check("missing <script src> → contract issue", not ok and any("script" in i.lower() for i in issues))

# 4e: run_browser_qa — no workspace
r = run_browser_qa("")
check("empty workspace → failed",  not r.passed)
check("method=skipped",            r.method == "skipped")

# 4f: run_browser_qa — no dist → skipped (source-only build)
w = ws()
Path(w,"src").mkdir()
Path(w,"src","App.jsx").write_text("export default function App(){return null;}")
r = run_browser_qa(w)
check("no dist → skipped (source-only)", r.passed and r.method == "skipped")
shutil.rmtree(w)

# 4g: run_browser_qa — dist with good HTML → static_http or file_analysis
w = ws()
dist = Path(w,"dist"); dist.mkdir()
(dist/"index.html").write_text(
    "<html><head><title>CrucibAI App</title></head>"
    "<body><div id='root'></div><script src='/assets/app.js'></script></body></html>"
)
r = run_browser_qa(w, routes=["/"])
check("dist with good HTML → passes",   r.passed, f"score={r.score} method={r.method} issues={r.issues}")
check("method is static_http or file_analysis", r.method in ("static_http","file_analysis","playwright"))
check("routes_total >= 1",             r.routes_total >= 1)
check("browser_qa.json written",       Path(w,".crucibai","browser_qa.json").exists())
shutil.rmtree(w)

# 4h: run_browser_qa — dist with bad HTML → fails contracts
w = ws()
dist = Path(w,"dist"); dist.mkdir()
(dist/"index.html").write_text("<html><body><p>broken</p></body></html>")  # no title, no root, no script
r = run_browser_qa(w, routes=["/"])
check("dist with bad HTML → contract issues detected", len(r.issues) > 0, str(r.issues))
shutil.rmtree(w)

# 4i: check_browser_qa gate — no dist → skipped (passes)
w = ws()
r = check_browser_qa(w)
check("check_browser_qa: no dist → passes (skipped)", r.passed)
shutil.rmtree(w)

# 4j: check_browser_qa gate — marker shows failed → 422
w = ws()
dist = Path(w,"dist"); dist.mkdir()
(dist/"index.html").write_text("<html></html>")
meta = Path(w,".crucibai"); meta.mkdir()
(meta/"browser_qa.json").write_text(json.dumps({
    "passed": False, "score": 30, "method": "file_analysis",
    "routes_ok": 0, "routes_total": 1,
    "issues": ["/ missing <title>", "/ missing #root"]
}))
r = check_browser_qa(w)
check("browser_qa marker score=30 → 422", not r.passed and r.status == 422)
check("detail mentions score", "30" in r.detail)
shutil.rmtree(w)

# 4k: check_browser_qa gate — marker shows pass → passes
w = ws()
dist = Path(w,"dist"); dist.mkdir()
(dist/"index.html").write_text("<html></html>")
meta = Path(w,".crucibai"); meta.mkdir()
(meta/"browser_qa.json").write_text(json.dumps({
    "passed": True, "score": 90, "method": "static_http",
    "routes_ok": 3, "routes_total": 3, "issues": []
}))
r = check_browser_qa(w)
check("browser_qa marker pass → gate passes", r.passed)
shutil.rmtree(w)


# ════════════════════════════════════════════════════════════════════════════
print("\n── Full publish gate: all 7 sub-gates ────────────────────────────────")
w = ws()
write_biv_pass(w, 88)
write_good_proof(w)

# dist/index.html
dist = Path(w,"dist"); dist.mkdir()
good_html_str = "<html><head><title>App</title></head><body><div id='root'></div><script src='/app.js'></script></body></html>"
(dist/"index.html").write_text(good_html_str)

# seal (intact)
content = good_html_str.encode()
meta = Path(w,".crucibai"); meta.mkdir(exist_ok=True)
manifest = {"files":[{"path":"dist/index.html","sha256":sha256(content),"bytes":len(content)}]}
seal = {"manifest_sha256": sha256(json.dumps(manifest["files"],sort_keys=True).encode())}
(meta/"seal.json").write_text(json.dumps(seal))
(meta/"artifact_manifest.json").write_text(json.dumps(manifest))

# No DELIVERY_CLASSIFICATION → live proof gate passes
# VQA marker (pass)
(meta/"visual_qa.json").write_text(json.dumps({"passed":True,"score":75,"orphans":[],"issues":[]}))
# Browser QA marker (pass)
(meta/"browser_qa.json").write_text(json.dumps({
    "passed":True,"score":85,"method":"file_analysis",
    "routes_ok":1,"routes_total":1,"issues":[]
}))

r = run_publish_gate(w)
check("full publish gate: all 7 sub-gates pass", r.passed, r.detail)
shutil.rmtree(w)


# ════════════════════════════════════════════════════════════════════════════
print(f"\n{'═'*60}")
print(f"  Results: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
if FAIL:
    print("  STATUS: FAIL")
    sys.exit(1)
else:
    print("  STATUS: ALL PASS ✓")
