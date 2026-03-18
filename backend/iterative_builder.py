"""
CrucibAI Iterative Builder
===========================
Full-stack, full-structure generation matching Manus quality.
Generates: TypeScript frontend + Express/Python backend + config files.
"""
import asyncio, re, logging
from typing import Dict, Optional, Callable
logger = logging.getLogger(__name__)

# ── Static config files injected on every build ───────────────────────────────
STATIC_FILES = {
    "fullstack": {
        "/.gitignore": "node_modules\ndist\nbuild\n.env\n.env.local\n*.log\n.DS_Store\ncoverage\n.vite",
        "/.gitkeep": "",
        "/public/favicon.ico": "<!-- placeholder -->",
        "/public/robots.txt": "User-agent: *\nAllow: /",
        "/patches/.gitkeep": "",
        "/.prettierrc": '{\n  "semi": true,\n  "singleQuote": true,\n  "tabWidth": 2,\n  "trailingComma": "es5"\n}',
        "/.prettierignore": "node_modules\ndist\nbuild\n.next",
        "/tsconfig.json": '{\n  "compilerOptions": {\n    "target": "ES2020",\n    "useDefineForClassFields": true,\n    "lib": ["ES2020", "DOM", "DOM.Iterable"],\n    "module": "ESNext",\n    "skipLibCheck": true,\n    "moduleResolution": "bundler",\n    "allowImportingTsExtensions": true,\n    "resolveJsonModule": true,\n    "isolatedModules": true,\n    "noEmit": true,\n    "jsx": "react-jsx",\n    "strict": true,\n    "noUnusedLocals": true,\n    "noUnusedParameters": true,\n    "noFallthroughCasesInSwitch": true\n  },\n  "include": ["src"],\n  "references": [{ "path": "./tsconfig.node.json" }]\n}',
        "/tsconfig.node.json": '{\n  "compilerOptions": {\n    "composite": true,\n    "skipLibCheck": true,\n    "module": "ESNext",\n    "moduleResolution": "bundler",\n    "allowSyntheticDefaultImports": true\n  },\n  "include": ["vite.config.ts"]\n}',
        "/vite.config.ts": 'import { defineConfig } from \'vite\';\nimport react from \'@vitejs/plugin-react\';\n\nexport default defineConfig({\n  plugins: [react()],\n  server: { port: 3000 },\n});',
        "/components.json": '{\n  "$schema": "https://ui.shadcn.com/schema.json",\n  "style": "default",\n  "rsc": false,\n  "tsx": true,\n  "tailwind": {\n    "config": "tailwind.config.js",\n    "css": "src/index.css",\n    "baseColor": "slate",\n    "cssVariables": true\n  },\n  "aliases": {\n    "components": "@/components",\n    "utils": "@/lib/utils"\n  }\n}',
    },
    "saas": {},
    "landing": {},
    "mobile": {
        "/.gitignore": "node_modules\ndist\n.expo\n*.log\n.DS_Store",
        "/.gitkeep": "",
        "/app.json": '{\n  "expo": {\n    "name": "MyApp",\n    "slug": "myapp",\n    "version": "1.0.0",\n    "orientation": "portrait",\n    "icon": "./assets/icon.png",\n    "splash": { "resizeMode": "contain", "backgroundColor": "#ffffff" },\n    "platforms": ["ios", "android", "web"]\n  }\n}',
        "/.prettierrc": '{\n  "semi": true,\n  "singleQuote": true,\n  "tabWidth": 2\n}',
    },
    "ai_agent": {},
    "game": {},
}

