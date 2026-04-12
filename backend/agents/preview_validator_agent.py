"""
PreviewValidatorAgent: Catch build/preview issues BEFORE browser verification.

This agent:
1. THINKS about what could break in vite build or browser preview
2. VALIDATES generated code against common failure patterns
3. SUGGESTS FIXES before preview fails
4. RETURNS early errors so Build Validator can fix them

Used in: Phase 5 (before verification.preview step)
"""

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PreviewValidatorAgent:
    """Validate generated code before preview tries to run it."""

    def __init__(self):
        self.name = "Preview Validator Agent"
        self.version = "1.0"

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate the generated frontend app.

        Input context:
        - workspace_path: Path to generated app
        - package_json: package.json content
        - vite_config: vite.config.js content
        - src_files: dict of src/* files
        - index_html: index.html content

        Output:
        - status: "SUCCESS" or "ISSUES_FOUND"
        - critical_issues: Issues that block preview
        - warnings: Non-blocking issues
        - suggested_fixes: How to fix each issue
        """
        workspace_path = context.get("workspace_path")

        if not workspace_path or not os.path.exists(workspace_path):
            return {"status": "ERROR", "reason": "No workspace_path provided"}

        logger.info(f"Preview validation starting for {workspace_path}")

        # Phase 1: THINK about what could break
        thinking = await self._think_about_risks(context)

        # Phase 2: RUN validations in parallel
        validations = await asyncio.gather(
            self._validate_package_json(context),
            self._validate_vite_config(context),
            self._validate_imports(context),
            self._validate_jsx_syntax(context),
            self._validate_dependencies_exist(context),
            self._validate_entry_point(context),
            self._validate_export_statements(context),
        )

        # Phase 3: ANALYZE results
        critical_issues = [v for v in validations if v.get("critical")]
        warnings = [v for v in validations if not v.get("critical")]

        # Phase 4: SUGGEST fixes
        fixes = {}
        for issue in critical_issues:
            fix = await self._suggest_fix(issue, context)
            fixes[issue["file"]] = fix

        logger.info(
            f"Preview validation: {len(critical_issues)} critical, {len(warnings)} warnings"
        )

        return {
            "status": "SUCCESS" if not critical_issues else "ISSUES_FOUND",
            "critical_issues": critical_issues,
            "warnings": warnings,
            "suggested_fixes": fixes,
            "thinking": thinking,
            "total_files_checked": len(self._get_all_files(workspace_path)),
        }

    async def _think_about_risks(self, context: Dict) -> str:
        """THINKING PHASE: Analyze what could break."""
        return """
        Potential preview failures:
        1. Missing dependencies in package.json
        2. Broken import paths (@ alias not configured)
        3. Invalid JSX syntax (unclosed tags, bad props)
        4. Missing entry point (index.html, src/main.jsx)
        5. Circular dependencies
        6. Missing React import (if JSX used)
        7. Vite config issues (wrong paths, plugins)
        8. Assets not found
        9. Environment variables not set
        10. CSS/SCSS import issues
        """

    async def _validate_package_json(self, context: Dict) -> Dict[str, Any]:
        """Check package.json structure."""
        workspace = context.get("workspace_path")
        package_json_path = os.path.join(workspace, "package.json")

        if not os.path.exists(package_json_path):
            return {
                "file": "package.json",
                "critical": True,
                "issue": "package.json missing",
                "suggestion": "Create package.json with react, react-dom, vite dependencies",
            }

        try:
            with open(package_json_path) as f:
                pkg = json.load(f)
        except json.JSONDecodeError as e:
            return {
                "file": "package.json",
                "critical": True,
                "issue": f"Invalid JSON: {str(e)[:100]}",
                "suggestion": "Fix JSON syntax errors",
            }

        # Check critical fields
        issues = []

        if "dependencies" not in pkg and "devDependencies" not in pkg:
            issues.append("No dependencies defined")

        all_deps = {
            **(pkg.get("dependencies") or {}),
            **(pkg.get("devDependencies") or {}),
        }

        # React must be present if we're using JSX
        if "react" not in all_deps and self._has_jsx_files(workspace):
            issues.append("React not in dependencies but JSX files present")

        if "vite" not in all_deps:
            issues.append("Vite not in devDependencies")

        if issues:
            return {
                "file": "package.json",
                "critical": True,
                "issue": " | ".join(issues),
                "suggestion": "Add missing dependencies to package.json",
            }

        return {"file": "package.json", "critical": False, "issue": None}

    async def _validate_vite_config(self, context: Dict) -> Dict[str, Any]:
        """Check vite.config.js structure."""
        workspace = context.get("workspace_path")
        vite_path = os.path.join(workspace, "vite.config.js")

        if not os.path.exists(vite_path):
            return {
                "file": "vite.config.js",
                "critical": True,
                "issue": "vite.config.js missing",
                "suggestion": "Create basic vite.config.js with plugin:vue or @vitejs/plugin-react",
            }

        try:
            with open(vite_path) as f:
                config_content = f.read()
        except Exception as e:
            return {
                "file": "vite.config.js",
                "critical": True,
                "issue": f"Cannot read: {str(e)[:100]}",
                "suggestion": "Check file permissions",
            }

        # Check for basic structure
        if (
            "export default" not in config_content
            and "module.exports" not in config_content
        ):
            return {
                "file": "vite.config.js",
                "critical": True,
                "issue": "No export statement found",
                "suggestion": "Use 'export default { ... }'",
            }

        # Check for React plugin if JSX used
        if self._has_jsx_files(workspace):
            if (
                "@vitejs/plugin-react" not in config_content
                and "@vite/plugin-react" not in config_content
            ):
                return {
                    "file": "vite.config.js",
                    "critical": True,
                    "issue": "React plugin not configured but JSX files present",
                    "suggestion": "Add '@vitejs/plugin-react' to plugins",
                }

        return {"file": "vite.config.js", "critical": False, "issue": None}

    async def _validate_imports(self, context: Dict) -> Dict[str, Any]:
        """Check for broken import paths."""
        workspace = context.get("workspace_path")
        src_path = os.path.join(workspace, "src")

        if not os.path.exists(src_path):
            return {
                "file": "src/",
                "critical": True,
                "issue": "src directory missing",
                "suggestion": "Create src/ directory with main.jsx or index.jsx",
            }

        # Find all JS/JSX files
        js_files = self._find_files(src_path, [".js", ".jsx", ".ts", ".tsx"])

        broken_imports = []

        for js_file in js_files:
            with open(js_file) as f:
                content = f.read()

            # Check for @ imports without alias config
            if re.search(r"from\s+['\"]@/", content):
                vite_config = os.path.join(workspace, "vite.config.js")
                if os.path.exists(vite_config):
                    with open(vite_config) as f:
                        vite_content = f.read()
                    if "resolve" not in vite_content or "@" not in vite_content:
                        broken_imports.append(
                            f"{os.path.basename(js_file)}: @ alias used but not configured"
                        )

            # Check for excessive relative path depth (3+ levels = likely wrong).
            # One or two levels (../ or ../../) are normal in pages/components.
            if re.search(r"from\s+['\"](\.\./)\1\1", content):
                broken_imports.append(
                    f"{os.path.basename(js_file)}: Too many ../ in import path"
                )

        if broken_imports:
            return {
                "file": "src/",
                "critical": True,
                "issue": " | ".join(broken_imports[:3]),
                "suggestion": "Fix import paths or configure vite aliases",
            }

        return {"file": "src/", "critical": False, "issue": None}

    async def _validate_jsx_syntax(self, context: Dict) -> Dict[str, Any]:
        """Check for basic JSX syntax errors."""
        workspace = context.get("workspace_path")
        src_path = os.path.join(workspace, "src")

        jsx_files = self._find_files(src_path, [".jsx", ".tsx"])

        syntax_errors = []

        for jsx_file in jsx_files:
            with open(jsx_file) as f:
                content = f.read()

            # Check for unclosed JSX tags — only flag clearly broken syntax.
            # Self-closing tags (<Foo />) and React fragments (<> </>) are valid,
            # so we strip them before counting to avoid false positives.
            stripped = re.sub(
                r"<[A-Z]\w*[^>]*/\s*>", "", content
            )  # remove self-closing
            stripped = re.sub(r"<>|</>", "", stripped)  # remove fragments
            open_tags = len(re.findall(r"<[A-Z]\w*(?:\s[^>]*)?>", stripped))
            close_tags = len(re.findall(r"</[A-Z]\w*>", stripped))
            # Allow ±2 tolerance for HOC/portal patterns
            if abs(open_tags - close_tags) > 2:
                syntax_errors.append(
                    f"{os.path.basename(jsx_file)}: Unmatched JSX tags"
                )

        if syntax_errors:
            return {
                "file": "src/",
                "critical": True,
                "issue": " | ".join(syntax_errors[:3]),
                "suggestion": "Fix JSX syntax errors",
            }

        return {"file": "src/", "critical": False, "issue": None}

    async def _validate_dependencies_exist(self, context: Dict) -> Dict[str, Any]:
        """Check that imported packages are in package.json."""
        workspace = context.get("workspace_path")
        package_json_path = os.path.join(workspace, "package.json")
        src_path = os.path.join(workspace, "src")

        if not os.path.exists(package_json_path):
            return {"file": "package.json", "critical": False, "issue": None}

        with open(package_json_path) as f:
            pkg = json.load(f)

        all_deps = {
            **(pkg.get("dependencies") or {}),
            **(pkg.get("devDependencies") or {}),
        }

        # Find all imports
        js_files = self._find_files(src_path, [".js", ".jsx", ".ts", ".tsx"])

        missing_deps = []

        for js_file in js_files:
            with open(js_file) as f:
                content = f.read()

            # Find: from 'package-name'
            imports = re.findall(r"from\s+['\"]([^/'\"]+)['\"]", content)

            for imp in imports:
                # Skip relative imports and @ alias
                if imp.startswith(".") or imp.startswith("@"):
                    continue

                # Get root package name (lodash/map -> lodash)
                root_pkg = imp.split("/")[0]

                if (
                    root_pkg not in all_deps
                    and root_pkg != "react"
                    and root_pkg != "react-dom"
                ):
                    missing_deps.append(f"{imp}")

        if missing_deps:
            return {
                "file": "package.json",
                "critical": True,
                "issue": f"Missing dependencies: {', '.join(set(missing_deps)[:3])}",
                "suggestion": "Add missing packages to package.json dependencies",
            }

        return {"file": "package.json", "critical": False, "issue": None}

    async def _validate_entry_point(self, context: Dict) -> Dict[str, Any]:
        """Check that entry point exists."""
        workspace = context.get("workspace_path")

        # Check index.html
        index_html = os.path.join(workspace, "index.html")
        if not os.path.exists(index_html):
            return {
                "file": "index.html",
                "critical": True,
                "issue": "index.html missing",
                "suggestion": "Create index.html with <div id='root'></div>",
            }

        with open(index_html) as f:
            html_content = f.read()

        if "<div" not in html_content or "id=" not in html_content:
            return {
                "file": "index.html",
                "critical": True,
                "issue": "No root div found in index.html",
                "suggestion": "Add <div id='root'></div> to index.html body",
            }

        return {"file": "index.html", "critical": False, "issue": None}

    async def _validate_export_statements(self, context: Dict) -> Dict[str, Any]:
        """Check main.jsx/index.jsx exports."""
        workspace = context.get("workspace_path")
        src_path = os.path.join(workspace, "src")

        main_file = None
        for fname in ["main.jsx", "index.jsx", "main.js", "index.js"]:
            fpath = os.path.join(src_path, fname)
            if os.path.exists(fpath):
                main_file = fpath
                break

        if not main_file:
            return {
                "file": "src/",
                "critical": True,
                "issue": "No src/main.jsx or src/index.jsx found",
                "suggestion": "Create src/main.jsx with ReactDOM.render() or createRoot()",
            }

        with open(main_file) as f:
            content = f.read()

        if "ReactDOM" not in content and "createRoot" not in content:
            return {
                "file": os.path.basename(main_file),
                "critical": True,
                "issue": "No ReactDOM or createRoot call found",
                "suggestion": "Add ReactDOM.render() or createRoot() to mount React app",
            }

        return {"file": os.path.basename(main_file), "critical": False, "issue": None}

    async def _suggest_fix(self, issue: Dict, context: Dict) -> str:
        """Suggest a fix for an issue."""
        issue_type = issue.get("issue", "")

        if "package.json missing" in issue_type:
            return """Create package.json:
{
  "name": "generated-app",
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0"
  }
}"""

        elif "vite.config.js missing" in issue_type:
            return """Create vite.config.js:
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
})"""

        elif "React plugin not configured" in issue_type:
            return """Add to vite.config.js:
import react from '@vitejs/plugin-react'

export default {
  plugins: [react()],
}"""

        elif "@ alias used" in issue_type:
            return """Add to vite.config.js resolve:
resolve: {
  alias: {
    '@': '/src',
  },
}"""

        else:
            return "Review error message and fix accordingly"

    # Helper methods

    def _has_jsx_files(self, workspace: str) -> bool:
        """Check if JSX files exist."""
        src_path = os.path.join(workspace, "src")
        if not os.path.exists(src_path):
            return False

        for root, dirs, files in os.walk(src_path):
            for f in files:
                if f.endswith((".jsx", ".tsx")):
                    return True
        return False

    def _find_files(self, directory: str, extensions: List[str]) -> List[str]:
        """Find all files with given extensions."""
        files = []
        if not os.path.exists(directory):
            return files

        for root, dirs, filenames in os.walk(directory):
            for f in filenames:
                if any(f.endswith(ext) for ext in extensions):
                    files.append(os.path.join(root, f))
        return files

    def _get_all_files(self, directory: str) -> List[str]:
        """Get all files in directory."""
        files = []
        for root, dirs, filenames in os.walk(directory):
            for f in filenames:
                files.append(os.path.join(root, f))
        return files
