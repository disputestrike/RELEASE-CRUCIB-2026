"""
FIX #5: Proof Bundle Generator

Creates /proof/{job_id}/ directory with complete evidence of execution for every run.

Structure:
/proof/{job_id}/
  ├─ manifest.json          # Job metadata, timeline, status
  ├─ status.json            # Final status (SUCCESS/FAILED/CANCELED)
  ├─ phases.json            # Each phase's result
  ├─ logs/
  │  ├─ planning.log
  │  ├─ generation.log
  │  ├─ verification.log
  │  └─ deployment.log
  ├─ artifacts/
  │  ├─ generated_code.zip
  │  ├─ package.json
  │  └─ deploy_url.txt (if successful)
  ├─ workspace_meta/        # P5: copy of workspace META (+ path_last_writer when present)
  ├─ verification/
  │  ├─ compile_check.json
  │  ├─ api_smoke.json
  │  ├─ preview.json
  │  ├─ security.json
  │  └─ elite_builder.json
  ├─ deployment/
  │  ├─ build_output.json
  │  ├─ deployment_status.json
  │  └─ health_check.json
  └─ metrics.json            # Timing, cost, tokens
"""

import asyncio
import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProofBundleGenerator:
    """Generate complete proof bundles for every job execution."""
    
    def __init__(self, proof_base_dir: str = "/tmp/proof"):
        self.proof_base_dir = proof_base_dir
        os.makedirs(proof_base_dir, exist_ok=True)
    
    async def generate_proof_bundle(
        self,
        job_id: str,
        job_state: Dict[str, Any],
    ) -> str:
        """
        Generate complete proof bundle for job.
        
        Returns: Path to proof directory (e.g., "/tmp/proof/job-123")
        """
        proof_dir = os.path.join(self.proof_base_dir, job_id)
        os.makedirs(proof_dir, exist_ok=True)
        
        # Create subdirectories
        for subdir in ["logs", "artifacts", "verification", "deployment"]:
            os.makedirs(os.path.join(proof_dir, subdir), exist_ok=True)
        
        # 1. MANIFEST
        await self._write_manifest(proof_dir, job_id, job_state)
        
        # 2. STATUS
        await self._write_status(proof_dir, job_state)
        
        # 3. PHASES
        await self._write_phases(proof_dir, job_state)
        
        # 4. LOGS
        await self._write_logs(proof_dir, job_state)
        
        # 5. VERIFICATION RESULTS
        await self._write_verification_results(proof_dir, job_state)
        
        # 6. DEPLOYMENT INFO
        await self._write_deployment_info(proof_dir, job_state)
        
        # 7. METRICS
        await self._write_metrics(proof_dir, job_state)
        
        # 8. ARTIFACTS
        await self._collect_artifacts(proof_dir, job_state)

        # 8b. Workspace META (P5 proof ↔ files) — mirror from sealed project workspace when available
        await self._copy_workspace_meta(proof_dir, job_state)
        
        # 9. CREATE ZIP FOR DOWNLOAD
        await self._create_proof_zip(proof_dir)
        
        logger.info(f"Proof bundle generated: {proof_dir}")
        return proof_dir
    
    async def _copy_workspace_meta(self, proof_dir: str, job_state: Dict[str, Any]) -> None:
        """Copy META/* from the durable workspace into proof bundle (P5)."""
        ws = (job_state.get("workspace_path") or "").strip()
        pid = (job_state.get("project_id") or "").strip().replace("..", "")
        if not ws and pid:
            try:
                from pathlib import Path
                from project_state import WORKSPACE_ROOT

                p = Path(WORKSPACE_ROOT) / pid
                if p.is_dir():
                    ws = str(p.resolve())
            except Exception as e:
                logger.debug("workspace_meta: resolve workspace: %s", e)
        if not ws or not os.path.isdir(ws):
            return
        meta = os.path.join(ws, "META")
        if not os.path.isdir(meta):
            return
        dest = os.path.join(proof_dir, "workspace_meta")
        os.makedirs(dest, exist_ok=True)
        for name in (
            "proof_index.json",
            "artifact_manifest.json",
            "run_manifest.json",
            "seal.json",
            "path_last_writer.json",
        ):
            src = os.path.join(meta, name)
            if os.path.isfile(src):
                try:
                    shutil.copy2(src, os.path.join(dest, name))
                except OSError as e:
                    logger.debug("workspace_meta copy %s: %s", name, e)

    async def _write_manifest(self, proof_dir: str, job_id: str, job_state: Dict[str, Any]) -> None:
        """Write job manifest."""
        manifest = {
            "job_id": job_id,
            "user_id": job_state.get("user_id", "unknown"),
            "created_at": job_state.get("created_at", datetime.utcnow().isoformat()),
            "completed_at": job_state.get("completed_at", datetime.utcnow().isoformat()),
            "status": job_state.get("status", "unknown"),
            "original_prompt": job_state.get("goal", ""),
            "phases": self._extract_phases_summary(job_state),
        }
        
        manifest_path = os.path.join(proof_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2, default=str)
    
    async def _write_status(self, proof_dir: str, job_state: Dict[str, Any]) -> None:
        """Write final job status."""
        status = {
            "status": job_state.get("status", "unknown"),
            "root_cause": job_state.get("failure_reason") or None,
            "details": job_state.get("failure_details") or "Completed successfully",
            "recommendation": "Deploy ready" if job_state.get("status") == "completed" else "Review failures",
        }
        
        status_path = os.path.join(proof_dir, "status.json")
        with open(status_path, "w") as f:
            json.dump(status, f, indent=2)
    
    async def _write_phases(self, proof_dir: str, job_state: Dict[str, Any]) -> None:
        """Write phase execution details."""
        phases = {
            "planning": self._extract_phase_state(job_state, "planning"),
            "generation": self._extract_phase_state(job_state, "generation"),
            "database": self._extract_phase_state(job_state, "database"),
            "verification": self._extract_phase_state(job_state, "verification"),
            "deployment": self._extract_phase_state(job_state, "deployment"),
        }
        
        phases_path = os.path.join(proof_dir, "phases.json")
        with open(phases_path, "w") as f:
            json.dump(phases, f, indent=2, default=str)
    
    async def _write_logs(self, proof_dir: str, job_state: Dict[str, Any]) -> None:
        """Write phase logs."""
        logs_dir = os.path.join(proof_dir, "logs")
        
        for phase in ["planning", "generation", "database", "verification", "deployment"]:
            phase_logs = job_state.get(f"{phase}_logs", [])
            log_content = "\n".join(phase_logs)
            
            log_path = os.path.join(logs_dir, f"{phase}.log")
            with open(log_path, "w") as f:
                f.write(log_content)
    
    async def _write_verification_results(self, proof_dir: str, job_state: Dict[str, Any]) -> None:
        """Write verification check results."""
        verification_dir = os.path.join(proof_dir, "verification")
        verification_results = job_state.get("verification_results", {})
        
        for check_name, result in verification_results.items():
            check_path = os.path.join(verification_dir, f"{check_name}.json")
            with open(check_path, "w") as f:
                json.dump(result if isinstance(result, dict) else {"result": str(result)}, f, indent=2, default=str)
    
    async def _write_deployment_info(self, proof_dir: str, job_state: Dict[str, Any]) -> None:
        """Write deployment information."""
        deployment_dir = os.path.join(proof_dir, "deployment")
        
        deployment = job_state.get("deployment", {})
        if deployment:
            deploy_info = {
                "url": deployment.get("url"),
                "status": deployment.get("status", "unknown"),
                "health_check_passed": deployment.get("health_check_passed", False),
                "deployed_at": str(deployment.get("deployed_at", datetime.utcnow().isoformat())),
            }
            
            deploy_path = os.path.join(deployment_dir, "deployment_status.json")
            with open(deploy_path, "w") as f:
                json.dump(deploy_info, f, indent=2)
            
            # Write deploy URL for easy access
            if deployment.get("url"):
                url_path = os.path.join(proof_dir, "artifacts", "deploy_url.txt")
                with open(url_path, "w") as f:
                    f.write(deployment.get("url"))
    
    async def _write_metrics(self, proof_dir: str, job_state: Dict[str, Any]) -> None:
        """Write execution metrics."""
        metrics = {
            "total_duration_seconds": job_state.get("duration_seconds", 0),
            "tokens_used": job_state.get("total_tokens", 0),
            "cost_cents": job_state.get("cost_cents", 0),
            "phase_timings": self._extract_phase_timings(job_state),
        }
        
        metrics_path = os.path.join(proof_dir, "metrics.json")
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
    
    async def _collect_artifacts(self, proof_dir: str, job_state: Dict[str, Any]) -> None:
        """Collect generated artifacts."""
        artifacts_dir = os.path.join(proof_dir, "artifacts")
        
        generated_files = job_state.get("generated_files", {})
        
        # Collect key artifacts
        key_files = ["package.json", "src/App.jsx", "backend/main.py"]
        for fname in key_files:
            if fname in generated_files:
                artifact_path = os.path.join(artifacts_dir, os.path.basename(fname))
                with open(artifact_path, "w") as f:
                    f.write(generated_files[fname])
        
        # Create zip of all generated code
        if generated_files:
            zip_path = os.path.join(artifacts_dir, "generated_code.zip")
            await self._create_artifacts_zip(zip_path, generated_files)
    
    async def _create_artifacts_zip(self, zip_path: str, files: Dict[str, str]) -> None:
        """Create zip file of generated artifacts."""
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for fname, content in files.items():
                    zf.writestr(fname, content)
            logger.info(f"Created artifacts zip: {zip_path}")
        except Exception as e:
            logger.error(f"Error creating artifacts zip: {e}")
    
    async def _create_proof_zip(self, proof_dir: str) -> None:
        """Create downloadable zip of entire proof bundle."""
        try:
            zip_path = f"{proof_dir}.zip"
            shutil.make_archive(proof_dir, "zip", proof_dir)
            logger.info(f"Created proof bundle zip: {zip_path}")
        except Exception as e:
            logger.error(f"Error creating proof bundle zip: {e}")
    
    def _extract_phases_summary(self, job_state: Dict[str, Any]) -> Dict[str, str]:
        """Extract phase statuses."""
        return {
            "planning": job_state.get("planning_status", "unknown"),
            "generation": job_state.get("generation_status", "unknown"),
            "database": job_state.get("database_status", "unknown"),
            "verification": job_state.get("verification_status", "unknown"),
            "deployment": job_state.get("deployment_status", "unknown"),
        }
    
    def _extract_phase_state(self, job_state: Dict[str, Any], phase: str) -> Dict[str, Any]:
        """Extract detailed phase state."""
        return {
            "status": job_state.get(f"{phase}_status", "unknown"),
            "started_at": str(job_state.get(f"{phase}_start_time", "")),
            "completed_at": str(job_state.get(f"{phase}_end_time", "")),
            "duration_seconds": job_state.get(f"{phase}_duration", 0),
            "error": job_state.get(f"{phase}_error"),
        }
    
    def _extract_phase_timings(self, job_state: Dict[str, Any]) -> Dict[str, float]:
        """Extract phase timings."""
        return {
            "planning": job_state.get("planning_duration", 0),
            "generation": job_state.get("generation_duration", 0),
            "database": job_state.get("database_duration", 0),
            "verification": job_state.get("verification_duration", 0),
            "deployment": job_state.get("deployment_duration", 0),
        }


# Singleton instance
_proof_generator = None


def get_proof_generator(base_dir: str = "/tmp/proof") -> ProofBundleGenerator:
    """Get or create proof bundle generator."""
    global _proof_generator
    if _proof_generator is None:
        _proof_generator = ProofBundleGenerator(base_dir)
    return _proof_generator


async def generate_proof_for_job(job_id: str, job_state: Dict[str, Any]) -> str:
    """Generate proof bundle for a job."""
    generator = get_proof_generator()
    return await generator.generate_proof_bundle(job_id, job_state)