# ── Full structure matching Manus ──────────────────────────────────────────────
BUILD_STRUCTURES = {
    "fullstack": {
        "passes": [
            {
                "name": "config",
                "desc": "package.json, index.html, entry point, styles, constants",
                "files": [
                    "/package.json       — name, version, scripts (dev/build), dependencies: react ^18, react-dom, react-router-dom ^6, lucide-react, framer-motion, recharts, clsx, date-fns",
                    "/index.html         — <!DOCTYPE html>, <head> with Tailwind CDN + Google Fonts, <div id='root'>",
                    "/src/main.tsx       — import React, ReactDOM, App, './index.css'; createRoot(document.getElementById('root')).render(<App/>)",
                    "/src/index.css      — :root CSS variables (--primary, --secondary, colors), body reset, font-family, smooth scrolling",
                    "/src/const.ts       — export all data arrays and constants: navLinks, features, testimonials, pricing plans, team members, FAQ items — all typed with TS interfaces, all real content specific to the project",
                ],
            },
            {
                "name": "app_layout",
                "desc": "App router + layout shell",
                "files": [
                    "/src/App.tsx                   — import MemoryRouter, Routes, Route; import all page components; define all routes; wrap in <Layout>",
                    "/src/components/Layout.tsx     — accepts {children}: renders <Navbar/> + <main>{children}</main> + <Footer/>",
                    "/src/components/Navbar.tsx     — sticky top nav: logo left, links center, CTA right; mobile hamburger menu with useState; uses navLinks from const.ts",
                    "/src/components/Footer.tsx     — 4-column grid: brand+desc, links, contact, newsletter form; social icons; copyright row",
                ],
            },
            {
                "name": "ui_components",
                "desc": "Reusable UI components",
                "files": [
                    "/src/components/Hero.tsx        — large hero: animated headline with framer-motion, subtext, 2 CTA buttons, mockup/illustration; gradient background",
                    "/src/components/Features.tsx    — 6-card grid: each card has lucide icon, title, description; hover animation; data from const.ts",
                    "/src/components/Testimonials.tsx — carousel: 3 testimonial cards, avatar, name, role, quote; prev/next buttons; auto-advance",
                    "/src/components/Pricing.tsx     — 3-tier pricing cards: Free/Pro/Enterprise; feature list with checkmarks; highlighted middle card; CTA buttons",
                    "/src/components/CTA.tsx         — full-width CTA banner: headline, subtext, button; gradient background",
                    "/src/lib/utils.ts               — export cn(...classes) for Tailwind merging, formatDate(d), formatCurrency(n), truncate(str, n)",
                ],
            },
            {
                "name": "pages",
                "desc": "Main pages",
                "files": [
                    "/src/pages/Home.tsx     — import and compose Hero + Features + Testimonials + CTA sections; full home page",
                    "/src/pages/About.tsx    — hero banner, company story paragraph, team grid (4 members with photo placeholder, name, role), values section",
                    "/src/pages/Services.tsx — services grid: 6 cards each with icon, title, description, price; filter by category",
                    "/src/pages/Contact.tsx  — 2-column: left info (address, phone, email, hours), right contact form (name/email/subject/message, submit button with loading state)",
                ],
            },
            {
                "name": "more_pages_and_backend",
                "desc": "More pages + backend server + shared types",
                "files": [
                    "/src/pages/Pricing.tsx          — full pricing page: toggle annual/monthly, 3 tier cards, feature comparison table, FAQ accordion",
                    "/src/contexts/AppContext.tsx    — createContext with theme (dark/light), user state, cart; useApp() hook export",
                    "/src/hooks/useLocalStorage.ts   — generic hook: useLocalStorage<T>(key, initialValue) with get/set/remove",
                    "/shared/types.ts                — TypeScript interfaces: User, Product, NavLink, Feature, Testimonial, PricingPlan, ContactForm — match const.ts",
                    "/server/index.ts                — Express server: cors, json middleware; GET /api/health; GET /api/items; POST /api/contact; listen on port 5000",
                    "/ideas.md                       — # Project Ideas\n## Built: [project name]\n## Architecture: React + Express\n## Key Features: [list from prompt]\n## Future Improvements: [3 ideas]",
                ],
            },
        ]
    },
    "saas": {
        "passes": [
            {
                "name": "config",
                "desc": "Config + entry files",
                "files": [
                    "/package.json       — react, react-dom, react-router-dom, recharts, lucide-react, framer-motion, clsx",
                    "/index.html         — Vite HTML entry with Tailwind CDN",
                    "/src/main.tsx       — ReactDOM.createRoot entry",
                    "/src/index.css      — dark SaaS theme CSS variables",
                    "/src/const.ts       — mock data: metrics[], users[], plans[], activityFeed[], navItems[] — all typed",
                    "/shared/types.ts    — interfaces: User, Metric, Plan, ActivityItem, NavItem",
                ],
            },
            {
                "name": "app_layout",
                "desc": "Shell + auth",
                "files": [
                    "/src/App.tsx                    — MemoryRouter: public routes (/, /login, /signup) + protected routes (/dashboard, /settings, /users)",
                    "/src/components/Sidebar.tsx     — collapsible sidebar: logo, nav items with icons, user avatar + name at bottom, logout button",
                    "/src/components/Header.tsx      — top bar: breadcrumb, search input, notifications bell with badge, user dropdown menu",
                    "/src/components/Layout.tsx      — AppLayout: Sidebar + Header + <main>{children}</main>",
                    "/src/contexts/AuthContext.tsx   — AuthContext: { user, isAuthenticated, login(email,pass), logout, signup }; useAuth() hook",
                ],
            },
            {
                "name": "dashboard",
                "desc": "Dashboard components",
                "files": [
                    "/src/components/MetricCard.tsx  — card: title, value, trend (up/down %, colored), icon; animated count-up",
                    "/src/components/LineChart.tsx   — recharts ResponsiveContainer LineChart with real data from props",
                    "/src/components/BarChart.tsx    — recharts BarChart component",
                    "/src/components/DataTable.tsx   — sortable table: columns prop, data prop, pagination, search filter",
                    "/src/pages/Dashboard.tsx        — 4 MetricCards row, LineChart, BarChart, DataTable with recent activity",
                ],
            },
            {
                "name": "pages",
                "desc": "All pages",
                "files": [
                    "/src/pages/Home.tsx     — marketing landing: hero, 3 feature cards, pricing section, testimonials, CTA",
                    "/src/pages/Login.tsx    — centered card: email + password inputs, submit button, useAuth().login(), error display, link to signup",
                    "/src/pages/Signup.tsx   — name + email + password + confirm, useAuth().signup(), validation",
                    "/src/pages/Settings.tsx — tabs: Profile (avatar, name, email form), Security (password change), Billing (plan cards), Notifications (toggles)",
                    "/server/index.ts        — Express: /api/health, /api/auth/login, /api/auth/signup, /api/metrics, /api/users",
                    "/ideas.md               — project notes and planned features",
                ],
            },
        ]
    },
    "landing": {
        "passes": [
            {
                "name": "config",
                "desc": "Config + all content data",
                "files": [
                    "/package.json    — react, react-dom, framer-motion, lucide-react",
                    "/index.html      — Vite entry with Tailwind CDN and Google Fonts",
                    "/src/main.tsx    — entry point",
                    "/src/index.css   — global styles, CSS vars, keyframe animations",
                    "/src/const.ts    — ALL content: headline, features[], testimonials[], pricing[], faq[], footerLinks[], social[]",
                    "/shared/types.ts — Feature, Testimonial, PricingPlan, FAQItem interfaces",
                ],
            },
            {
                "name": "sections",
                "desc": "Full landing page",
                "files": [
                    "/src/App.tsx                     — imports all section components in order, renders as single page",
                    "/src/components/Nav.tsx          — sticky nav: logo, links, CTA button, mobile hamburger",
                    "/src/components/Hero.tsx         — headline (framer-motion), subtext, 2 CTA buttons, hero image/mockup",
                    "/src/components/Features.tsx     — 6-card features grid with icons from lucide-react",
                    "/src/components/HowItWorks.tsx   — numbered steps: icon, number, title, description",
                    "/src/components/Testimonials.tsx — 3 testimonial cards with avatar, stars, quote",
                    "/src/components/Pricing.tsx      — toggle monthly/annual, 3 tier cards, feature list",
                    "/src/components/FAQ.tsx          — accordion: question + answer, expand/collapse with animation",
                    "/src/components/Footer.tsx       — links, social icons, newsletter input, copyright",
                    "/ideas.md                        — project brief and key decisions",
                ],
            },
        ]
    },
    "mobile": {
        "passes": [
            {
                "name": "config",
                "desc": "Expo config",
                "files": [
                    "/package.json         — expo ~49, react-native, @react-navigation/native, @react-navigation/stack, @react-navigation/bottom-tabs",
                    "/app.json             — Expo config: name, slug, version, icon, splash",
                    "/App.tsx              — NavigationContainer, createBottomTabNavigator, all screens with icons",
                    "/src/theme.ts         — colors object, typography scale, spacing scale, shadows",
                    "/src/data.ts          — all mock data typed with TS interfaces",
                    "/shared/types.ts      — all TypeScript interfaces for the app",
                ],
            },
            {
                "name": "components",
                "desc": "Reusable components",
                "files": [
                    "/src/components/Card.tsx         — shadow card: title, subtitle, children",
                    "/src/components/Button.tsx       — variants: primary/secondary/outline/danger, loading state",
                    "/src/components/ListItem.tsx     — list row with icon, title, subtitle, chevron",
                    "/src/components/EmptyState.tsx   — centered empty state with icon and message",
                ],
            },
            {
                "name": "screens",
                "desc": "All screens",
                "files": [
                    "/src/screens/HomeScreen.tsx      — scrollable home with cards, featured section",
                    "/src/screens/DetailScreen.tsx    — detail view with back navigation, full content",
                    "/src/screens/ProfileScreen.tsx   — user profile, settings list, logout button",
                    "/src/screens/SearchScreen.tsx    — search input, filter chips, results list",
                    "/src/screens/OnboardingScreen.tsx — 3-slide swipeable onboarding with skip/next/done",
                    "/ideas.md                        — app concept and future features",
                ],
            },
        ]
    },
    "ai_agent": {
        "passes": [
            {
                "name": "config",
                "desc": "Config + agent data",
                "files": [
                    "/package.json    — react, react-dom, react-router-dom, lucide-react, framer-motion",
                    "/index.html      — entry with Tailwind CDN",
                    "/src/main.tsx    — entry point",
                    "/src/index.css   — dark chat theme styles",
                    "/src/const.ts    — agents[], examplePrompts[], conversationStarters[] — typed",
                    "/shared/types.ts — Agent, Message, Conversation, Tool interfaces",
                ],
            },
            {
                "name": "app_components",
                "desc": "Chat UI components",
                "files": [
                    "/src/App.tsx                        — MemoryRouter: /, /chat/:agentId, /config",
                    "/src/components/ChatMessage.tsx     — message bubble: role (user/agent), content, timestamp, copy button, code block rendering",
                    "/src/components/ChatInput.tsx       — textarea (auto-resize), send button, attach button, character count",
                    "/src/components/AgentCard.tsx       — agent card: avatar, name, description, capabilities chips, select button",
                    "/src/components/ConversationList.tsx — sidebar list of past conversations",
                    "/src/contexts/ChatContext.tsx        — messages state, sendMessage (simulated), clearChat, activeAgent",
                    "/src/hooks/useChat.ts               — useChatSimulation: fake streaming response with typewriter effect",
                ],
            },
            {
                "name": "pages",
                "desc": "Agent pages",
                "files": [
                    "/src/pages/Home.tsx        — agent gallery: search, filter by capability, AgentCard grid",
                    "/src/pages/Chat.tsx        — full chat: ConversationList sidebar + ChatMessage list + ChatInput",
                    "/src/pages/AgentConfig.tsx — configure: name, system prompt textarea, temperature slider, tools checkboxes",
                    "/server/index.ts           — Express: POST /api/chat (simulated AI response), GET /api/agents",
                    "/ideas.md                  — agent capabilities and roadmap",
                ],
            },
        ]
    },
    "game": {
        "passes": [
            {
                "name": "config",
                "desc": "Config + game constants",
                "files": [
                    "/package.json    — react, react-dom, framer-motion",
                    "/index.html      — entry with full-screen canvas styles",
                    "/src/main.tsx    — entry point",
                    "/src/index.css   — dark game theme, canvas styles, pixel font",
                    "/src/const.ts    — GAME_CONFIG: width, height, speeds, colors; LEVELS[]; LEADERBOARD[]",
                    "/shared/types.ts — GameState, Entity, Player, Enemy, Level interfaces",
                ],
            },
            {
                "name": "game_engine",
                "desc": "Full game",
                "files": [
                    "/src/App.tsx                   — game states: menu | playing | paused | gameover; useReducer for state",
                    "/src/game/useGameLoop.ts       — useRef for animationFrame, useCallback for update, returns { start, stop, fps }",
                    "/src/game/collision.ts         — isColliding(a,b), resolveCollision, pointInRect, circleRect",
                    "/src/game/entities.ts          — createPlayer(), createEnemy(type), createBullet(), createPowerUp() factory functions",
                    "/src/components/GameCanvas.tsx — useRef canvas, useEffect draws entities each frame, keyboard event listeners",
                    "/src/components/HUD.tsx        — score, lives (heart icons), level, power-up indicators",
                    "/src/components/Menu.tsx       — start screen: title, high scores table, difficulty select, start button",
                    "/src/components/GameOver.tsx   — game over screen: final score, high score, play again button",
                    "/ideas.md                      — game design notes and planned levels",
                ],
            },
        ]
    },
}


