"""
CrucibAI Iterative Builder
==========================
Multi-turn file generation pipeline.
Each step is one focused API call under 8192 tokens.
Produces 15-30 complete files for any build type.
"""
import asyncio
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── File structure per build type ─────────────────────────────────────────────
BUILD_STRUCTURES = {
    "fullstack": {
        "passes": [
            {
                "name": "scaffold",
                "instruction": "Generate ONLY these 3 files — complete, no placeholders:\n1. /App.js (MemoryRouter, all routes, import Navbar+Footer)\n2. /styles.css (global styles, CSS variables, fonts)\n3. /components/Navbar.js (full responsive nav, logo, links, mobile menu)",
            },
            {
                "name": "components",
                "instruction": "Generate ONLY these component files — complete, no placeholders:\n1. /components/Footer.js (links, socials, copyright)\n2. /components/Hero.js (bold hero section, CTA button, gradient bg)\n3. /components/Features.js (3-6 feature cards with icons)\n4. /components/Pricing.js (3 tier cards with CTA buttons)",
            },
            {
                "name": "pages",
                "instruction": "Generate ONLY these page files — complete, no placeholders:\n1. /pages/Home.js (uses Hero + Features components, full content)\n2. /pages/About.js (team, mission, story — real hardcoded content)\n3. /pages/Contact.js (contact form with validation, map placeholder)",
            },
            {
                "name": "extra_pages",
                "instruction": "Generate ONLY these page files — complete, no placeholders:\n1. /pages/Services.js (services grid with descriptions and icons)\n2. /pages/Pricing.js (uses Pricing component, FAQs section)\n3. /pages/Blog.js (article cards grid with categories)",
            },
        ]
    },
    "landing": {
        "passes": [
            {
                "name": "scaffold",
                "instruction": "Generate ONLY these files — complete, one-page landing:\n1. /App.js (single page, no routing needed, import all sections)\n2. /styles.css (global styles, animations)\n3. /components/Nav.js (sticky header, logo, CTA button)",
            },
            {
                "name": "sections",
                "instruction": "Generate ONLY these section files — complete:\n1. /components/Hero.js (hero with headline, subtext, CTA, mockup)\n2. /components/Features.js (feature grid with icons)\n3. /components/Social.js (testimonials carousel)\n4. /components/Pricing.js (3 tier cards)\n5. /components/Footer.js (links, newsletter signup)",
            },
        ]
    },
    "saas": {
        "passes": [
            {
                "name": "scaffold",
                "instruction": "Generate ONLY these files:\n1. /App.js (MemoryRouter, public routes + /dashboard)\n2. /styles.css (SaaS design system, dark sidebar)\n3. /components/Sidebar.js (full sidebar nav with icons)\n4. /components/Header.js (top bar, user menu, notifications)",
            },
            {
                "name": "dashboard",
                "instruction": "Generate ONLY these files:\n1. /pages/Dashboard.js (metrics cards, charts with recharts, activity feed)\n2. /pages/Settings.js (profile form, billing section, API keys)\n3. /components/MetricCard.js (stat card with trend indicator)",
            },
            {
                "name": "public_pages",
                "instruction": "Generate ONLY these files:\n1. /pages/Home.js (marketing landing with hero, features, pricing)\n2. /pages/Login.js (login form with localStorage auth)\n3. /pages/Signup.js (signup form with validation)",
            },
        ]
    },
    "ai_agent": {
        "passes": [
            {
                "name": "scaffold",
                "instruction": "Generate ONLY these files:\n1. /App.js (chat interface layout)\n2. /styles.css (dark chat UI styles)\n3. /components/ChatInterface.js (message list, input, send button)\n4. /components/AgentCard.js (agent info card with status)",
            },
            {
                "name": "pages",
                "instruction": "Generate ONLY these files:\n1. /pages/Home.js (agent selection, available agents grid)\n2. /pages/Chat.js (full chat with agent, message history)\n3. /pages/AgentConfig.js (configure agent parameters)",
            },
        ]
    },
    "mobile": {
        "passes": [
            {
                "name": "scaffold",
                "instruction": "Generate ONLY these React Native / Expo files:\n1. /App.js (NavigationContainer, Stack navigator, all screens)\n2. /styles/theme.js (colors, typography, spacing constants)\n3. /components/Header.js (custom header with back button)\n4. /components/Card.js (reusable card component)",
            },
            {
                "name": "screens",
                "instruction": "Generate ONLY these screen files:\n1. /screens/HomeScreen.js (main screen with content)\n2. /screens/DetailScreen.js (detail view)\n3. /screens/ProfileScreen.js (user profile)\n4. /components/BottomTab.js (tab navigation)",
            },
        ]
    },
    "game": {
        "passes": [
            {
                "name": "scaffold",
                "instruction": "Generate ONLY these files:\n1. /App.js (game container, game loop)\n2. /styles.css (game canvas styles, dark theme)\n3. /components/GameCanvas.js (canvas rendering logic)\n4. /components/HUD.js (score, lives, level display)",
            },
            {
                "name": "game_logic",
                "instruction": "Generate ONLY these files:\n1. /game/GameEngine.js (game loop, collision detection)\n2. /game/Player.js (player class, movement, actions)\n3. /game/Entities.js (enemies, items, obstacles)\n4. /pages/Menu.js (main menu, high scores, start button)",
            },
        ]
    },
}

