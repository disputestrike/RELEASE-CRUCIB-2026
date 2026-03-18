"""
CrucibAI Iterative Builder
===========================
Generates the FULL file structure like Manus.
Each pass is one focused AI call under 8192 tokens.
Total: 25-35 files across 5-6 passes.
"""
import asyncio
import re
import logging
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)

# ── Full file structure per build type ────────────────────────────────────────

BUILD_STRUCTURES = {
    "fullstack": {
        "passes": [
            {
                "name": "config",
                "desc": "Project config & entry files",
                "files": [
                    "/package.json       — dependencies: react, react-dom, react-router-dom, lucide-react, framer-motion, recharts, clsx",
                    "/index.html         — Vite HTML entry, <div id='root'>, loads Tailwind CDN",
                    "/src/main.jsx       — ReactDOM.createRoot, renders <App/>",
                    "/src/index.css      — CSS variables, global resets, fonts",
                    "/src/const.js       — all hardcoded data arrays (products, team, pricing, testimonials, nav links)",
                ],
            },
            {
                "name": "app_and_layout",
                "desc": "App router + layout components",
                "files": [
                    "/src/App.jsx                    — MemoryRouter, all Routes, imports all pages",
                    "/src/components/Navbar.jsx      — full responsive nav, logo, links, mobile hamburger menu",
                    "/src/components/Footer.jsx      — links, social icons, newsletter, copyright",
                    "/src/components/Layout.jsx      — wraps Navbar + {children} + Footer",
                ],
            },
            {
                "name": "ui_components",
                "desc": "Reusable UI components",
                "files": [
                    "/src/components/Hero.jsx        — hero section: headline, subtext, CTA, gradient bg, framer-motion",
                    "/src/components/Features.jsx    — 6-card features grid with lucide icons",
                    "/src/components/Pricing.jsx     — 3-tier pricing cards with CTA buttons",
                    "/src/components/Testimonials.jsx — testimonial carousel with avatars",
                    "/src/components/CTA.jsx         — call-to-action banner section",
                    "/src/lib/utils.js               — cn() helper, formatDate, formatCurrency, truncate",
                ],
            },
            {
                "name": "pages",
                "desc": "All page components",
                "files": [
                    "/src/pages/Home.jsx     — imports Hero+Features+Testimonials+CTA, full home page",
                    "/src/pages/About.jsx    — team grid, mission, story, values — real content",
                    "/src/pages/Services.jsx — services cards with descriptions, icons, pricing",
                    "/src/pages/Contact.jsx  — contact form (controlled), map placeholder, contact info",
                ],
            },
            {
                "name": "extra_pages",
                "desc": "Additional pages",
                "files": [
                    "/src/pages/Pricing.jsx  — full pricing page, uses Pricing component, FAQs accordion",
                    "/src/pages/Blog.jsx     — blog listing with category filter, article cards",
                    "/src/contexts/AppContext.jsx — React context: theme, user, cart or app state",
                    "/src/hooks/useLocalStorage.js — custom hook for localStorage",
                ],
            },
        ]
    },
    "saas": {
        "passes": [
            {
                "name": "config",
                "desc": "Config + entry",
                "files": [
                    "/package.json        — react, react-router-dom, recharts, lucide-react, framer-motion",
                    "/index.html          — Vite entry with Tailwind CDN",
                    "/src/main.jsx        — ReactDOM.createRoot",
                    "/src/index.css       — dark SaaS theme CSS vars",
                    "/src/const.js        — mock data: metrics, users, plans, activity feed",
                ],
            },
            {
                "name": "layout",
                "desc": "App shell",
                "files": [
                    "/src/App.jsx                    — MemoryRouter: / (Home), /login, /dashboard, /settings",
                    "/src/components/Sidebar.jsx     — collapsible sidebar, nav items with icons, user avatar",
                    "/src/components/Header.jsx      — top bar, search, notifications bell, user menu",
                    "/src/components/Layout.jsx      — Sidebar + Header + {children} layout shell",
                ],
            },
            {
                "name": "dashboard",
                "desc": "Dashboard components",
                "files": [
                    "/src/components/MetricCard.jsx  — stat card with trend up/down indicator",
                    "/src/components/Chart.jsx       — recharts line/bar chart with real data",
                    "/src/components/DataTable.jsx   — sortable table with pagination",
                    "/src/pages/Dashboard.jsx        — metrics row, chart, activity feed, quick actions",
                ],
            },
            {
                "name": "pages",
                "desc": "All SaaS pages",
                "files": [
                    "/src/pages/Home.jsx     — marketing landing: hero, features, pricing, CTA",
                    "/src/pages/Login.jsx    — login form, localStorage auth simulation",
                    "/src/pages/Signup.jsx   — signup form with validation",
                    "/src/pages/Settings.jsx — profile, billing, API keys, notifications tabs",
                    "/src/contexts/AuthContext.jsx — auth state, login/logout, useAuth hook",
                ],
            },
        ]
    },
    "landing": {
        "passes": [
            {
                "name": "config",
                "desc": "Config + entry",
                "files": [
                    "/package.json    — react, react-dom, framer-motion, lucide-react",
                    "/index.html      — Vite entry with Tailwind CDN",
                    "/src/main.jsx    — ReactDOM.createRoot",
                    "/src/index.css   — global styles, animations",
                    "/src/const.js    — all content: headlines, features, testimonials, pricing, team",
                ],
            },
            {
                "name": "sections",
                "desc": "All landing sections",
                "files": [
                    "/src/App.jsx                    — single page, imports all sections in order",
                    "/src/components/Nav.jsx         — sticky header, logo, CTA button, mobile menu",
                    "/src/components/Hero.jsx        — bold hero: headline, subheadline, CTA, mockup image",
                    "/src/components/Features.jsx    — features grid with icons and descriptions",
                    "/src/components/HowItWorks.jsx  — numbered steps section",
                    "/src/components/Testimonials.jsx — social proof with avatars and quotes",
                    "/src/components/Pricing.jsx     — 3-tier pricing with toggle annual/monthly",
                    "/src/components/FAQ.jsx         — accordion FAQ section",
                    "/src/components/Footer.jsx      — links, socials, newsletter form",
                ],
            },
        ]
    },
    "mobile": {
        "passes": [
            {
                "name": "config",
                "desc": "Expo config + entry",
                "files": [
                    "/package.json        — expo, react-native, @react-navigation/native, lucide-react-native",
                    "/app.json            — Expo app config: name, slug, version, icon",
                    "/App.jsx             — NavigationContainer, Stack + Tab navigators",
                    "/src/theme.js        — colors, typography, spacing, shadow constants",
                    "/src/data.js         — all mock data arrays",
                ],
            },
            {
                "name": "components",
                "desc": "Reusable components",
                "files": [
                    "/src/components/Card.jsx        — reusable card with shadow",
                    "/src/components/Button.jsx      — primary/secondary/outline variants",
                    "/src/components/Header.jsx      — screen header with back button",
                    "/src/components/BottomTabs.jsx  — bottom tab bar navigator",
                ],
            },
            {
                "name": "screens",
                "desc": "All screens",
                "files": [
                    "/src/screens/HomeScreen.jsx     — main screen with content list",
                    "/src/screens/DetailScreen.jsx   — detail view with full content",
                    "/src/screens/ProfileScreen.jsx  — user profile with settings",
                    "/src/screens/SearchScreen.jsx   — search with filter chips",
                    "/src/screens/OnboardingScreen.jsx — 3-slide onboarding flow",
                ],
            },
        ]
    },
    "ai_agent": {
        "passes": [
            {
                "name": "config",
                "desc": "Config + entry",
                "files": [
                    "/package.json    — react, react-dom, lucide-react, framer-motion",
                    "/index.html      — Vite entry",
                    "/src/main.jsx    — entry point",
                    "/src/index.css   — dark chat UI styles",
                    "/src/const.js    — agent configs, example prompts, conversation starters",
                ],
            },
            {
                "name": "app_and_components",
                "desc": "Agent UI",
                "files": [
                    "/src/App.jsx                        — MemoryRouter: /, /chat/:agentId, /config",
                    "/src/components/ChatMessage.jsx     — message bubble: user/agent, timestamp, copy button",
                    "/src/components/ChatInput.jsx       — input with send, voice, attach buttons",
                    "/src/components/AgentCard.jsx       — agent selection card with avatar, description",
                    "/src/components/Sidebar.jsx         — conversation history list",
                    "/src/hooks/useChat.js               — chat state, message history, simulated responses",
                    "/src/contexts/ChatContext.jsx       — global chat state provider",
                ],
            },
            {
                "name": "pages",
                "desc": "Agent pages",
                "files": [
                    "/src/pages/Home.jsx       — agent gallery grid with search and filter",
                    "/src/pages/Chat.jsx       — full chat interface using ChatMessage + ChatInput",
                    "/src/pages/AgentConfig.jsx — configure agent: name, model, system prompt, tools",
                ],
            },
        ]
    },
    "game": {
        "passes": [
            {
                "name": "config",
                "desc": "Config + entry",
                "files": [
                    "/package.json    — react, react-dom, framer-motion",
                    "/index.html      — Vite entry",
                    "/src/main.jsx    — entry point",
                    "/src/index.css   — dark game styles, canvas styles",
                    "/src/const.js    — game config: levels, speeds, colors, scoring",
                ],
            },
            {
                "name": "game_engine",
                "desc": "Game logic",
                "files": [
                    "/src/App.jsx                  — game state machine: menu → playing → paused → gameover",
                    "/src/game/useGameLoop.js      — requestAnimationFrame game loop hook",
                    "/src/game/collision.js        — collision detection utilities",
                    "/src/game/entities.js         — player, enemies, items, bullets classes",
                    "/src/components/GameCanvas.jsx — canvas rendering with useRef",
                    "/src/components/HUD.jsx        — score, lives, level, power-ups display",
                    "/src/pages/Menu.jsx            — main menu with high scores table",
                    "/src/pages/Game.jsx            — game screen, uses GameCanvas + HUD",
                ],
            },
        ]
    },
}