def get_build_structure(build_kind: str) -> dict:
    return BUILD_STRUCTURES.get(build_kind, BUILD_STRUCTURES["fullstack"])


def get_static_files(build_kind: str) -> Dict[str, str]:
    base = STATIC_FILES.get("fullstack", {})
    specific = STATIC_FILES.get(build_kind, {})
    return {**base, **specific}


def parse_files_from_response(text: str) -> Dict[str, str]:
    pattern = r'```(?:tsx?|jsx?|css|html|json|md|ya?ml|sh)?:(/[\w./\-]+)\n([\s\S]*?)```'
    files = {}
    for m in re.finditer(pattern, text):
        path, code = m.group(1).strip(), m.group(2).strip()
        if code and len(code) > 10:
            files[path] = code
    if not files:
        plain = re.findall(r'```(?:tsx?|jsx?)\n([\s\S]*?)```', text)
        if plain:
            files['/src/App.tsx'] = plain[0].strip()
    return files


async def run_iterative_build(
    prompt: str,
    build_kind: str,
    call_llm: Callable,
    on_progress: Optional[Callable] = None,
) -> Dict[str, str]:
    structure = get_build_structure(build_kind)
    passes = structure["passes"]
    # Inject static config files upfront
    all_files: Dict[str, str] = get_static_files(build_kind)

    SYSTEM = """You are CrucibAI — senior full-stack TypeScript developer.
Generate COMPLETE, PRODUCTION-QUALITY code. No placeholders, no TODOs.

FILE FORMAT — each file in its own fenced block with path:
```tsx:/src/components/Navbar.tsx
// complete TypeScript React code
```
```ts:/shared/types.ts
// complete TypeScript interfaces
```
```json:/package.json
{ "complete": "json" }
```
```md:/ideas.md
# complete markdown
```

RULES:
- TypeScript (.ts/.tsx) for all React/logic files
- MemoryRouter ONLY (never BrowserRouter — breaks in Sandpack iframe)
- Tailwind CSS classes for styling (CDN loaded)
- lucide-react icons, framer-motion animations, recharts charts
- Real content specific to the project — NO Lorem ipsum
- Complete imports — every imported symbol must be defined
- Exact import paths — './components/Navbar' not '../components/Navbar'"""

    for i, pass_info in enumerate(passes):
        file_list = "\n".join(f"  {f}" for f in pass_info["files"])
        context = ""
        if all_files:
            static_keys = set(get_static_files(build_kind).keys())
            generated = sorted(k for k in all_files.keys() if k not in static_keys)
            if generated:
                context = f"\nALREADY GENERATED:\n" + "\n".join(f"  {p}" for p in generated)
                app_key = next((k for k in ['/src/App.tsx','/src/App.jsx'] if k in all_files), None)
                if app_key:
                    context += f"\n\nApp.tsx (for consistent imports):\n```\n{all_files[app_key][:500]}\n...\n```"
                const_key = next((k for k in ['/src/const.ts','/src/const.js'] if k in all_files), None)
                if const_key:
                    context += f"\n\nconst.ts (use this data):\n```\n{all_files[const_key][:400]}\n...\n```"

        message = f"""Project: "{prompt}"
Build type: {build_kind}
Pass {i+1}/{len(passes)}: {pass_info['name'].upper()} — {pass_info['desc']}
{context}

Generate these files now — COMPLETE, no truncation:
{file_list}

Every file must be fully implemented with real content for: {prompt}"""

        try:
            logger.info(f"Pass {i+1}/{len(passes)}: {pass_info['name']}")
            response = await call_llm(message, SYSTEM)
            new_files = parse_files_from_response(response)
            if new_files:
                all_files.update(new_files)
                logger.info(f"  → {len(new_files)} files, total {len(all_files)}")
            else:
                logger.warning(f"  → no files parsed from response")
            if on_progress:
                await on_progress(pass_info['name'], dict(all_files))
        except Exception as e:
            logger.error(f"Pass {pass_info['name']} failed: {e}")

    logger.info(f"Build done: {len(all_files)} total files")
    return all_files
