#!/usr/bin/env python3
"""
Railway-authenticated benchmark runner.
Uses Railway API token to authenticate with the live CrucibAI deployment.
"""

import asyncio
import json
import time
import httpx
from datetime import datetime
import base64

LIVE_URL = "https://vigilant-youth-production-5aa6.up.railway.app"
API_BASE = f"{LIVE_URL}/api"

# Railway tokens
RAILWAY_API_TOKEN = "rlwy_oacs_47b0c24b2176e5f9563de14ae7466d343d34245c"

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
    
    # Use Railway token as Bearer token
    headers = {
        "Authorization": f"Bearer {RAILWAY_API_TOKEN}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=300.0, verify=False) as client:
        for idx, prompt in enumerate(PROMPTS, 1):
            print(f"\n{'='*70}")
            print(f"Prompt #{idx}: {prompt}")
            print(f"{'='*70}")
            
            result = {
                "prompt_idx": idx,
                "prompt": prompt,
                "status": "unknown",
                "job_id": None,
                "error": None,
                "timestamps": {},
                "metrics": {},
            }
            
            try:
                # Step 1: Create Job
                print("Step 1: Creating job...")
                start_benchmark = time.time()
                result["timestamps"]["benchmark_start"] = datetime.now().isoformat()
                
                job_data = {
                    "goal": prompt,
                    "project_id": None,
                    "mode": "guided",
                    "priority": "normal",
                    "timeout": 3600,
                }
                
                start_create = time.time()
                resp = await client.post(
                    f"{API_BASE}/jobs/",
                    json=job_data,
                    headers=headers,
                )
                create_time = time.time() - start_create
                result["metrics"]["time_to_create"] = create_time
                
                print(f"  Status: {resp.status_code}")
                
                if resp.status_code not in (200, 201):
                    error_msg = f"create_job {resp.status_code}: {resp.text[:200]}"
                    print(f"  FAILED: {error_msg}")
                    result["status"] = "failed"
                    result["error"] = error_msg
                    results.append(result)
                    continue
                
                job_res = resp.json()
                job_id = job_res.get("job", {}).get("id") or job_res.get("id")
                
                if not job_id:
                    error_msg = f"No job_id in response: {job_res}"
                    print(f"  FAILED: {error_msg}")
                    result["status"] = "failed"
                    result["error"] = error_msg
                    results.append(result)
                    continue
                
                result["job_id"] = job_id
                print(f"  ✓ Job created: {job_id} (took {create_time:.2f}s)")
                result["timestamps"]["job_created"] = datetime.now().isoformat()
                
                # Step 2: Trigger Execution
                print("Step 2: Triggering execution...")
                exec_resp = await client.post(
                    f"{API_BASE}/orchestrator/run-auto",
                    json={"job_id": job_id},
                    headers=headers,
                )
                
                if exec_resp.status_code in (200, 202):
                    print(f"  ✓ Execution triggered")
                    result["timestamps"]["execution_triggered"] = datetime.now().isoformat()
                else:
                    print(f"  WARNING: run-auto returned {exec_resp.status_code}")
                
                # Step 3: Poll for Job Completion
                print("Step 3: Waiting for job completion...")
                max_wait = 120  # seconds
                poll_interval = 3
                elapsed = 0
                first_file_time = None
                job_final_state = None
                
                while elapsed < max_wait:
                    status_resp = await client.get(
                        f"{API_BASE}/jobs/{job_id}",
                        headers=headers,
                    )
                    
                    if status_resp.status_code == 200:
                        job_status = status_resp.json()
                        state = job_status.get("state", "unknown")
                        
                        if elapsed % 9 == 0:  # Print every 9 seconds
                            print(f"  Status: {state} (elapsed: {elapsed}s)")
                        
                        if state == "completed":
                            job_final_state = "completed"
                            print(f"  ✓ Job completed!")
                            result["timestamps"]["job_completed"] = datetime.now().isoformat()
                            break
                        elif state == "failed":
                            job_final_state = "failed"
                            print(f"  ✗ Job failed!")
                            result["timestamps"]["job_failed"] = datetime.now().isoformat()
                            break
                        
                        # Check for first file
                        if first_file_time is None and job_status.get("files_count", 0) > 0:
                            first_file_time = elapsed
                            result["metrics"]["time_to_first_file"] = first_file_time
                            print(f"  ✓ First file generated at {first_file_time}s")
                            result["timestamps"]["first_file"] = datetime.now().isoformat()
                    
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                
                if job_final_state is None:
                    print(f"  ✗ Job timed out after {max_wait}s")
                    result["status"] = "timeout"
                    result["error"] = f"Job did not complete within {max_wait}s"
                    results.append(result)
                    continue
                
                # Step 4: Fetch Proof
                print("Step 4: Fetching proof.json...")
                proof_resp = await client.get(
                    f"{API_BASE}/jobs/{job_id}/proof",
                    headers=headers,
                )
                
                proof_data = None
                if proof_resp.status_code == 200:
                    proof_data = proof_resp.json()
                    print(f"  ✓ Proof retrieved ({len(str(proof_data))} bytes)")
                    result["timestamps"]["proof_fetched"] = datetime.now().isoformat()
                else:
                    print(f"  WARNING: proof endpoint returned {proof_resp.status_code}")
                
                # Step 5: Fetch Files
                print("Step 5: Fetching generated files...")
                files_resp = await client.get(
                    f"{API_BASE}/jobs/{job_id}/files",
                    headers=headers,
                )
                
                files_data = []
                if files_resp.status_code == 200:
                    files_data = files_resp.json()
                    print(f"  ✓ Files retrieved ({len(files_data)} files)")
                    result["timestamps"]["files_fetched"] = datetime.now().isoformat()
                else:
                    print(f"  WARNING: files endpoint returned {files_resp.status_code}")
                
                # Step 6: Verify No Placeholders
                print("Step 6: Checking for placeholders...")
                placeholder_count = 0
                for file_obj in files_data:
                    content = file_obj.get("content", "")
                    if any(p in content.lower() for p in ["todo", "fixme", "placeholder", "stub", "mock"]):
                        placeholder_count += 1
                
                if placeholder_count == 0:
                    print(f"  ✓ No placeholders detected")
                else:
                    print(f"  ⚠ {placeholder_count} files contain placeholder markers")
                
                result["metrics"]["files_count"] = len(files_data)
                result["metrics"]["placeholder_count"] = placeholder_count
                result["metrics"]["proof_generated"] = proof_data is not None
                
                # Final Metrics
                total_time = time.time() - start_benchmark
                result["metrics"]["total_time"] = total_time
                result["status"] = "completed"
                result["timestamps"]["benchmark_end"] = datetime.now().isoformat()
                
                print(f"\n✓ Benchmark #{idx} PASSED")
                print(f"  Total time: {total_time:.2f}s")
                print(f"  Files created: {len(files_data)}")
                print(f"  Proof generated: {proof_data is not None}")
                
            except Exception as e:
                print(f"✗ FAILED: {e}")
                result["status"] = "failed"
                result["error"] = str(e)
                result["timestamps"]["error"] = datetime.now().isoformat()
            
            results.append(result)
    
    # Save Results
    with open("/home/ubuntu/crucibai/live_benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Print Summary
    print("\n" + "="*70)
    print("BENCHMARK COMPLETE")
    print("="*70)
    
    passed = sum(1 for r in results if r["status"] == "completed")
    failed = sum(1 for r in results if r["status"] == "failed")
    timeout = sum(1 for r in results if r["status"] == "timeout")
    
    print(f"Passed:  {passed}/10")
    print(f"Failed:  {failed}/10")
    print(f"Timeout: {timeout}/10")
    print(f"\nResults saved to: /home/ubuntu/crucibai/live_benchmark_results.json")
    
    # Calculate averages
    completed_results = [r for r in results if r["status"] == "completed"]
    if completed_results:
        avg_total_time = sum(r["metrics"].get("total_time", 0) for r in completed_results) / len(completed_results)
        avg_files = sum(r["metrics"].get("files_count", 0) for r in completed_results) / len(completed_results)
        print(f"\nAverages (completed jobs):")
        print(f"  Total time: {avg_total_time:.2f}s")
        print(f"  Files per job: {avg_files:.1f}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
