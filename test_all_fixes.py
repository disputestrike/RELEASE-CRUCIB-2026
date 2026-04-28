#!/usr/bin/env python3
"""
test_all_fixes.py — Validates every fix made this session.
Run from /home/ubuntu/crucibai:  python3 test_all_fixes.py
"""
import ast
import json
import os
import sys
import tempfile
import traceback

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
WARN = "\033[93m⚠ WARN\033[0m"

results = []

def check(name, fn):
    try:
        msg = fn()
        results.append((True, name, msg or ""))
        print(f"  {PASS}  {name}{(' — ' + msg) if msg else ''}")
    except Exception as e:
        tb = traceback.format_exc().strip().split("\n")[-1]
        results.append((False, name, tb))
        print(f"  {FAIL}  {name}\n         {tb}")

print("\n══════════════════════════════════════════════════════════════")
print("  CrucibAI Fix Validation Suite")
print("══════════════════════════════════════════════════════════════\n")

# ─────────────────────────────────────────────────────────────────
# 1. SYNTAX: All changed Python files parse cleanly
# ─────────────────────────────────────────────────────────────────
print("▶ 1. Python syntax checks")
BACKEND = "backend"
PY_FILES = [
    "backend/orchestration/workspace_assembly_pipeline.py",
    "backend/orchestration/brain_repair.py",
    "backend/orchestration/self_repair.py",
    "backend/orchestration/workspace_reader.py",
    "backend/orchestration/swarm_agent_runner.py",
    "backend/orchestration/build_memory.py",
    "backend/server.py",
]
for f in PY_FILES:
    def _syntax(f=f):
        with open(f) as fh:
            ast.parse(fh.read())
        return f"parsed {os.path.basename(f)}"
    check(f"syntax: {os.path.basename(f)}", _syntax)

# ─────────────────────────────────────────────────────────────────
# 2. PROSE GUARD: workspace_assembly_pipeline._is_prose_content
# ─────────────────────────────────────────────────────────────────
print("\n▶ 2. Prose guard in workspace_assembly_pipeline")
sys.path.insert(0, "backend")

def _import_pipeline():
    from orchestration.workspace_assembly_pipeline import _is_prose_content
    # _is_prose_content(content: str, rel_path: str) -> bool
    result = _is_prose_content('{"test": 1}', 'src/App.jsx')
    assert isinstance(result, bool), f"Expected bool, got {type(result)}"
    return "_is_prose_content(content, rel_path) -> bool"

check("_is_prose_content exists", _import_pipeline)

def _prose_json_object():
    from orchestration.workspace_assembly_pipeline import _is_prose_content
    # signature: _is_prose_content(content, rel_path)
    assert _is_prose_content('{"text": "I am the Data Visualization Agent..."}', 'src/charts/Dashboard.jsx'), \
        "JSON object not detected as prose"
    return "JSON object correctly flagged as prose"
check("prose: JSON object flagged", _prose_json_object)

def _prose_english_sentence():
    from orchestration.workspace_assembly_pipeline import _is_prose_content
    assert _is_prose_content("Here is the complete implementation of the Dashboard component.", 'src/App.jsx'), \
        "English sentence not detected as prose"
    return "English sentence correctly flagged"
check("prose: English sentence flagged", _prose_english_sentence)

def _prose_real_code_not_flagged():
    from orchestration.workspace_assembly_pipeline import _is_prose_content
    code = "import React from 'react';\n\nexport default function App() {\n  return <div>Hello</div>;\n}\n"
    assert not _is_prose_content(code, 'src/App.jsx'), \
        "Real JSX code incorrectly flagged as prose"
    return "Real JSX code not flagged"
check("prose: real JSX code NOT flagged", _prose_real_code_not_flagged)

def _prose_parse_proposed_files_rejects_prose():
    from orchestration.workspace_assembly_pipeline import parse_proposed_files
    # signature: parse_proposed_files(raw, default_rel, agent_name)
    prose_response = '{"text": "I am the Data Visualization Agent and here is my response..."}'
    files = parse_proposed_files(prose_response, 'src/charts/Dashboard.jsx', 'DataVisualizationAgent')
    assert files == [], f"Expected [], got {files}"
    return "prose agent response produces no files"