def get_build_structure(build_kind: str) -> dict:
    return BUILD_STRUCTURES.get(build_kind, BUILD_STRUCTURES["fullstack"])


def parse_files_from_response(text: str) -> Dict[str, str]:
    """Extract all ```lang:/path\ncode``` blocks from AI response."""
    pattern = r'```(?:jsx?|tsx?|css|html|ts|js)?:(/[\w./\-]+)\n([\s\S]*?)```'
    files = {}
    for match in re.finditer(pattern, text):
        path = match.group(1)
        code = match.group(2).strip()
        if code:
            files[path] = code
    # Fallback: plain ```jsx block → /App.js
    if not files:
        plain = re.findall(r'```(?:jsx?|tsx?)\n([\s\S]*?)```', text)
        if plain:
            files['/App.js'] = plain[0].strip()
    return files


async def run_iterative_build(
    prompt: str,
    build_kind: str,
    call_llm,  # async callable: (message, system) -> str
    on_progress=None,  # optional async callback(step_name, files_so_far)
) -> Dict[str, str]:
    """
    Run multi-turn iterative build.
    Returns dict of {filepath: code} for all generated files.
    """
    structure = get_build_structure(build_kind)
    passes = structure["passes"]
    all_files: Dict[str, str] = {}
    
    system = f"""You are CrucibAI, expert React developer building for Sandpack browser preview.
RULES:
- MemoryRouter ONLY (not BrowserRouter — breaks in iframes)
- Tailwind CSS classes only (loaded via CDN)
- lucide-react icons, framer-motion animations
- Real hardcoded data — NO Lorem ipsum, NO placeholder text
- NO fetch(), NO API calls, NO backend code
- COMPLETE code — no TODO, no truncation, no "// rest of code here"
- Every file must be fully implemented and ready to render

OUTPUT FORMAT — each file in its own fenced block:
```jsx:/path/to/File.js
// complete code here
```
```css:/styles.css
/* complete css here */
```"""

    for i, pass_info in enumerate(passes):
        step_name = pass_info["name"]
        instruction = pass_info["instruction"]
        
        # Build context from already-generated files
        context = ""
        if all_files:
            file_list = "\n".join(f"  - {p}" for p in sorted(all_files.keys()))
            # Include key files as context (App.js shows structure)
            key_files = ["/App.js", "/styles.css"]
            context_code = ""
            for kf in key_files:
                if kf in all_files:
                    context_code += f"\n\n// Already generated: {kf}\n{all_files[kf][:500]}...\n"
            context = f"\n\nFILES ALREADY GENERATED:\n{file_list}{context_code}\n\nGenerate ONLY the new files listed below. Import from already-generated files as needed."

        message = f"""Project: {prompt}
Build type: {build_kind}
Step {i+1}/{len(passes)}: {step_name.upper()}
{context}

{instruction}

Generate each file COMPLETELY — no truncation, no placeholders:"""

        try:
            logger.info(f"Iterative build step {i+1}/{len(passes)}: {step_name}")
            response = await call_llm(message, system)
            step_files = parse_files_from_response(response)
            
            if step_files:
                all_files.update(step_files)
                logger.info(f"Step {step_name}: generated {len(step_files)} files → total {len(all_files)}")
            else:
                logger.warning(f"Step {step_name}: no files parsed from response")
            
            if on_progress:
                await on_progress(step_name, dict(all_files))
                
        except Exception as e:
            logger.error(f"Iterative build step {step_name} failed: {e}")
            # Continue with next step even if one fails
            continue
    
    logger.info(f"Iterative build complete: {len(all_files)} total files")
    return all_files
