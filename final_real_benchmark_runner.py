#!/usr/bin/env python3
"""
Final real benchmark runner using the protected benchmark endpoint.
No mocks, no simulations—just real execution on the live production backend.
"""

import asyncio
import json
import time
import httpx
from datetime import datetime

LIVE_URL = "https://vigilant-youth-production-5aa6.up.railway.app"
API_BASE = f"{LIVE_URL}/api"
BENCHMARK_SECRET = "crucibai_benchmark_2026_secret_key"

PROMPTS = [
    "build a SaaS landing page with pricing and auth-ready layout",
    "build a React dashboard with charts and filters",
    "build a FastAPI endpoint and frontend form that calls it",
    "fix a broken React component",
    "add Stripe pricing page UI",
    "build a public share/remix route",
    "generate a proof report for a job",
    "create a multi-page website",
    "create a developer workspace with preview panel",
    "intentionally introduce a failing verification and repair it",
]

async def run_benchmark():
    """Execute the 10-prompt benchmark against the live deployment."""
    results = []
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        for idx, prompt in enumerate(PROMPTS, 1):
            print(f"\n{'='*70}")
            print(f"Prompt #{idx}: {prompt}")
            print(f"{'='*70}")
            
            result = {
                "prompt_idx": idx,
                "prompt": prompt,
                "status": "unknown",
                "job_id": None,
                "project_id": None,
                "error": None,
                "metrics": {},
            }
            
            try:
                # Step 1: Create and Trigger Job
                print("Step 1: Creating and triggering job via benchmark endpoint...")
                start_time = time.time()
                
                resp = await client.post(
                    f"{API_BASE}/jobs/benchmark/run",
                    json={
                        "goal": prompt,
                        "secret": BENCHMARK_SECRET
                    },
                    headers={"Content-Type": "application/json"},
                )
                
                if resp.status_code != 200:
                    error_msg = f"benchmark/run {resp.status_code}: {resp.text[:200]}"
                    print(f"  FAILED: {error_msg}")
                    result["status"] = "failed"
                    result["error"] = error_msg
                    results.append(result)
                    continue
                
                job_res = resp.json()
                job_id = job_res.get("job_id")
                project_id = job_res.get("project_id")
                
                result["job_id"] = job_id
                result["project_id"] = project_id
                print(f"  ✓ Job created: {job_id}")

                # Step 1.5: Trigger Execution
                print("Step 1.5: Triggering execution...")
                exec_resp = await client.post(
                    f"{API_BASE}/orchestrator/run-auto",
                    json={"job_id": job_id},
                    headers={
                        "Content-Type": "application/json",
                        "X-Benchmark-Secret": BENCHMARK_SECRET
                    },
                )
                if exec_resp.status_code in (200, 202):
                    print(f"  ✓ Execution triggered")
                else:
                    print(f"  WARNING: run-auto returned {exec_resp.status_code}: {exec_resp.text}")
                
                # Step 2: Poll for Job Completion
                print("Step 2: Waiting for job completion...")
                max_wait = 180  # seconds
                poll_interval = 5
                elapsed = 0
                job_final_state = None
                
                while elapsed < max_wait:
                    status_resp = await client.get(f"{API_BASE}/jobs/{job_id}")
                    
                    if status_resp.status_code == 200:
                        job_status = status_resp.json()
                        state = job_status.get("state", "unknown")
                        
                        print(f"  Status: {state} (elapsed: {elapsed}s)")
                        
                        if state == "completed":
                            job_final_state = "completed"
                            break
                        elif state == "failed":
                            job_final_state = "failed"
                            break
                    
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                
                if job_final_state is None:
                    print(f"  ✗ Job timed out after {max_wait}s")
                    result["status"] = "timeout"
                else:
                    result["status"] = job_final_state
                
                # Step 3: Fetch Proof and Files
                print("Step 3: Fetching artifacts...")
                proof_resp = await client.get(f"{API_BASE}/jobs/{job_id}/proof")
                files_resp = await client.get(f"{API_BASE}/jobs/{job_id}/files")
                
                result["metrics"]["proof_generated"] = proof_resp.status_code == 200
                result["metrics"]["files_count"] = len(files_resp.json()) if files_resp.status_code == 200 else 0
                result["metrics"]["total_time"] = time.time() - start_time
                
                print(f"  ✓ Proof: {'Yes' if result['metrics']['proof_generated'] else 'No'}")
                print(f"  ✓ Files: {result['metrics']['files_count']}")
                print(f"  ✓ Total Time: {result['metrics']['total_time']:.2f}s")
                
            except Exception as e:
                print(f"✗ FAILED: {e}")
                result["status"] = "failed"
                result["error"] = str(e)
            
            results.append(result)
    
    # Save Results
    with open("/home/ubuntu/crucibai/final_benchmark_results_real.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*70)
    print("FINAL REAL BENCHMARK COMPLETE")
    print("="*70)
    passed = sum(1 for r in results if r["status"] == "completed")
    print(f"Passed: {passed}/10")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
