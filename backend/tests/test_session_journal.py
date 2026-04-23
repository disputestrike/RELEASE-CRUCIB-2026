from __future__ import annotations

import uuid

from services.session_journal import append_entry, list_entries


def test_session_journal_append_and_list():
    project_id = "journal-test-project"
    append_entry(
        project_id,
        entry_type="tool_execution",
        task_id="task-1",
        payload={"tool": "file", "success": True},
    )
    entries = list_entries(project_id, limit=20)
    assert entries
    last = entries[-1]
    assert last["project_id"] == project_id
    assert last["entry_type"] == "tool_execution"
    assert last["payload"]["tool"] == "file"


def test_session_journal_retention_limit(monkeypatch):
    monkeypatch.setenv("CRUCIB_SESSION_JOURNAL_MAX_ENTRIES", "100")
    project_id = f"journal-retention-{uuid.uuid4().hex[:8]}"
    for i in range(140):
        append_entry(
            project_id,
            entry_type="tool_execution",
            payload={"index": i},
        )

    entries = list_entries(project_id, limit=0)
    assert len(entries) == 100
    assert entries[0]["payload"]["index"] == 40
    assert entries[-1]["payload"]["index"] == 139