def get_build_structure(build_kind: str) -> dict:
    return BUILD_STRUCTURES.get(build_kind, BUILD_STRUCTURES["fullstack"])


def parse_files_from_response(text: str) -> Dict[str, str]:
    """Extract all fenced code blocks with file paths."""
    pattern = r'```(?:jsx?|tsx?|css|html|json|ts|js)?:(/[\w./\-]+)\n([\s\S]*?)```'
    files = {}
    for match in re.finditer(pattern, text):
        path = match.group(1).strip()
        code = match.group(2).strip()
        if code and len(code) > 20:  # skip empty/tiny files
            files[path] = code
    if not files:
        # Fallback: plain code block → /src/App.jsx
        plain = re.findall(r'```(?:jsx?|tsx?)\n([\s\S]*?)```', text)
        if plain:
            files['/src/App.jsx'] = plain[0].strip()
    return files


def count_total_files(build_kind: str) -> int:
    structure = get_build_structure(build_kind)
    return sum(len(p["files"]) for p in structure["passes"])


async def run_iterative_build(
    prompt: str,
    build_kind: str,
    call_llm: Callable,
    on_progress: Optional[Callable] = None,
) -> Dict[str, str]:
    """
    Multi-turn build: each pass generates one section of files.
    Returns {filepath: code} for all files.
    """
    structure = get_build_structure(build_kind)
    passes = structure["passes"]
    all_files: Dict[str, str] = {}

    SYSTEM = f"""You are CrucibAI — expert React/frontend developer.
You are building a COMPLETE, PRODUCTION-QUALITY application for Sandpack browser preview.

ABSOLUTE RULES:
- Use MemoryRouter (NEVER BrowserRouter — breaks in iframe)
- Tailwind CSS only (loaded via CDN in index.html — no config needed)
- lucide-react for icons, framer-motion for animations, recharts for charts
- Real hardcoded content — NO Lorem ipsum, NO "placeholder text", NO "// add content here"
- NO fetch(), NO axios, NO API calls, NO require(), NO Node.js imports
- EVERY file must be 100% complete — no truncation, no "// rest here", no TODOs
- Import paths must match exactly: './components/Navbar' not '../components/Navbar'

OUTPUT FORMAT — one fenced block per file, path in the opening fence:
```jsx:/src/components/Navbar.jsx
// complete code
```
```css:/src/index.css
/* complete styles */
```
```json:/package.json
{{ "name": "app" }}
```"""

    for i, pass_info in enumerate(passes):
        step_name = pass_info["name"]
        file_list = "\n".join(f"  {f}" for f in pass_info["files"])

        # Build context from already-generated files
        context_parts = []
        if all_files:
            generated = sorted(all_files.keys())
            context_parts.append(f"ALREADY GENERATED ({len(generated)} files):")
            context_parts.extend(f"  {p}" for p in generated)
            # Include App.jsx structure for reference if available
            app_key = next((k for k in ['/src/App.jsx','/src/App.js','/App.jsx','/App.js'] if k in all_files), None)
            if app_key:
                snippet = all_files[app_key][:600]
                context_parts.append(f"\nApp structure (for consistent imports):\n```\n{snippet}\n...\n```")
        context = "\n".join(context_parts)

        message = f"""Project: {prompt}
Build type: {build_kind}
Pass {i+1} of {len(passes)}: {step_name.upper()} — {pass_info['desc']}

{context}

Generate THESE files now — every file COMPLETE with real content:
{file_list}

Rules for this pass:
- Every file fully implemented, no placeholders
- Use data from /src/const.js for all content (import it)
- Import components using exact paths shown above
- Real content specific to: {prompt}

Output each file in its fenced block now:"""

        try:
            logger.info(f"Iterative build pass {i+1}/{len(passes)}: {step_name}")
            response = await call_llm(message, SYSTEM)
            step_files = parse_files_from_response(response)

            if step_files:
                all_files.update(step_files)
                logger.info(f"  Pass {step_name}: {len(step_files)} files → total {len(all_files)}")
            else:
                logger.warning(f"  Pass {step_name}: no files parsed")

            if on_progress:
                await on_progress(step_name, dict(all_files))

        except Exception as e:
            logger.error(f"Pass {step_name} failed: {e}")
            continue

    logger.info(f"Build complete: {len(all_files)} total files")
    return all_files
