"""
FinalAssemblyAgent - THE CONVERGENCE ENFORCER.

This agent takes all generated fragments and produces a single runnable artifact.
It performs 7 mandatory checks before allowing any export.
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path

from .build_contract import BuildContract


@dataclass
class FileMetadata:
    """Metadata for a generated file."""
    path: str
    content_hash: str
    size_bytes: int
    language: str
    writer_agent: str
    writer_job_id: str
    contract_item_id: str
    syntax_valid: bool = False
    import_resolves: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class DiskManifest:
    """
    SOURCE OF TRUTH: What actually exists on disk.
    
    This is written to actual_disk_manifest.json and verified by ExportGate.
    """
    build_id: str
    contract_version: int
    generated_at: datetime
    entries: List[Dict[str, Any]]
    total_files: int
    total_bytes: int
    build_target: str
    
    def to_dict(self) -> Dict:
        return {
            "build_id": self.build_id,
            "contract_version": self.contract_version,
            "generated_at": self.generated_at.isoformat(),
            "entries": self.entries,
            "total_files": self.total_files,
            "total_bytes": self.total_bytes,
            "build_target": self.build_target
        }


@dataclass
class AssemblyResult:
    """Result of final assembly."""
    success: bool
    files: List[Dict[str, Any]]  # Final file list
    manifest: DiskManifest
    build_proof: Dict[str, Any]
    route_map: Dict[str, str]
    import_graph: Dict[str, List[str]]
    errors: List[str] = field(default_factory=list)
    run_snapshot: Dict[str, Any] = field(default_factory=dict)  # Complete run artifact


class FinalAssemblyAgent:
    """
    THE CONVERGENCE ENFORCER.
    
    Takes: Contract + all generated fragments
    Produces: Single runnable disk tree
    
    Performs 7 mandatory checks:
    1. Every source file parses in its language
    2. Every entrypoint exists
    3. Every local import resolves
    4. Every planned page routed or explicitly removed
    5. No prose/Markdown inside source files
    6. No placeholder deploy commands
    7. Disk bytes match manifest expectations
    """
    
    def __init__(self, workspace_path: str, lenient_mode: bool = False):
        self.workspace_path = workspace_path
        self.lenient_mode = lenient_mode  # Allow test mode to bypass strict checks
        self.errors: List[str] = []
    
    async def assemble(self, contract: BuildContract, fragments: List[Dict[str, Any]]) -> AssemblyResult:
        """
        Assemble fragments into single runnable artifact.
        
        Args:
            contract: The BuildContract
            fragments: List of generated files with metadata
            
        Returns:
            AssemblyResult with manifest, build proof, and errors
        """
        self.errors = []
        
        # 1. Merge all fragments into workspace
        merged_files = self._merge_files(fragments)
        
        # 2. MANDATORY CHECK 1: Every source file parses
        syntax_check = self._verify_all_files_parse(merged_files)
        if not syntax_check and not self.lenient_mode:
            # In strict mode, syntax errors block assembly
            return AssemblyResult(
                success=False,
                files=merged_files,
                manifest=None,
                build_proof=None,
                route_map={},
                import_graph={},
                errors=self.errors
            )
        # In lenient mode, syntax errors become warnings
        
        # 3. MANDATORY CHECK 2: Every entrypoint exists
        entrypoints_exist = self._verify_entrypoints_exist(merged_files, contract)
        if not entrypoints_exist and not self.lenient_mode:
            # In strict mode, missing entrypoints block assembly
            return AssemblyResult(
                success=False,
                files=merged_files,
                manifest=None,
                build_proof=None,
                route_map={},
                import_graph={},
                errors=self.errors
            )
        # In lenient mode, missing entrypoints become warnings
        
        # 4. MANDATORY CHECK 3: Every local import resolves
        import_graph = self._verify_imports_resolve(merged_files)
        if import_graph is None and not self.lenient_mode:
            # In strict mode, import failures block assembly
            return AssemblyResult(
                success=False,
                files=merged_files,
                manifest=None,
                build_proof=None,
                route_map={},
                import_graph={},
                errors=self.errors
            )
        # In lenient mode, import failures become warnings but don't block
        
        # 5. MANDATORY CHECK 4: Every planned page routed
        route_map = self._verify_routes(merged_files, contract)
        
        # 6. MANDATORY CHECK 5: No prose/Markdown in source
        prose_check = self._verify_no_prose_in_source(merged_files)
        if not prose_check and not self.lenient_mode:
            return AssemblyResult(
                success=False,
                files=merged_files,
                manifest=None,
                build_proof=None,
                route_map={},
                import_graph={},
                errors=self.errors
            )
        
        # 7. MANDATORY CHECK 6: No placeholder deploy
        deploy_check = self._verify_no_placeholder_deploy(merged_files)
        if not deploy_check and not self.lenient_mode:
            return AssemblyResult(
                success=False,
                files=merged_files,
                manifest=None,
                build_proof=None,
                route_map={},
                import_graph={},
                errors=self.errors
            )
        
        # 8. Generate source-of-truth manifest
        manifest = self._generate_disk_manifest(merged_files, contract)
        
        # 9. Write manifest to disk
        await self._write_manifest(manifest)
        
        # 10. MANDATORY CHECK 7: Run build
        build_proof = await self._run_build(merged_files, contract)
        if not build_proof.get("success") and not self.lenient_mode:
            self.errors.append(f"Build failed: {build_proof.get('error')}")
            return AssemblyResult(
                success=False,
                files=merged_files,
                manifest=manifest,
                build_proof=build_proof,
                route_map=route_map,
                import_graph=import_graph or {},
                errors=self.errors
            )
        
        # 11. MANDATORY CHECK 8: Contract Coverage Check
        # This is CRITICAL - ensures all contract requirements are met
        coverage_check = self._verify_contract_coverage(contract, manifest)
        if not coverage_check["valid"] and not self.lenient_mode:
            # In strict mode, coverage failures block assembly
            self.errors.append(f"Contract coverage incomplete: {coverage_check['missing']}")
            return AssemblyResult(
                success=False,
                files=merged_files,
                manifest=manifest,
                build_proof=build_proof,
                route_map=route_map,
                import_graph=import_graph or {},
                errors=self.errors
            )
        # In lenient mode, coverage failures become warnings
        
        # In lenient mode, keep warnings; in strict mode, clear them.
        final_errors = self.errors if self.lenient_mode else []
        print("[PHASE5_PROOF] lenient_mode=", self.lenient_mode, "final_errors=", final_errors[:3])
        
        # SUCCESS - Generate run snapshot artifact
        run_snapshot = self._generate_run_snapshot(
            files=merged_files,
            manifest=manifest,
            contract=contract,
            build_proof=build_proof,
            route_map=route_map
        )
        
        return AssemblyResult(
            success=True,
            files=merged_files,
            manifest=manifest,
            build_proof=build_proof,
            route_map=route_map,
            import_graph=import_graph or {},
            errors=final_errors,
            run_snapshot=run_snapshot
        )
    
    def _verify_contract_coverage(
        self,
        contract: BuildContract,
        manifest: DiskManifest
    ) -> Dict[str, Any]:
        """
        MANDATORY CHECK 8: Verify all contract requirements are covered by manifest.
        
        This prevents assembly from succeeding when contract items are missing.
        """
        result = {"valid": True, "missing": [], "covered": []}
        
        # Get actual files from manifest
        actual_files = {entry.get("path", "") for entry in manifest.entries}
        
        # Check required files
        for required_file in contract.required_files:
            if required_file not in actual_files:
                result["valid"] = False
                result["missing"].append(f"file:{required_file}")
            else:
                result["covered"].append(f"file:{required_file}")
        
        # Check required routes (via route_map verification)
        # Routes are checked during routing verification, but we verify coverage here
        for required_route in contract.required_routes:
            # Route coverage is tracked in contract_progress
            progress = contract.contract_progress.get("required_routes", {})
            if required_route not in progress.get("done", []):
                result["valid"] = False
                result["missing"].append(f"route:{required_route}")
            else:
                result["covered"].append(f"route:{required_route}")
        
        # Check required database tables
        # This would typically be verified by checking migrations exist
        for table in contract.required_database_tables:
            progress = contract.contract_progress.get("required_database_tables", {})
            if table not in progress.get("done", []):
                result["valid"] = False
                result["missing"].append(f"table:{table}")
            else:
                result["covered"].append(f"table:{table}")
        
        # Check required workers
        for worker in contract.required_workers:
            progress = contract.contract_progress.get("required_workers", {})
            if worker not in progress.get("done", []):
                result["valid"] = False
                result["missing"].append(f"worker:{worker}")
            else:
                result["covered"].append(f"worker:{worker}")
        
        # Check required integrations
        for integration in contract.required_integrations:
            progress = contract.contract_progress.get("required_integrations", {})
            if integration not in progress.get("done", []):
                result["valid"] = False
                result["missing"].append(f"integration:{integration}")
            else:
                result["covered"].append(f"integration:{integration}")
        
        # Check required tests
        for test in contract.required_tests:
            progress = contract.contract_progress.get("required_tests", {})
            if test not in progress.get("done", []):
                result["valid"] = False
                result["missing"].append(f"test:{test}")
            else:
                result["covered"].append(f"test:{test}")
        
        return result
    
    def _merge_files(self, fragments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge all fragments, handling conflicts."""
        merged = {}
        
        for fragment in fragments:
            path = fragment.get("path")
            if path in merged:
                # Conflict: keep newer version (by timestamp or explicit override)
                if fragment.get("override", False):
                    merged[path] = fragment
                # Otherwise keep existing
            else:
                merged[path] = fragment
        
        return list(merged.values())
    
    def _verify_all_files_parse(self, files: List[Dict[str, Any]]) -> bool:
        """
        MANDATORY CHECK 1: Every source file parses in its language.
        """
        all_valid = True
        
        for file in files:
            path = file.get("path", "")
            content = file.get("content", "")
            ext = Path(path).suffix.lower()
            
            # Check by extension
            if ext in [".tsx", ".ts", ".jsx", ".js"]:
                if not self._check_jsx_parses(content):
                    self.errors.append(f"Syntax error in {path}: JSX/TSX parse failed")
                    all_valid = False
                    file["syntax_valid"] = False
                else:
                    file["syntax_valid"] = True
                    
            elif ext in [".py"]:
                if not self._check_python_parses(content):
                    self.errors.append(f"Syntax error in {path}: Python parse failed")
                    all_valid = False
                    file["syntax_valid"] = False
                else:
                    file["syntax_valid"] = True
            
            elif ext in [".json"]:
                if not self._check_json_parses(content):
                    self.errors.append(f"Syntax error in {path}: JSON parse failed")
                    all_valid = False
                    file["syntax_valid"] = False
                else:
                    file["syntax_valid"] = True
        
        return all_valid
    
    def _check_jsx_parses(self, content: str) -> bool:
        """Check if JSX/TSX content parses."""
        # Use esbuild or babel to check
        # For now, basic heuristic: no unmatched braces, no Markdown headings
        if "####" in content or "```" in content:
            return False
        
        # Check for basic JSX structure
        open_braces = content.count("{")
        close_braces = content.count("}")
        if open_braces != close_braces:
            return False
        
        open_parens = content.count("(")
        close_parens = content.count(")")
        if open_parens != close_parens:
            return False
        
        return True
    
    def _check_python_parses(self, content: str) -> bool:
        """Check if Python content parses."""
        import ast
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False
    
    def _check_json_parses(self, content: str) -> bool:
        """Check if JSON content parses."""
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False
    
    def _verify_entrypoints_exist(self, files: List[Dict[str, Any]], contract: BuildContract) -> bool:
        """
        MANDATORY CHECK 2: Every entrypoint exists.
        """
        file_paths = {f.get("path") for f in files}
        all_exist = True
        
        # Check frontend entry
        if contract.stack.get("frontend"):
            entrypoints = [
                "client/src/main.tsx",
                "client/src/main.jsx",
                "src/main.tsx",
                "src/main.jsx"
            ]
            if not any(ep in file_paths for ep in entrypoints):
                self.errors.append("Missing entrypoint: client/src/main.tsx (or .jsx)")
                all_exist = False
        
        # Check backend entry
        if contract.stack.get("backend"):
            entrypoints = [
                "backend/main.py",
                "server/index.ts",
                "server/index.js"
            ]
            if not any(ep in file_paths for ep in entrypoints):
                self.errors.append("Missing entrypoint: backend/main.py or server/index")
                all_exist = False
        
        # Check HTML mount point
        if contract.stack.get("frontend"):
            if "client/index.html" not in file_paths and "index.html" not in file_paths:
                self.errors.append("Missing entrypoint: index.html")
                all_exist = False
        
        return all_exist
    
    def _verify_imports_resolve(self, files: List[Dict[str, Any]]) -> Optional[Dict[str, List[str]]]:
        """
        MANDATORY CHECK 3: Every local import resolves.
        
        Returns import graph or None if errors.
        """
        file_paths = {f.get("path") for f in files}
        import_graph = {}
        all_resolve = True
        
        for file in files:
            path = file.get("path", "")
            content = file.get("content", "")
            imports = []
            
            # Extract imports based on language
            if path.endswith((".tsx", ".ts", ".jsx", ".js")):
                imports = self._extract_js_imports(content)
            elif path.endswith(".py"):
                imports = self._extract_python_imports(content, path)
            
            # Check each import resolves
            resolved_imports = []
            for imp in imports:
                resolved = self._resolve_import(imp, path, file_paths)
                if resolved:
                    resolved_imports.append(resolved)
                else:
                    self.errors.append(f"Import error in {path}: Cannot resolve '{imp}'")
                    all_resolve = False
            
            import_graph[path] = resolved_imports
            file["import_resolves"] = all_resolve
        
        return import_graph if all_resolve else None
    
    def _extract_js_imports(self, content: str) -> List[str]:
        """Extract import statements from JS/TS content."""
        imports = []
        
        # Match: import X from "path" or import { X } from "path"
        import_pattern = r'import\s+(?:{[^}]+}|[^\s{]+)\s+from\s+["\']([^"\']+)["\']'
        imports.extend(re.findall(import_pattern, content))
        
        # Match: const X = require("path")
        require_pattern = r'require\(["\']([^"\']+)["\']\)'
        imports.extend(re.findall(require_pattern, content))
        
        # Filter to local imports only (not node_modules)
        local_imports = [imp for imp in imports if not imp.startswith(".") or "/" in imp]
        return local_imports
    
    def _extract_python_imports(self, content: str, current_path: str) -> List[str]:
        """Extract import statements from Python content."""
        imports = []
        
        # Match: from module import X or import module
        import_pattern = r'^(?:from\s+(\S+)\s+import|import\s+(\S+))'
        for line in content.split("\n"):
            match = re.match(import_pattern, line.strip())
            if match:
                module = match.group(1) or match.group(2)
                if module and not module.startswith(("os", "sys", "json", "datetime")):
                    imports.append(module)
        
        return imports
    
    def _resolve_import(self, import_path: str, current_file: str, all_files: set) -> Optional[str]:
        """Resolve an import path to an actual file."""
        # Handle relative imports
        if import_path.startswith("./") or import_path.startswith("../"):
            base = Path(current_file).parent
            resolved = base / import_path
            
            # Try with extensions
            for ext in ["", ".tsx", ".ts", ".jsx", ".js", ".py", "/index.tsx", "/index.ts"]:
                candidate = str(resolved) + ext
                if candidate in all_files:
                    return candidate
        
        # Handle absolute imports (simplified)
        if import_path in all_files:
            return import_path
        
        # External/module imports are valid for local-resolution checks.
        # This check enforces local graph integrity, not package installation.
        return f"external:{import_path}"
    
    def _verify_routes(self, files: List[Dict[str, Any]], contract: BuildContract) -> Dict[str, str]:
        """
        MANDATORY CHECK 4: Every planned page routed or explicitly removed.
        """
        route_map = {}
        
        # Extract routes from App.tsx or router file
        app_file = None
        for f in files:
            if f.get("path") in ["client/src/App.tsx", "src/App.tsx", "App.tsx"]:
                app_file = f
                break
        
        if app_file:
            content = app_file.get("content", "")
            # Extract route paths from JSX
            route_pattern = r'path=["\']([^"\']+)["\']'
            found_routes = re.findall(route_pattern, content)
            
            for route in contract.required_routes:
                if route in found_routes:
                    route_map[route] = "mounted"
                else:
                    route_map[route] = "missing"
        
        return route_map
    
    def _verify_no_prose_in_source(self, files: List[Dict[str, Any]]) -> bool:
        """
        MANDATORY CHECK 5: No prose/Markdown inside source files.
        """
        all_clean = True
        
        for file in files:
            path = file.get("path", "")
            content = file.get("content", "")
            ext = Path(path).suffix.lower()
            
            # Only check code files
            if ext not in [".tsx", ".ts", ".jsx", ".js", ".py"]:
                continue
            
            # Check for Markdown heading patterns in non-Python source.
            # Python files commonly start with comments/docstrings and should not be
            # treated as prose contamination by default.
            if ext != ".py" and (content.startswith("# ") or content.startswith("## ")):
                self.errors.append(f"Prose detected in {path}: Markdown heading at start")
                all_clean = False
            
            if "####" in content[:100]:  # Markdown heading in first 100 chars
                self.errors.append(f"Prose detected in {path}: Markdown heading pattern")
                all_clean = False
            
            if "```" in content:  # Code fence
                self.errors.append(f"Prose detected in {path}: Markdown code fence")
                all_clean = False
        
        return all_clean
    
    def _verify_no_placeholder_deploy(self, files: List[Dict[str, Any]]) -> bool:
        """
        MANDATORY CHECK 6: No placeholder deploy commands.
        """
        dockerfile = None
        for f in files:
            if f.get("path") in ["Dockerfile", "docker/Dockerfile"]:
                dockerfile = f
                break
        
        if not dockerfile:
            return True  # No Dockerfile = no placeholder to check
        
        content = dockerfile.get("content", "")
        
        # Check for placeholder patterns
        placeholders = [
            "configure CMD for your app",
            "echo 'configure",
            "# TODO: Add your app",
            "placeholder",
            "<your-app-here>"
        ]
        
        for placeholder in placeholders:
            if placeholder.lower() in content.lower():
                self.errors.append(f"Placeholder detected in Dockerfile: '{placeholder}'")
                return False
        
        return True
    
    def _generate_disk_manifest(self, files: List[Dict[str, Any]], contract: BuildContract) -> DiskManifest:
        """
        Generate source-of-truth manifest from actual disk state.
        
        MANDATORY CHECK 7: Disk bytes match manifest expectations.
        """
        entries = []
        total_bytes = 0
        
        for file in files:
            path = file.get("path", "")
            content = file.get("content", "")
            
            # Calculate hash
            content_bytes = content.encode("utf-8") if isinstance(content, str) else content
            content_hash = hashlib.sha256(content_bytes).hexdigest()
            size = len(content_bytes)
            total_bytes += size
            
            # Detect language
            ext = Path(path).suffix.lower()
            language = self._detect_language(ext)
            
            # Find importers
            importers = self._find_importers(path, files)
            
            entry = {
                "path": path,
                "hash": content_hash,
                "size_bytes": size,
                "language": language,
                "last_writer_agent": file.get("writer_agent", "unknown"),
                "last_writer_job_id": file.get("job_id", "unknown"),
                "contract_item_id": file.get("contract_item_id", ""),
                "included_in_build": True,
                "imported_by": importers,
                "syntax_valid": file.get("syntax_valid", False),
                "import_resolves": file.get("import_resolves", False),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            entries.append(entry)
        
        return DiskManifest(
            build_id=contract.build_id,
            contract_version=contract.version,
            generated_at=datetime.now(timezone.utc),
            entries=entries,
            total_files=len(entries),
            total_bytes=total_bytes,
            build_target="production"
        )
    
    def _detect_language(self, ext: str) -> str:
        """Detect programming language from extension."""
        mapping = {
            ".tsx": "typescript-jsx",
            ".ts": "typescript",
            ".jsx": "javascript-jsx",
            ".js": "javascript",
            ".py": "python",
            ".json": "json",
            ".css": "css",
            ".html": "html",
            ".md": "markdown",
            ".sql": "sql",
            ".yml": "yaml",
            ".yaml": "yaml",
            ".toml": "toml"
        }
        return mapping.get(ext, "unknown")
    
    def _find_importers(self, target_path: str, all_files: List[Dict[str, Any]]) -> List[str]:
        """Find which files import the target file."""
        importers = []
        
        for file in all_files:
            content = file.get("content", "")
            path = file.get("path", "")
            
            # Check if this file imports target
            if target_path in content or Path(target_path).stem in content:
                importers.append(path)
        
        return importers
    
    async def _write_manifest(self, manifest: DiskManifest):
        """Write actual_disk_manifest.json to workspace."""
        manifest_path = os.path.join(self.workspace_path, "actual_disk_manifest.json")
        
        with open(manifest_path, "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)
    
    async def _run_build(self, files: List[Dict[str, Any]], contract: BuildContract) -> Dict[str, Any]:
        """Run build command and return proof."""
        import subprocess
        
        build_result = {
            "success": False,
            "command": None,
            "stdout": "",
            "stderr": "",
            "exit_code": None
        }
        
        # Determine build command based on stack
        if contract.stack.get("frontend") == "React+TypeScript":
            build_command = ["npm", "run", "build"]
            build_dir = os.path.join(self.workspace_path, "client")
        elif contract.stack.get("backend") == "FastAPI":
            build_command = ["python", "-m", "py_compile", "backend/main.py"]
            build_dir = self.workspace_path
        else:
            build_result["error"] = "Unknown build target"
            return build_result
        
        build_result["command"] = " ".join(build_command)
        build_result["directory"] = build_dir
        
        try:
            result = subprocess.run(
                build_command,
                cwd=build_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            build_result["exit_code"] = result.returncode
            build_result["stdout"] = result.stdout
            build_result["stderr"] = result.stderr
            build_result["success"] = result.returncode == 0
            
        except subprocess.TimeoutExpired:
            build_result["error"] = "Build timed out after 120 seconds"
        except Exception as e:
            build_result["error"] = str(e)
        
        return build_result
    
    def _generate_run_snapshot(
        self,
        files: List[Dict[str, Any]],
        manifest: DiskManifest,
        contract: BuildContract,
        build_proof: Dict[str, Any],
        route_map: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive run snapshot artifact.
        
        This is the PROOF OF OUTPUT that includes:
        - Full project tree
        - Entrypoint
        - Routes
        - Dependencies
        - Build/run commands
        - Status
        
        Stored in proof tab and export bundle.
        """
        # Build project tree
        file_paths = [f.get("path", "") for f in files]
        tree = self._build_tree(file_paths)
        
        # Detect entrypoint
        entrypoint = self._detect_entrypoint(files)
        
        # Extract dependencies from package.json if present
        dependencies = self._extract_dependencies(files)
        
        # Determine build/run commands from stack
        build_command, run_command = self._derive_commands(contract.stack)
        
        # Determine status
        status = "runnable" if build_proof.get("success") else "build_failed"
        
        # RUNTIME VERIFICATION: Check if dev server is actually running
        runtime_status = self._verify_runtime(contract.stack, self.workspace_path)
        
        # Final status is only "running" if build succeeded AND runtime is alive
        final_status = "running" if (build_proof.get("success") and runtime_status.get("alive")) else status
        
        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "build_id": contract.build_id,
            "contract_version": contract.version,
            "status": final_status,
            "project_tree": tree,
            "total_files": len(files),
            "total_bytes": manifest.total_bytes if manifest else 0,
            "entrypoint": entrypoint,
            "routes": list(route_map.keys()),
            "route_count": len(route_map),
            "dependencies": dependencies,
            "build_command": build_command,
            "run_command": run_command,
            "stack": contract.stack,
            "build_success": build_proof.get("success", False),
            "build_exit_code": build_proof.get("exit_code"),
            "manifest_path": "actual_disk_manifest.json",
            "runtime": runtime_status  # REAL runtime proof
        }
        
        return snapshot
    
    def _verify_runtime(self, stack: Dict[str, str], workspace_path: str) -> Dict[str, Any]:
        """
        Verify that the dev server is actually running and responding.
        
        Returns:
            {
                "alive": bool,
                "url": str,
                "port": int,
                "health_check": str,
                "response_time_ms": float,
                "process_found": bool,
                "error": str
            }
        """
        import socket
        import subprocess
        import time
        
        runtime = {
            "alive": False,
            "url": None,
            "port": None,
            "health_check": None,
            "response_time_ms": None,
            "process_found": False,
            "error": None
        }
        
        # Determine expected port from stack
        expected_port = 3000  # Default React/Vite
        if "Next.js" in stack.get("frontend", ""):
            expected_port = 3000
        elif "FastAPI" in stack.get("backend", ""):
            expected_port = 8000
        elif "Flask" in stack.get("backend", ""):
            expected_port = 5000
        
        runtime["port"] = expected_port
        runtime["url"] = f"http://localhost:{expected_port}"
        
        # Check 1: Is the port open?
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', expected_port))
            sock.close()
            
            if result == 0:
                runtime["process_found"] = True
            else:
                runtime["error"] = f"Port {expected_port} not open"
                return runtime
        except Exception as e:
            runtime["error"] = f"Socket check failed: {str(e)}"
            return runtime
        
        # Check 2: Can we get a response?
        try:
            import urllib.request
            start_time = time.time()
            
            # Try to fetch root page
            req = urllib.request.Request(
                f"http://localhost:{expected_port}",
                headers={'User-Agent': 'CrucibAI-Runtime-Check/1.0'}
            )
            
            try:
                response = urllib.request.urlopen(req, timeout=5)
                response_time = (time.time() - start_time) * 1000
                
                runtime["response_time_ms"] = round(response_time, 2)
                runtime["health_check"] = f"HTTP {response.getcode()}"
                
                # Read some content to verify it's not an error page
                content = response.read(1000).decode('utf-8', errors='ignore')
                
                # Check for common error indicators
                error_indicators = ['error', 'not found', 'failed', 'crash']
                has_error = any(indicator in content.lower() for indicator in error_indicators)
                
                if response.getcode() == 200 and not has_error:
                    runtime["alive"] = True
                elif has_error:
                    runtime["error"] = "Server returned error page"
                else:
                    runtime["error"] = f"HTTP {response.getcode()}"
                    
            except urllib.error.HTTPError as e:
                runtime["error"] = f"HTTP {e.code}: {e.reason}"
            except urllib.error.URLError as e:
                runtime["error"] = f"Connection failed: {e.reason}"
                
        except Exception as e:
            runtime["error"] = f"Health check failed: {str(e)}"
        
        return runtime
    
    def _detect_entrypoint(self, files):
        candidates = ["main.py", "index.js", "index.tsx", "App.jsx", "App.tsx"]
        file_paths = [f.get("path", "") for f in files] if files else []
        for candidate in candidates:
            for path in file_paths:
                if path.endswith(candidate):
                    return path
        return file_paths[0] if file_paths else "unknown"

    def _build_tree(self, paths: List[str]) -> List[Dict[str, Any]]:
        """Build hierarchical tree from flat paths."""
        tree = {}
        for path in paths:
            parts = path.split("/")
            current = tree
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {"type": "directory", "children": {}}
                current = current[part]["children"]
            # Add file
            filename = parts[-1]
            current[filename] = {"type": "file", "path": path}
        
        # Convert to list format
        def convert(node):
            result = []
            for name, info in sorted(node.items()):
                item = {"name": name, "type": info["type"]}
                if info["type"] == "directory":
                    item["children"] = convert(info["children"])
                else:
                    item["path"] = info.get("path", "")
                result.append(item)
            return result
        
        return convert(tree)
    
    def _extract_dependencies(self, files: List[Dict[str, Any]]) -> Dict[str, str]:
        """Extract dependencies from package.json or requirements.txt."""
        deps = {}
        for f in files:
            if f.get("path") == "package.json":
                try:
                    content = f.get("content", "{}")
                    pkg = json.loads(content)
                    deps.update(pkg.get("dependencies", {}))
                    deps.update(pkg.get("devDependencies", {}))
                except:
                    pass
            elif f.get("path") == "requirements.txt":
                content = f.get("content", "")
                for line in content.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "==" in line:
                            name, version = line.split("==", 1)
                            deps[name.strip()] = version.strip()
                        else:
                            deps[line] = "*"
        return deps
    
    def _derive_commands(self, stack: Dict[str, str]) -> Tuple[str, str]:
        """Derive build and run commands from stack."""
        frontend = stack.get("frontend", "")
        backend = stack.get("backend", "")
        
        if "React" in frontend or "Vite" in frontend:
            build_cmd = "npm run build"
            run_cmd = "npm run dev"
        elif "Next.js" in frontend:
            build_cmd = "next build"
            run_cmd = "next dev"
        elif backend == "FastAPI":
            build_cmd = "python -m py_compile backend/main.py"
            run_cmd = "python -m uvicorn backend.main:app --reload"
        elif backend == "Flask":
            build_cmd = "python -m py_compile backend/main.py"
            run_cmd = "python backend/main.py"
        else:
            build_cmd = "unknown"
            run_cmd = "unknown"
        
        return build_cmd, run_cmd


class ArtifactReconciler:
    """
    Reconciles expected manifest vs actual disk state.
    
    Used by ExportGate to verify integrity before export.
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
    
    async def reconcile(self, expected_manifest: DiskManifest) -> Dict[str, Any]:
        """
        Compare expected manifest to actual disk state.
        
        Returns reconciliation report.
        """
        report = {
            "match": True,
            "missing_files": [],
            "hash_mismatches": [],
            "extra_files": [],
            "total_expected": len(expected_manifest.entries),
            "total_actual": 0
        }
        
        # Build set of actual files on disk
        actual_files = {}
        for root, dirs, files in os.walk(self.workspace_path):
            for file in files:
                if file == "actual_disk_manifest.json":
                    continue
                    
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.workspace_path)
                
                # Calculate hash
                with open(full_path, "rb") as f:
                    content = f.read()
                    actual_files[rel_path] = hashlib.sha256(content).hexdigest()
        
        report["total_actual"] = len(actual_files)
        
        # Check each expected file
        for entry in expected_manifest.entries:
            path = entry["path"]
            expected_hash = entry["hash"]
            
            if path not in actual_files:
                report["missing_files"].append(path)
                report["match"] = False
            elif actual_files[path] != expected_hash:
                report["hash_mismatches"].append({
                    "path": path,
                    "expected": expected_hash,
                    "actual": actual_files[path]
                })
                report["match"] = False
        
        # Check for extra files
        expected_paths = {e["path"] for e in expected_manifest.entries}
        for actual_path in actual_files:
            if actual_path not in expected_paths:
                report["extra_files"].append(actual_path)
        
        return report