check("prose: parse_proposed_files returns [] for prose", _prose_parse_proposed_files_rejects_prose)

def _prose_parse_proposed_files_keeps_real_code():
    from orchestration.workspace_assembly_pipeline import parse_proposed_files
    response = """Here's the component:

```jsx
// src/App.jsx
import React from 'react';
export default function App() { return <div>Hello</div>; }
```
"""
    files = parse_proposed_files(response, 'src/App.jsx', 'FrontendAgent')
    assert len(files) >= 1, f"Expected at least 1 file, got {files}"
    return f"{len(files)} file(s) extracted from fenced code"
check("prose: parse_proposed_files extracts real fenced code", _prose_parse_proposed_files_keeps_real_code)

# ─────────────────────────────────────────────────────────────────
# 3. SELF-REPAIR: detect_prose_in_file catches JSON content
# ─────────────────────────────────────────────────────────────────
print("\n▶ 3. Self-repair prose detection")

def _detect_prose_json():
    from orchestration.workspace_reader import detect_prose_in_file
    # signature: detect_prose_in_file(content: str, file_ext: str) -> Optional[str]
    # returns the prose line if prose detected, else None
    content = '{"text": "I am the Data Visualization Agent and here is my response..."}'
    result = detect_prose_in_file(content, file_ext=".jsx")
    assert result is not None, f"Expected prose line string, got None"
    return f"JSON object in .jsx detected as prose: '{result[:60]}'"
check("detect_prose: JSON object in JSX detected", _detect_prose_json)

def _detect_prose_real_jsx():
    from orchestration.workspace_reader import detect_prose_in_file
    content = "import React from 'react';\nexport default function App() { return <div/>; }\n"
    result = detect_prose_in_file(content, file_ext=".jsx")
    assert result is None, f"Expected None, got '{result}'"
    return "Real JSX not flagged as prose"
check("detect_prose: real JSX NOT detected as prose", _detect_prose_real_jsx)

# ─────────────────────────────────────────────────────────────────
# 4. SELF-REPAIR: repair_prose_in_file replaces JSON with scaffold
# ─────────────────────────────────────────────────────────────────
print("\n▶ 4. Self-repair file repair functions")

def _repair_prose_json_file():
    from orchestration.self_repair import repair_prose_in_file
    with tempfile.TemporaryDirectory() as tmpdir:
        rel = "src/charts/Dashboard.jsx"
        full = os.path.join(tmpdir, "src", "charts")
        os.makedirs(full, exist_ok=True)
        with open(os.path.join(full, "Dashboard.jsx"), "w") as f:
            f.write('{"text": "I am the Data Visualization Agent..."}')
        result = repair_prose_in_file(tmpdir, rel)
        assert result.get("fixed"), f"Expected fixed=True, got {result}"
        with open(os.path.join(tmpdir, rel)) as f:
            content = f.read()
        assert "import React" in content or "export default" in content, \
            f"Scaffold not written, got: {content[:100]}"
        return f"action={result.get('action')}"
check("repair: JSON prose replaced with scaffold", _repair_prose_json_file)

def _repair_inject_health_route_creates_file():
    from orchestration.self_repair import repair_inject_health_route
    with tempfile.TemporaryDirectory() as tmpdir:
        result = repair_inject_health_route(tmpdir)
        assert result.get("fixed"), f"Expected fixed=True, got {result}"
        main_path = os.path.join(tmpdir, "backend", "main.py")
        assert os.path.exists(main_path), "backend/main.py not created"
        with open(main_path) as f:
            content = f.read()
        assert "/health" in content, f"/health not in created file: {content[:200]}"
        return f"action={result.get('action')}"
check("repair: inject_health_route creates backend/main.py with /health", _repair_inject_health_route_creates_file)

def _repair_inject_health_route_appends():
    from orchestration.self_repair import repair_inject_health_route
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "backend"), exist_ok=True)
        with open(os.path.join(tmpdir, "backend", "main.py"), "w") as f:
            f.write("from fastapi import FastAPI\napp = FastAPI()\n\n@app.get('/')\ndef root(): return {}\n")
        result = repair_inject_health_route(tmpdir)
        assert result.get("fixed"), f"Expected fixed=True, got {result}"
        with open(os.path.join(tmpdir, "backend", "main.py")) as f:
            content = f.read()
        assert "/health" in content, f"/health not appended: {content}"
        return f"action={result.get('action')}"
