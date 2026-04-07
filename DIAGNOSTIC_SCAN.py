#!/usr/bin/env python3
"""
CrucibAI DIAGNOSTIC SCANNER
==============================================================================
Scans the entire codebase to identify:
1. Missing integrations
2. Unimplemented components
3. Status bar issues
4. Pre-build state issues
5. Empty states
6. Broken imports/dependencies
7. Database schema mismatches
8. API endpoint wiring issues
==============================================================================
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple

class DiagnosticScanner:
    def __init__(self, root_dir="/home/claude/CrucibAI"):
        self.root = Path(root_dir)
        self.issues = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }
        self.components = {
            "implemented": [],
            "partial": [],
            "missing": [],
        }

    def scan_frontend_for_TODO(self):
        """Find all TODO/FIXME comments in frontend"""
        frontend_src = self.root / "frontend" / "src"
        todos = []
        
        for fpath in frontend_src.rglob("*.js*"):
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        if re.search(r'TODO|FIXME|XXX|HACK|BROKEN|NOT_IMPLEMENTED', line, re.I):
                            todos.append({
                                "file": str(fpath.relative_to(self.root)),
                                "line": i,
                                "text": line.strip()[:100]
                            })
            except:
                pass
        
        if todos:
            self.issues["high"].append({
                "category": "Frontend TODOs",
                "count": len(todos),
                "items": todos[:20]  # First 20
            })

    def scan_status_bar(self):
        """Check if status bar is actually wired up"""
        workspace_file = self.root / "frontend" / "src" / "pages" / "Workspace.jsx"
        
        if not workspace_file.exists():
            self.issues["critical"].append({
                "category": "Status Bar",
                "issue": "Workspace.jsx not found",
                "file": str(workspace_file)
            })
            return
        
        try:
            with open(workspace_file, 'r') as f:
                content = f.read()
                
            # Check for status bar component
            if "StatusBar" not in content and "statusBar" not in content:
                self.issues["high"].append({
                    "category": "Status Bar",
                    "issue": "StatusBar component not imported or used in Workspace",
                    "location": "Workspace.jsx"
                })
            
            # Check if it's actually connected to backend
            if "buildStatus" not in content:
                self.issues["high"].append({
                    "category": "Status Bar",
                    "issue": "No buildStatus state tracking in Workspace",
                    "location": "Workspace.jsx"
                })
        except Exception as e:
            self.issues["medium"].append({
                "category": "Status Bar",
                "issue": f"Could not read Workspace.jsx: {e}"
            })

    def scan_prebuild_states(self):
        """Check for pre-build empty states"""
        pages_dir = self.root / "frontend" / "src" / "pages"
        
        files_to_check = [
            "Dashboard.jsx",
            "Builder.jsx",
            "ProjectBuilder.jsx"
        ]
        
        for fname in files_to_check:
            fpath = pages_dir / fname
            if not fpath.exists():
                self.issues["high"].append({
                    "category": "Pre-build States",
                    "issue": f"{fname} not found",
                    "expected_location": str(fpath)
                })
                continue
            
            try:
                with open(fpath, 'r') as f:
                    content = f.read()
                
                # Check for empty state
                if "emptyState" not in content and "placeholder" not in content.lower():
                    self.issues["medium"].append({
                        "category": "Pre-build States",
                        "issue": f"{fname} has no visible empty state",
                        "file": str(fpath.relative_to(self.root))
                    })
            except:
                pass

    def scan_backend_routes(self):
        """Check if all necessary backend routes are wired"""
        server_file = self.root / "backend" / "server.py"
        
        required_endpoints = [
            "/api/projects",
            "/api/builds",
            "/api/agents",
            "/api/workspace",
            "/api/quality-gate",
            "/api/build-plan",
        ]
        
        if not server_file.exists():
            self.issues["critical"].append({
                "category": "Backend Routes",
                "issue": "server.py not found",
                "file": str(server_file)
            })
            return
        
        try:
            with open(server_file, 'r') as f:
                content = f.read()
            
            missing = []
            for endpoint in required_endpoints:
                # Check for decorator or string reference
                if endpoint not in content:
                    missing.append(endpoint)
            
            if missing:
                self.issues["high"].append({
                    "category": "Backend Routes",
                    "issue": f"Missing endpoints: {', '.join(missing)}",
                    "location": "server.py"
                })
        except Exception as e:
            self.issues["medium"].append({
                "category": "Backend Routes",
                "issue": f"Could not scan server.py: {e}"
            })

    def scan_frontend_api_calls(self):
        """Check frontend API integration"""
        frontend_src = self.root / "frontend" / "src"
        
        # Look for broken fetch/axios calls
        broken_apis = []
        
        for fpath in frontend_src.rglob("*.js*"):
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                # Find fetch/axios calls
                matches = re.findall(r'(fetch|axios\.(get|post|put|delete))\([\'"]([^\'"]+)', content)
                for match in matches:
                    endpoint = match[2] if len(match) > 2 else match[0]
                    
                    # Check if endpoint looks incomplete
                    if endpoint.startswith('/api/') and '/api/undefined' in endpoint:
                        broken_apis.append({
                            "file": str(fpath.relative_to(self.root)),
                            "endpoint": endpoint
                        })
            except:
                pass
        
        if broken_apis:
            self.issues["high"].append({
                "category": "Frontend API Calls",
                "issue": f"Broken/undefined API endpoints found",
                "count": len(broken_apis),
                "examples": broken_apis[:5]
            })

    def scan_database_schema(self):
        """Check if database schema is properly initialized"""
        db_init = self.root / "backend" / "database_init.py"
        
        if not db_init.exists():
            self.issues["critical"].append({
                "category": "Database",
                "issue": "database_init.py not found"
            })
            return
        
        try:
            with open(db_init, 'r') as f:
                content = f.read()
            
            # Check for schema definitions
            required_tables = [
                "users",
                "projects",
                "builds",
                "workspaces",
                "agents",
            ]
            
            missing_tables = []
            for table in required_tables:
                if f"'{table}'" not in content and f'"{table}"' not in content and f'`{table}`' not in content:
                    missing_tables.append(table)
            
            if missing_tables:
                self.issues["high"].append({
                    "category": "Database Schema",
                    "issue": f"Missing table definitions: {', '.join(missing_tables)}",
                    "file": "database_init.py"
                })
        except Exception as e:
            self.issues["medium"].append({
                "category": "Database Schema",
                "issue": f"Could not parse database_init.py: {e}"
            })

    def scan_component_wiring(self):
        """Check if major UI components are properly wired"""
        component_checks = {
            "Layout.jsx": ["navbar", "sidebar", "footer"],
            "Workspace.jsx": ["editor", "preview", "statusbar"],
            "Dashboard.jsx": ["projects", "recent", "templates"],
        }
        
        frontend_src = self.root / "frontend" / "src"
        
        for comp_file, features in component_checks.items():
            fpath = frontend_src / "pages" / comp_file
            
            if not fpath.exists():
                fpath = frontend_src / "components" / comp_file
            
            if not fpath.exists():
                self.issues["high"].append({
                    "category": "Component Wiring",
                    "issue": f"{comp_file} not found",
                    "expected": f"src/pages/{comp_file} or src/components/{comp_file}"
                })
                continue
            
            try:
                with open(fpath, 'r') as f:
                    content = f.read()
                
                missing_features = []
                for feature in features:
                    if feature.lower() not in content.lower():
                        missing_features.append(feature)
                
                if missing_features:
                    self.issues["medium"].append({
                        "category": "Component Wiring",
                        "issue": f"{comp_file} missing features: {', '.join(missing_features)}",
                        "file": str(fpath.relative_to(self.root))
                    })
            except:
                pass

    def scan_environment_config(self):
        """Check if environment variables are properly set up"""
        env_example = self.root / "backend" / ".env.example"
        env_file = self.root / "backend" / ".env"
        
        if not env_example.exists():
            self.issues["medium"].append({
                "category": "Environment Config",
                "issue": ".env.example not found"
            })
            return
        
        try:
            with open(env_example, 'r') as f:
                example_vars = [line.split('=')[0].strip() for line in f if '=' in line and not line.startswith('#')]
            
            if env_file.exists():
                with open(env_file, 'r') as f:
                    set_vars = [line.split('=')[0].strip() for line in f if '=' in line and not line.startswith('#')]
                
                missing = set(example_vars) - set(set_vars)
                if missing:
                    self.issues["high"].append({
                        "category": "Environment Config",
                        "issue": f"Missing environment variables in .env: {', '.join(list(missing)[:5])}...",
                        "total_missing": len(missing)
                    })
            else:
                self.issues["critical"].append({
                    "category": "Environment Config",
                    "issue": ".env file not found - app cannot run"
                })
        except Exception as e:
            self.issues["medium"].append({
                "category": "Environment Config",
                "issue": f"Could not parse .env files: {e}"
            })

    def run_all_scans(self):
        """Execute all diagnostic scans"""
        print("🔍 CRUCIBAI DIAGNOSTIC SCANNER")
        print("=" * 80)
        
        scans = [
            ("Frontend TODOs", self.scan_frontend_for_TODO),
            ("Status Bar Wiring", self.scan_status_bar),
            ("Pre-build States", self.scan_prebuild_states),
            ("Backend Routes", self.scan_backend_routes),
            ("Frontend API Integration", self.scan_frontend_api_calls),
            ("Database Schema", self.scan_database_schema),
            ("Component Wiring", self.scan_component_wiring),
            ("Environment Config", self.scan_environment_config),
        ]
        
        for name, scan_func in scans:
            print(f"  ⏳ Scanning {name}...")
            try:
                scan_func()
            except Exception as e:
                print(f"    ⚠️  Error during scan: {e}")
        
        print("\n" + "=" * 80)
        self.print_results()

    def print_results(self):
        """Print scan results in priority order"""
        total_issues = sum(len(v) for v in self.issues.values())
        
        print(f"\n📊 SCAN COMPLETE - {total_issues} issues found\n")
        
        for severity in ["critical", "high", "medium", "low"]:
            issues = self.issues[severity]
            if not issues:
                continue
            
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}[severity]
            print(f"{icon} {severity.upper()} ({len(issues)} issues)")
            print("-" * 80)
            
            for issue in issues:
                if isinstance(issue, dict):
                    if "category" in issue:
                        print(f"   [{issue['category']}]", end="")
                        if "issue" in issue:
                            print(f" {issue['issue']}")
                        if "count" in issue:
                            print(f"              Count: {issue['count']}")
                        if "file" in issue:
                            print(f"              File: {issue['file']}")
                    else:
                        print(f"   {issue}")
            
            print()

if __name__ == "__main__":
    scanner = DiagnosticScanner()
    scanner.run_all_scans()
    
    # Exit with error if critical issues found
    sys.exit(len(scanner.issues["critical"]))
