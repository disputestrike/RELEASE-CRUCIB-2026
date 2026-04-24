import asyncio
import json
import time
import uuid
import sys
import os
from typing import Any, Dict, List, Optional

# Add backend to path for direct imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

# Mocking auth for internal testing
class MockUser:
    def __init__(self, id="benchmark-user", email="benchmark@crucib.ai"):
        self.id = id
        self.email = email
        self.is_admin = True
        self.public_api = True

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key):
        return getattr(self, key)

async def run_benchmark():
    from backend.routes.jobs import create_job, get_job, get_job_proof, JobCreateRequest
    from backend.routes.orchestrator import run_auto, RunAutoRequest
    from backend.adapter.routes.files import get_files, get_file_content
    from fastapi import BackgroundTasks

    prompts = [
        "build a SaaS landing page with pricing and auth-ready layout",
        "build a React dashboard with charts and filters",
        "build a FastAPI endpoint and frontend form that calls it",
        "fix a broken React component",
        "add Stripe pricing page UI",
        "build a public share/remix route",
        "generate a proof report for a job",
        "create a multi-page website",
        "create a developer workspace with preview panel",
        "intentionally introduce a failing verification and repair it"
    ]

    user = MockUser()
    results = []
    
    print(f"Starting REAL benchmark for {len(prompts)} prompts...")

    for i, prompt in enumerate(prompts):
        print(f"\n--- Prompt #{i+1}: {prompt} ---")
        start_time = time.time()
        
        # 1. Create Job via /api/jobs/
        print("Step 1: Creating job...")
        job_req = JobCreateRequest(goal=prompt)
        try:
            job_res = await create_job(job_req, user=user)
            # Response format is {"success": True, "job": {...}, "plan": {...}}
            job_id = job_res.get("job", {}).get("id")
        except Exception as e:
            print(f"FAILED: create_job raised: {e}")
            results.append({"prompt": prompt, "status": "failed", "error": str(e)})
            continue
            
        if not job_id:
            print(f"FAILED: No job_id returned. Response: {job_res}")
            results.append({"prompt": prompt, "status": "failed", "error": "No job_id"})
            continue
        
        time_to_job_created = time.time() - start_time
        print(f"Job created: {job_id} (took {time_to_job_created:.2f}s)")

        # 2. Trigger Execution via /api/orchestrator/run-auto
        print("Step 2: Triggering execution...")
        bg_tasks = BackgroundTasks()
        run_req = RunAutoRequest(job_id=job_id)
        try:
            await run_auto(run_req, bg_tasks, user=user)
        except Exception as e:
            print(f"FAILED: run_auto raised: {e}")
            results.append({"prompt": prompt, "status": "failed", "error": str(e)})
            continue
        
        # Manually run the background task since we're not in a real FastAPI request cycle
        from backend.routes.orchestrator import _background_auto_runner_job
        from backend.config import WORKSPACE_ROOT
        workspace_path = str(os.path.join(WORKSPACE_ROOT, job_id))
        
        print("Step 3: Running background execution...")
        # This is the REAL execution path
        try:
            await _background_auto_runner_job(job_id, workspace_path)
        except Exception as e:
            print(f"FAILED: _background_auto_runner_job raised: {e}")
            results.append({"prompt": prompt, "status": "failed", "error": str(e)})
            continue
        
        total_runtime = time.time() - start_time
        print(f"Execution finished (total time: {total_runtime:.2f}s)")

        # 4. Verify Results
        print("Step 4: Verifying results...")
        
        # Fetch Job Status
        try:
            job_data = await get_job(job_id, user=user)
            final_status = job_data.get("status")
            print(f"Final Status: {final_status}")
        except Exception as e:
            print(f"Error fetching job status: {e}")
            final_status = "unknown"

        # Fetch Proof
        try:
            proof_res = await get_job_proof(job_id, user=user)
            has_proof = proof_res.get("success", False)
            print(f"Proof Generated: {has_proof}")
        except Exception as e:
            print(f"Error fetching proof: {e}")
            has_proof = False
            proof_res = None

        # Fetch Files
        try:
            files = await get_files(job_id, user=user)
            file_count = len(files)
            print(f"Files Generated: {file_count}")
        except Exception as e:
            print(f"Error fetching files: {e}")
            files = []
            file_count = 0
        
        # Check for placeholders in a sample file if any exist
        has_placeholders = False
        if file_count > 0:
            def find_first_file(nodes):
                for n in nodes:
                    if n["type"] == "file": return n["path"]
                    if "children" in n:
                        res = find_first_file(n["children"])
                        if res: return res
                return None
            
            first_file_path = find_first_file(files)
            if first_file_path:
                try:
                    content = await get_file_content(job_id, first_file_path, user=user)
                    placeholders = ["TODO", "FIXME", "STUB", "PLACEHOLDER", "INSERT CODE HERE"]
                    if any(p in content.upper() for p in placeholders):
                        has_placeholders = True
                        print(f"WARNING: Placeholders detected in {first_file_path}")
                except Exception as e:
                    print(f"Error reading file content: {e}")

        results.append({
            "prompt": prompt,
            "job_id": job_id,
            "status": final_status,
            "has_proof": has_proof,
            "file_count": file_count,
            "has_placeholders": has_placeholders,
            "time_to_job_created": time_to_job_created,
            "total_runtime": total_runtime,
            "proof_data": proof_res if has_proof else None
        })

    # Save results
    with open("benchmark_results_real.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nBenchmark Complete. Results saved to benchmark_results_real.json")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
