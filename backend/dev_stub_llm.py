"""
When CRUCIBAI_DEV=1 and no LLM provider keys are set, return deterministic
plan / file outputs so Workspace preview and flows can be tested locally.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from llm_router import router

REAL_AGENT_NO_LLM_KEYS_DETAIL = (
    "CRUCIBAI_REAL_AGENT_ONLY is enabled but no LLM API keys are configured. "
    "Set ANTHROPIC_API_KEY, CEREBRAS_API_KEY, and/or LLAMA_API_KEY (or disable CRUCIBAI_REAL_AGENT_ONLY for local dev)."
)


def _real_agent_only() -> bool:
    v = (os.environ.get("CRUCIBAI_REAL_AGENT_ONLY") or "").strip().lower()
    return v in ("1", "true", "yes", "on")


def is_real_agent_only() -> bool:
    """True when the deployment forbids dev stubs (crew + chat stub); real LLM keys must be present."""
    return _real_agent_only()


def chat_llm_available(effective_keys: Optional[Dict[str, Any]] = None) -> bool:
    """Whether server/workspace effective keys or env can reach an LLM (matches stub_build_enabled key detection)."""
    ek = effective_keys or {}
    if str(ek.get("anthropic") or "").strip():
        return True
    if str(ek.get("cerebras") or "").strip():
        return True
    return bool(
        router.llama_available or router.cerebras_available or router.haiku_available
    )


def stub_build_enabled() -> bool:
    # Production-style: forbid dev stub when real LLM execution is required.
    if _real_agent_only():
        return False
    # Pytest sets CRUCIBAI_TEST=1; do not stub or API contract tests break when .env has CRUCIBAI_DEV=1.
    if os.environ.get("CRUCIBAI_TEST") == "1":
        return False
    if os.environ.get("CRUCIBAI_DEV") != "1":
        return False
    return not (
        router.llama_available or router.cerebras_available or router.haiku_available
    )


def detect_build_kind(message: str) -> str:
    p = (message or "").lower()
    if any(x in p for x in ("mobile", "react native", "expo", "ios app", "android")):
        return "mobile"
    if any(x in p for x in ("saas", "dashboard", "admin panel", "subscription")):
        return "saas"
    if any(x in p for x in ("landing page", "one page", "marketing page")):
        return "landing"
    if any(x in p for x in ("agent", "automation", "chatbot")):
        return "ai_agent"
    if any(x in p for x in ("game", "2d game", "browser game")):
        return "game"
    return "fullstack"


def _safe_title(prompt: str, max_len: int = 72) -> str:
    raw = (prompt or "Your app").strip()[:max_len]
    raw = re.sub(r"[\r\n`]+", " ", raw)
    return raw or "Your app"


def plan_and_suggestions(prompt: str, build_kind: str) -> Tuple[str, List[str]]:
    title = _safe_title(prompt)
    plan = f"""Plan
Key Features:
• Local dev preview – stub build (no LLM API keys in backend/.env)
• Sandpack preview – MemoryRouter app you can click through
• Production path – add ANTHROPIC_API_KEY, CEREBRAS_API_KEY, and/or LLAMA_API_KEY

Your request (summary): {title} (kind: {build_kind})

Design Language:
• Slate / emerald theme, readable typography
• Single-column layout with clear call-to-action

Color Palette:
• Primary: Emerald (#10b981)
• Secondary: Slate (#64748b)
• Accent: Amber (#f59e0b)
• Background: Slate 900 (#0f172a)

Components:
• Hero explaining dev-stub mode
• Link to secondary route
• Footer hint to configure keys

Let me build this now."""
    suggestions = [
        "Add real LLM keys for full multi-file generation",
        "Try a longer product prompt after keys are set",
        "Use Credit Center if you hit 402 on builds",
    ]
    return plan, suggestions


def stub_file_dict(prompt: str, build_kind: str) -> Dict[str, str]:
    title_js = json.dumps(_safe_title(prompt))
    app_js = f"""import React from 'react';
import {{ MemoryRouter as Router, Routes, Route, Link }} from 'react-router-dom';

function Home() {{
  const title = {title_js};
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8">
      <h1 className="text-3xl font-bold text-emerald-400 mb-4">CrucibAI — local dev build</h1>
      <p className="text-slate-300 mb-4 max-w-2xl leading-relaxed">
        This preview is a <strong>stub</strong> because no LLM keys are configured (CRUCIBAI_DEV=1).
        Your idea: <span className="text-white font-medium">{{title}}</span>
        <span className="block mt-2 text-slate-500 text-sm">Build kind: {build_kind}</span>
      </p>
      <p className="text-slate-400 mb-6 max-w-2xl text-sm">
        Set <code className="bg-slate-800 px-1 rounded">ANTHROPIC_API_KEY</code>,{' '}
        <code className="bg-slate-800 px-1 rounded">CEREBRAS_API_KEY</code>, or{' '}
        <code className="bg-slate-800 px-1 rounded">LLAMA_API_KEY</code> in{' '}
        <code className="bg-slate-800 px-1 rounded">backend/.env</code>, restart the API, then build again for real output.
      </p>
      <Link className="inline-block text-emerald-400 underline font-medium" to="/about">About this stub →</Link>
    </div>
  );
}}

function About() {{
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-8">
      <Link className="text-emerald-400 underline" to="/">← Back</Link>
      <h2 className="text-2xl font-semibold mt-6 mb-3">Stub mode</h2>
      <p className="text-slate-400 max-w-xl">
        The full pipeline (plan → iterative passes → many files) runs once an LLM provider is available.
        Database, auth, and preview still work for local testing.
      </p>
    </div>
  );
}}

export default function App() {{
  return (
    <Router>
      <Routes>
        <Route path="/" element={{<Home />}} />
        <Route path="/about" element={{<About />}} />
      </Routes>
    </Router>
  );
}}
"""
    index_js = """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
"""
    styles_css = """/* Dev stub — Tailwind via Sandpack CDN in workspace */
body { margin: 0; }
"""
    return {
        "/App.js": app_js,
        "/index.js": index_js,
        "/styles.css": styles_css,
    }


def stub_multifile_markdown(prompt: str, build_kind: str | None = None) -> str:
    bk = build_kind or detect_build_kind(prompt)
    files = stub_file_dict(prompt, bk)
    blocks = []
    for path in sorted(files.keys()):
        rel = path.lstrip("/")
        lang = "css" if rel.endswith(".css") else "jsx"
        blocks.append(f"```{lang}:/{rel}\n{files[path]}\n```")
    return "\n\n".join(blocks)