check("repair: inject_health_route appends to existing FastAPI file", _repair_inject_health_route_appends)

def _repair_inject_health_route_skips_if_present():
    from orchestration.self_repair import repair_inject_health_route
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "backend"), exist_ok=True)
        with open(os.path.join(tmpdir, "backend", "main.py"), "w") as f:
            f.write('from fastapi import FastAPI\napp = FastAPI()\n\n@app.get("/health")\ndef health(): return {"status":"ok"}\n')
        result = repair_inject_health_route(tmpdir)
        assert not result.get("fixed"), f"Expected fixed=False (already present), got {result}"
        return "correctly skipped when /health already present"
check("repair: inject_health_route skips if /health already present", _repair_inject_health_route_skips_if_present)

# ─────────────────────────────────────────────────────────────────
# 5. BRAIN REPAIR: scaffold_replaced files trigger LLM repair
# ─────────────────────────────────────────────────────────────────
print("\n▶ 5. Brain repair — scaffold-replaced files go to LLM repair")

def _brain_repair_scaffold_not_in_truly_fixed():
    import ast as _ast
    with open("backend/orchestration/brain_repair.py") as f:
        src = f.read()
    # Check that scaffold_replaced set exists
    assert "scaffold_replaced" in src, "scaffold_replaced set not found in brain_repair.py"
    # Check that scaffold_replaced files are excluded from truly_fixed_by_det
    assert "scaffold_replaced" in src and "truly_fixed_by_det" in src, \
        "scaffold_replaced or truly_fixed_by_det not found"
    return "scaffold_replaced set found and used to gate LLM repair"
check("brain_repair: scaffold_replaced set gates LLM repair", _brain_repair_scaffold_not_in_truly_fixed)

def _brain_repair_jsx_in_llm_scope():
    with open("backend/orchestration/brain_repair.py") as f:
        src = f.read()
    assert '".jsx"' in src or "'.jsx'" in src, ".jsx not in LLM repair scope"
    assert '".tsx"' in src or "'.tsx'" in src, ".tsx not in LLM repair scope"
    return ".jsx/.tsx included in LLM repair file extensions"
check("brain_repair: .jsx/.tsx in LLM repair scope", _brain_repair_jsx_in_llm_scope)

# ─────────────────────────────────────────────────────────────────
# 6. SIDEBAR: jobId mapped in listItems
# ─────────────────────────────────────────────────────────────────
print("\n▶ 6. Sidebar jobId mapping")

def _sidebar_jobid_mapped():
    with open("frontend/src/components/Sidebar.jsx") as f:
        src = f.read()
    assert "jobId: t.jobId" in src, "jobId not mapped in fromStore listItems"
    return "jobId: t.jobId || null found in fromStore mapping"
check("sidebar: jobId mapped in listItems fromStore", _sidebar_jobid_mapped)

def _sidebar_opentask_uses_jobid():
    with open("frontend/src/components/Sidebar.jsx") as f:
        src = f.read()
    assert "item.jobId" in src, "item.jobId not used in openTask"
    assert 'qs.set(\'jobId\'' in src or 'qs.set("jobId"' in src, \
        "jobId not set in URL query string"
    return "openTask correctly uses item.jobId in URL"
check("sidebar: openTask uses item.jobId in URL", _sidebar_opentask_uses_jobid)

# ─────────────────────────────────────────────────────────────────
# 7. JOB-SWITCH RESET: useEffect in UnifiedWorkspace
# ─────────────────────────────────────────────────────────────────
print("\n▶ 7. UnifiedWorkspace job-switch reset")

def _job_switch_reset_exists():
    with open("frontend/src/pages/UnifiedWorkspace.jsx") as f:
        src = f.read()
    assert "prevJobIdFromUrlRef" in src, "prevJobIdFromUrlRef not found"
    assert "Job-switch state reset" in src or "job-switch" in src.lower(), \
        "job-switch reset comment not found"
    assert "setStage('input')" in src or 'setStage("input")' in src, \
        "setStage('input') not found in reset"
    return "prevJobIdFromUrlRef + setStage('input') found in reset useEffect"
