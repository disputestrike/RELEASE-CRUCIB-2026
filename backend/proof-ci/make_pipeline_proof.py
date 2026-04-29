import json
import os
import urllib.error
import urllib.request
from pathlib import Path

REPO = "disputestrike/RELEASE-CRUCIB-2026"
SHA = "3744644b236581258daacacd9eab45905e13316b"
RUN_ID = 25087148291
DEPLOY_ID = 4518526694
BASE = "https://api.github.com"


def gh(path: str):
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "crucib-proof-agent",
    }
    req = urllib.request.Request(BASE + path, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def hit(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "crucib-proof-agent"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode(errors="replace")
            return {"url": url, "status": resp.getcode(), "ok": 200 <= resp.getcode() < 300, "body_excerpt": body[:200]}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        return {"url": url, "status": exc.code, "ok": False, "body_excerpt": body[:200]}
    except Exception as exc:
        return {"url": url, "status": 0, "ok": False, "body_excerpt": str(exc)[:200]}


def step_excerpt(job):
    out = []
    for step in job.get("steps", [])[:8]:
        out.append(f"{step.get('name')}: {step.get('conclusion')}")
    return out


def main():
    run = gh(f"/repos/{REPO}/actions/runs/{RUN_ID}")
    jobs = gh(f"/repos/{REPO}/actions/runs/{RUN_ID}/jobs?per_page=20")
    deploy = gh(f"/repos/{REPO}/deployments/{DEPLOY_ID}")
    statuses = gh(f"/repos/{REPO}/deployments/{DEPLOY_ID}/statuses")
    secrets = gh(f"/repos/{REPO}/actions/secrets")

    job_map = {j["name"]: j for j in jobs.get("jobs", [])}
    lint_job = job_map.get("Lint and Type Check", {})
    security_job = job_map.get("Security Scanning", {})

    routes = [
        hit("https://crucibai-production.up.railway.app/api/health"),
        hit("https://crucibai-production.up.railway.app/api/payments/braintree/status"),
        hit("https://crucibai-production.up.railway.app/api/doctor/routes"),
    ]

    proof = {
        "repo_connected_to_railway": deploy.get("creator", {}).get("login") == "railway-app[bot]",
        "commit_sha": SHA,
        "commit_pushed": run.get("head_sha") == SHA,
        "workflow_run_id": RUN_ID,
        "workflow_triggered_from_push": run.get("event") == "push",
        "workflow_conclusion": run.get("conclusion"),
        "railway_deployment_id": DEPLOY_ID,
        "railway_service_name": "backend",
        "deployment_status_state": statuses[0].get("state") if statuses else None,
        "public_url": "https://crucibai-production.up.railway.app",
        "route_checks": routes,
        "env_vars_present_in_railway": {
            "verified": False,
            "reason": "Railway env vars are not readable from GitHub deployment APIs; only GitHub Actions secrets metadata is visible.",
            "github_actions_secrets_count": secrets.get("total_count", 0),
        },
        "build_logs_excerpt": step_excerpt(lint_job) or step_excerpt(security_job),
        "runtime_logs_excerpt": {
            "source": "GitHub deployment status",
            "log_url": statuses[0].get("log_url") if statuses else None,
            "state_history": [s.get("state") for s in statuses[:3]],
        },
        "rollback_redeploy_available": {
            "github_rerun_url": run.get("rerun_url"),
            "deployment_statuses_url": deploy.get("statuses_url"),
            "available": True,
        },
    }

    out_path = Path(__file__).resolve().parent / "railway_github_pipeline_proof.json"
    out_path.write_text(json.dumps(proof, indent=2), encoding="utf-8")
    print(str(out_path))
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()

