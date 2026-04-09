import pytest

from memory.service import get_memory_service


@pytest.mark.asyncio
async def test_memory_service_builds_scoped_context_packets():
    memory = await get_memory_service()

    await memory.store_step_summary(
        project_id="proj-ctx",
        job_id="job-ctx",
        text="Frontend generation completed with auth shell",
        agent_name="Frontend Generation",
        phase="agents.phase_04",
        step_key="agents.frontend_generation",
        metadata={"verification_score": "85"},
    )
    await memory.store_step_summary(
        project_id="proj-ctx",
        job_id="job-ctx",
        text="Rate limiting rules added to API gateway",
        agent_name="Rate Limiting Agent",
        phase="agents.phase_05",
        step_key="agents.rate_limiting_agent",
        metadata={"verification_score": "88"},
    )
    await memory.store_controller_checkpoint(
        project_id="proj-ctx",
        job_id="job-ctx",
        text="Controller recommends synthesis before verification",
        phase="planning",
        checkpoint_type="plan_summary",
    )

    packet = await memory.build_context_packet(
        project_id="proj-ctx",
        job_id="job-ctx",
        phase="agents.phase_05",
        query="What security work is already done?",
        top_k=5,
    )

    assert packet["provider"] in {"memory", "pinecone"}
    assert packet["project_id"] == "proj-ctx"
    assert packet["job_id"] == "job-ctx"
    assert packet["phase"] == "agents.phase_05"
    assert packet["token_usage"] >= 0
    assert packet["recent_memories"]
    assert all(item["job_id"] == "job-ctx" for item in packet["recent_memories"])
    assert all(item["phase"] == "agents.phase_05" for item in packet["recent_memories"])


@pytest.mark.asyncio
async def test_memory_service_retrieves_job_scoped_context():
    memory = await get_memory_service()

    await memory.store_step_summary(
        project_id="proj-job",
        job_id="job-a",
        text="Job A built realtime websocket transport",
        agent_name="WebSocket Agent",
        phase="agents.phase_05",
        step_key="agents.websocket_agent",
    )
    await memory.store_step_summary(
        project_id="proj-job",
        job_id="job-b",
        text="Job B built static marketing homepage",
        agent_name="Content Agent",
        phase="agents.phase_05",
        step_key="agents.content_agent",
    )

    job_a_context = await memory.retrieve_job_context(
        project_id="proj-job",
        job_id="job-a",
        query="What realtime work exists?",
        top_k=5,
    )

    assert job_a_context
    assert all(item["agent"] != "Content Agent" for item in job_a_context)
