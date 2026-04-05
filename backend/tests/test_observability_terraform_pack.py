"""Observability workspace pack + multi-region Terraform sketch intents and security proof."""
import os
import tempfile

import pytest

from orchestration.domain_packs import multiregion_terraform_intent, observability_intent
from orchestration.multiregion_terraform_sketch import tf_multiregion_root_main
from orchestration.observability_workspace_pack import docker_compose_observability_stub
from orchestration.verification_security import verify_security_workspace


def test_observability_intent_keywords():
    assert observability_intent("Add OpenTelemetry traces and Prometheus metrics")
    assert observability_intent({"goal": "Grafana dashboards with structured JSON logs"})
    assert not observability_intent("simple todo app")


def test_multiregion_terraform_intent():
    assert multiregion_terraform_intent("Multi-region AWS deployment with Terraform")
    assert multiregion_terraform_intent("Terraform for GKE in europe-west1 and failover")
    assert multiregion_terraform_intent("Cross-region active-active Postgres")
    assert not multiregion_terraform_intent("Local todo app without cloud")


def test_observability_stub_compose_contains_services():
    yml = docker_compose_observability_stub()
    assert "otel-collector" in yml
    assert "prometheus" in yml
    assert "grafana" in yml


def test_terraform_root_declares_aws_modules():
    main = tf_multiregion_root_main()
    assert "module \"aws_primary\"" in main
    assert "aws_region_stub" in main


def test_verify_security_observability_and_terraform_dirs():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "deploy", "observability"), exist_ok=True)
        os.makedirs(os.path.join(d, "terraform", "multiregion_sketch"), exist_ok=True)
        with open(os.path.join(d, "terraform", "multiregion_sketch", "main.tf"), "w", encoding="utf-8") as f:
            f.write("# stub\n")
        os.makedirs(os.path.join(d, "db", "migrations"), exist_ok=True)
        with open(os.path.join(d, "db", "migrations", "001.sql"), "w", encoding="utf-8") as f:
            f.write("SELECT 1;\n")
        os.makedirs(os.path.join(d, "backend"), exist_ok=True)
        with open(os.path.join(d, "backend", "main.py"), "w", encoding="utf-8") as f:
            f.write("from fastapi import FastAPI\napp = FastAPI()\n")
        with open(os.path.join(d, "package.json"), "w", encoding="utf-8") as f:
            f.write('{"dependencies":{"react":"18"},"engines":{"node":">=18"}}\n')
        r = verify_security_workspace(d)
        checks = {p.get("payload", {}).get("check") for p in r["proof"]}
        assert "observability_pack_present" in checks
        assert "multiregion_terraform_sketch_present" in checks


@pytest.mark.asyncio
async def test_planner_detects_observability_integration():
    from orchestration.planner import generate_plan

    plan = await generate_plan(
        "SaaS with Prometheus metrics and Grafana",
        project_state={"env_vars": {"ANTHROPIC_API_KEY": "x"}},
    )
    assert "observability" in (plan.get("required_integrations") or [])


@pytest.mark.asyncio
async def test_planner_detects_multiregion_terraform_integration():
    from orchestration.planner import generate_plan

    plan = await generate_plan(
        "Multi-region Terraform on AWS and GCP with failover",
        project_state={"env_vars": {"ANTHROPIC_API_KEY": "x"}},
    )
    assert "multiregion_terraform" in (plan.get("required_integrations") or [])
