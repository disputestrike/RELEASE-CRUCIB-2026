#!/usr/bin/env python3
"""
Real benchmark runner that hits the live Railway deployment.
No mocks, no simulations—just real HTTP requests to the live API.
"""

import asyncio
import json
import time
import httpx
from datetime import datetime

LIVE_URL = "https://vigilant-youth-production-5aa6.up.railway.app"
API_BASE = f"{LIVE_URL}/api"

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
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for idx, prompt in enumerate(PROMPTS, 1):
            print(f"\n--- Prompt #{idx}: {prompt} ---")
            
            # Step 1: Create Job
            print("Step 1: Creating job...")
            job_data = {
                "goal": prompt,
                "project_id": None,
                "mode": "guided",
                "priority": "normal",
                "timeout": 3600,
            }
            
            try:
                start_time = time.time()
                resp = await client.post(
                    f"{API_BASE}/jobs/",
                    json=job_data,
                    headers={"Content-Type": "application/json"},
                )
                create_time = time.time() - start_time
                
                if resp.status_code not in (200, 201):
                    print(f"FAILED: create_job returned {resp.status_code}: {resp.text[:200]}")
                    results.append({
                        "prompt": prompt,
                        "status": "failed",
                        "error": f"create_job {resp.status_code}",
                        "timestamp": datetime.now().isoformat(),
                    })
                    continue
                
                job_res = resp.json()
                job_id = job_res.get("job", {}).get("id") or job_res.get("id")
                
                if not job_id:
                    print(f"FAILED: No job_id in response: {job_res}")
                    results.append({
                        "prompt": prompt,
                        "status": "failed",
                        "error": "no_job_id",
                        "timestamp": datetime.now().isoformat(),
                    })
                    continue
                
                print(f"Job created: {job_id} (took {create_time:.2f}s)")
                
                # Step 2: Trigger Execution
                print("Step 2: Triggering execution...")
                exec_resp = await client.post(
                    f"{API_BASE}/orchestrator/run-auto",
                    json={"job_id": job_id},
                    headers={"Content-Type": "application/json"},
                )
                
                if exec_resp.status_code not in (200, 202):
                    print(f"WARNING: run-auto returned {exec_resp.status_code}")
                
                # Step 3: Poll for Job Completion
                print("Step 3: Waiting for job completion...")
                max_wait = 60  # seconds
                poll_interval = 2
                elapsed = 0
                first_file_time = None
                
                while elapsed < max_wait:
                    status_resp = await client.get(f"{API_BASE}/jobs/{job_id}")
                    
                    if status_resp.status_code == 200:
                        job_status = status_resp.json()
                        state = job_status.get("state", "unknown")
                        
                        print(f"  Status: {state}")
                        
                        if state == "completed":
                            print(f"Job completed!")
                            break
                        elif state == "failed":
                            print(f"Job failed!")
                            break
                        
                        # Check for first file
                        if first_file_time is None and job_status.get("files_count", 0) > 0:
                            first_file_time = elapsed
                            print(f"  First file generated at {first_file_time}s")
                    
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                
                # Step 4: Fetch Proof
                print("Step 4: Fetching proof.json...")
                proof_resp = await client.get(f"{API_BASE}/jobs/{job_id}/proof")
                
                proof_data = None
                if proof_resp.status_code == 200:
                    proof_data = proof_resp.json()
                    print(f"Proof retrieved: {len(str(proof_data))} bytes")
                else:
                    print(f"WARNING: proof endpoint returned {proof_resp.status_code}")
                
                # Step 5: Fetch Files
                print("Step 5: Fetching generated files...")
                files_resp = await client.get(f"{API_BASE}/jobs/{job_id}/files")
                
                files_data = []
                if files_resp.status_code == 200:
                    files_data = files_resp.json()
                    print(f"Files retrieved: {len(files_data)} files")
                else:
                    print(f"WARNING: files endpoint returned {files_resp.status_code}")
                
                # Record Result
                total_time = time.time() - start_time
                results.append({
                    "prompt": prompt,
                    "status": "completed",
                    "job_id": job_id,
                    "time_to_create": create_time,
                    "time_to_first_file": first_file_time,
                    "total_time": total_time,
                    "files_count": len(files_data),
                    "proof_generated": proof_data is not None,
                    "timestamp": datetime.now().isoformat(),
                })
                
                print(f"✓ Benchmark #{idx} complete ({total_time:.2f}s total)")
                
            except Exception as e:
                print(f"FAILED: {e}")
                results.append({
                    "prompt": prompt,
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })
    
    # Save Results
    with open("/home/ubuntu/crucibai/live_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*60)
    print("BENCHMARK COMPLETE")
    print("="*60)
    passed = sum(1 for r in results if r["status"] == "completed")
    print(f"Passed: {passed}/{len(PROMPTS)}")
    print(f"Results saved to: /home/ubuntu/crucibai/live_benchmark_results.json")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