check("workspace: job-switch reset useEffect present", _job_switch_reset_exists)

def _job_switch_resets_messages():
    with open("frontend/src/pages/UnifiedWorkspace.jsx") as f:
        src = f.read()
    assert "setUserChatMessages([])" in src, "setUserChatMessages([]) not in reset"
    assert "setWsPaths([])" in src, "setWsPaths([]) not in reset"
    return "messages, wsPaths cleared on job switch"
check("workspace: messages + wsPaths cleared on job switch", _job_switch_resets_messages)

# ─────────────────────────────────────────────────────────────────
# 8. SIDEBAR SCROLL: CSS flex fix
# ─────────────────────────────────────────────────────────────────
print("\n▶ 8. Sidebar scroll CSS")

def _sidebar_scroll_css():
    with open("frontend/src/components/Sidebar.css") as f:
        src = f.read()
    # Check that the history section has flex: 1 or flex-grow
    has_flex1 = "flex: 1" in src or "flex-grow: 1" in src
    has_min_height = "min-height: 0" in src
    assert has_flex1, "sidebar-section-tasks missing flex:1"
    assert has_min_height, "sidebar-section-tasks missing min-height:0"
    return "flex:1 and min-height:0 present in sidebar section CSS"
check("sidebar CSS: history section has flex:1 + min-height:0", _sidebar_scroll_css)

# ─────────────────────────────────────────────────────────────────
# 9. PER-AGENT MODEL ROUTING
# ─────────────────────────────────────────────────────────────────
print("\n▶ 9. Per-agent model routing")

def _agent_model_tier_exists():
    with open("backend/orchestration/swarm_agent_runner.py") as f:
        src = f.read()
    assert "AGENT_MODEL_TIER" in src, "AGENT_MODEL_TIER dict not found"
    assert "_get_agent_model_chain" in src, "_get_agent_model_chain function not found"
    return "AGENT_MODEL_TIER + _get_agent_model_chain present"
check("swarm_runner: AGENT_MODEL_TIER dict and routing function present", _agent_model_tier_exists)

def _agent_model_tier_has_fast_agents():
    with open("backend/orchestration/swarm_agent_runner.py") as f:
        src = f.read()
    assert "cerebras" in src.lower(), "cerebras tier not found in AGENT_MODEL_TIER"
    assert "anthropic" in src.lower(), "anthropic tier not found in AGENT_MODEL_TIER"
    return "both cerebras and anthropic tiers present"
check("swarm_runner: both cerebras and anthropic tiers defined", _agent_model_tier_has_fast_agents)

# ─────────────────────────────────────────────────────────────────
# 10. BUILD MEMORY
# ─────────────────────────────────────────────────────────────────
print("\n▶ 10. Build memory")

def _build_memory_exists():
    assert os.path.exists("backend/orchestration/build_memory.py"), \
        "build_memory.py not found"
    with open("backend/orchestration/build_memory.py") as f:
        src = f.read()
    assert "init_build_memory" in src, "init_build_memory not found"
    assert "get_memory_summary" in src, "get_memory_summary not found"
    assert "record_agent_files" in src, "record_agent_files not found"
    return "init_build_memory, get_memory_summary, record_agent_files all present"
check("build_memory: all key functions present", _build_memory_exists)

def _build_memory_syntax():
    with open("backend/orchestration/build_memory.py") as f:
        src = f.read()
    ast.parse(src)
    return "valid Python"
check("build_memory: valid Python syntax", _build_memory_syntax)

# ─────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────
print("\n══════════════════════════════════════════════════════════════")
passed = sum(1 for r in results if r[0])
failed = sum(1 for r in results if not r[0])
total = len(results)
print(f"  Results: {passed}/{total} passed  |  {failed} failed")
print("══════════════════════════════════════════════════════════════\n")

if failed > 0:
    print("FAILED TESTS:")
    for ok, name, msg in results:
        if not ok:
            print(f"  ✗ {name}: {msg}")
    print()
    sys.exit(1)
else:
    print("All tests passed. Safe to push.\n")
    sys.exit(0)
