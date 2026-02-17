"""
Tests for Phase 3 tool agents: Browser, File, API, Database, Deployment.
"""
import pytest
import asyncio
import os
from pathlib import Path
import tempfile
import shutil


# ==================== BASE AGENT ====================

def test_base_agent_import():
    """BaseAgent can be imported."""
    from agents.base_agent import BaseAgent
    assert BaseAgent is not None


def test_base_agent_abstract():
    """BaseAgent is abstract and requires execute implementation."""
    from agents.base_agent import BaseAgent
    
    # Should not be able to instantiate directly
    with pytest.raises(TypeError):
        BaseAgent(llm_client=None, config={})


# ==================== BROWSER AGENT ====================

def test_browser_agent_import():
    """BrowserAgent can be imported."""
    from tools.browser_agent import BrowserAgent
    assert BrowserAgent is not None


def test_browser_agent_init():
    """BrowserAgent initializes correctly."""
    from tools.browser_agent import BrowserAgent
    agent = BrowserAgent(llm_client=None, config={})
    assert agent.name == "BrowserAgent"
    assert agent.llm_client is None


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Playwright browsers to be installed")
async def test_browser_agent_unknown_action():
    """BrowserAgent returns error for unknown action."""
    from tools.browser_agent import BrowserAgent
    agent = BrowserAgent(llm_client=None, config={})
    result = await agent.execute({"action": "unknown_action"})
    assert "error" in result
    assert "Unknown action" in result["error"]


# ==================== FILE AGENT ====================

def test_file_agent_import():
    """FileAgent can be imported."""
    from tools.file_agent import FileAgent
    assert FileAgent is not None


def test_file_agent_init():
    """FileAgent initializes and creates workspace."""
    from tools.file_agent import FileAgent
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agent = FileAgent(llm_client=None, config={"workspace": tmpdir})
        assert agent.name == "FileAgent"
        assert agent.workspace == Path(tmpdir)
        assert agent.workspace.exists()


@pytest.mark.asyncio
async def test_file_agent_write_read():
    """FileAgent can write and read files."""
    from tools.file_agent import FileAgent
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agent = FileAgent(llm_client=None, config={"workspace": tmpdir})
        
        # Write file
        write_result = await agent.execute({
            "action": "write",
            "path": "test.txt",
            "content": "Hello, World!"
        })
        assert write_result.get("success") is True
        
        # Read file
        read_result = await agent.execute({
            "action": "read",
            "path": "test.txt"
        })
        assert read_result.get("success") is True
        assert read_result.get("content") == "Hello, World!"


@pytest.mark.asyncio
async def test_file_agent_list_directory():
    """FileAgent can list directory contents."""
    from tools.file_agent import FileAgent
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agent = FileAgent(llm_client=None, config={"workspace": tmpdir})
        
        # Create some files
        await agent.execute({
            "action": "write",
            "path": "file1.txt",
            "content": "Test 1"
        })
        await agent.execute({
            "action": "write",
            "path": "file2.txt",
            "content": "Test 2"
        })
        
        # List directory
        list_result = await agent.execute({
            "action": "list",
            "path": "."
        })
        assert list_result.get("success") is True
        assert list_result.get("count") >= 2
        assert len(list_result.get("files", [])) >= 2


@pytest.mark.asyncio
async def test_file_agent_mkdir():
    """FileAgent can create directories."""
    from tools.file_agent import FileAgent
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agent = FileAgent(llm_client=None, config={"workspace": tmpdir})
        
        result = await agent.execute({
            "action": "mkdir",
            "path": "subdir/nested"
        })
        assert result.get("success") is True
        assert (agent.workspace / "subdir" / "nested").exists()


@pytest.mark.asyncio
async def test_file_agent_delete():
    """FileAgent can delete files."""
    from tools.file_agent import FileAgent
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agent = FileAgent(llm_client=None, config={"workspace": tmpdir})
        
        # Create file
        await agent.execute({
            "action": "write",
            "path": "delete_me.txt",
            "content": "Delete this"
        })
        
        # Delete file
        result = await agent.execute({
            "action": "delete",
            "path": "delete_me.txt"
        })
        assert result.get("success") is True
        assert not (agent.workspace / "delete_me.txt").exists()


@pytest.mark.asyncio
async def test_file_agent_unknown_action():
    """FileAgent returns error for unknown action."""
    from tools.file_agent import FileAgent
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agent = FileAgent(llm_client=None, config={"workspace": tmpdir})
        result = await agent.execute({"action": "unknown_action"})
        assert "error" in result
        assert result.get("success") is False


# ==================== API AGENT ====================

def test_api_agent_import():
    """APIAgent can be imported."""
    from tools.api_agent import APIAgent
    assert APIAgent is not None


def test_api_agent_init():
    """APIAgent initializes correctly."""
    from tools.api_agent import APIAgent
    agent = APIAgent(llm_client=None, config={})
    assert agent.name == "APIAgent"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires network access to httpbin.org")
async def test_api_agent_get_request():
    """APIAgent can make GET requests."""
    from tools.api_agent import APIAgent
    agent = APIAgent(llm_client=None, config={})
    
    # Test with a public API
    result = await agent.execute({
        "method": "GET",
        "url": "https://httpbin.org/get"
    })
    
    assert result.get("status_code") == 200
    assert result.get("success") is True


@pytest.mark.asyncio
async def test_api_agent_unknown_method():
    """APIAgent returns error for unknown HTTP method."""
    from tools.api_agent import APIAgent
    agent = APIAgent(llm_client=None, config={})
    
    result = await agent.execute({
        "method": "INVALID",
        "url": "https://httpbin.org/get"
    })
    assert "error" in result


# ==================== DATABASE AGENT ====================

def test_database_agent_import():
    """DatabaseOperationsAgent can be imported."""
    from tools.database_operations_agent import DatabaseOperationsAgent
    assert DatabaseOperationsAgent is not None


def test_database_agent_init():
    """DatabaseOperationsAgent initializes correctly."""
    from tools.database_operations_agent import DatabaseOperationsAgent
    agent = DatabaseOperationsAgent(llm_client=None, config={})
    assert agent.name == "DatabaseOperationsAgent"


@pytest.mark.asyncio
async def test_database_agent_sqlite_create_table():
    """DatabaseOperationsAgent can execute SQLite queries."""
    from tools.database_operations_agent import DatabaseOperationsAgent
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        agent = DatabaseOperationsAgent(llm_client=None, config={})
        
        # Create table
        result = await agent.execute({
            "db_type": "sqlite",
            "connection": {"database": db_path},
            "query": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
            "params": []
        })
        assert result.get("success") is True


@pytest.mark.asyncio
async def test_database_agent_sqlite_insert_select():
    """DatabaseOperationsAgent can insert and select from SQLite."""
    from tools.database_operations_agent import DatabaseOperationsAgent
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        agent = DatabaseOperationsAgent(llm_client=None, config={})
        
        # Create table
        await agent.execute({
            "db_type": "sqlite",
            "connection": {"database": db_path},
            "query": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
            "params": []
        })
        
        # Insert data
        insert_result = await agent.execute({
            "db_type": "sqlite",
            "connection": {"database": db_path},
            "query": "INSERT INTO users (name) VALUES (?)",
            "params": ["Alice"]
        })
        assert insert_result.get("success") is True
        
        # Select data
        select_result = await agent.execute({
            "db_type": "sqlite",
            "connection": {"database": db_path},
            "query": "SELECT * FROM users",
            "params": []
        })
        assert select_result.get("success") is True
        assert select_result.get("row_count") >= 1
        assert len(select_result.get("rows", [])) >= 1


@pytest.mark.asyncio
async def test_database_agent_unknown_db_type():
    """DatabaseOperationsAgent returns error for unknown database type."""
    from tools.database_operations_agent import DatabaseOperationsAgent
    agent = DatabaseOperationsAgent(llm_client=None, config={})
    
    result = await agent.execute({
        "db_type": "unknown_db",
        "connection": {},
        "query": "SELECT 1"
    })
    assert "error" in result


# ==================== DEPLOYMENT AGENT ====================

def test_deployment_agent_import():
    """DeploymentOperationsAgent can be imported."""
    from tools.deployment_operations_agent import DeploymentOperationsAgent
    assert DeploymentOperationsAgent is not None


def test_deployment_agent_init():
    """DeploymentOperationsAgent initializes correctly."""
    from tools.deployment_operations_agent import DeploymentOperationsAgent
    agent = DeploymentOperationsAgent(llm_client=None, config={})
    assert agent.name == "DeploymentOperationsAgent"


@pytest.mark.asyncio
async def test_deployment_agent_unknown_platform():
    """DeploymentOperationsAgent returns error for unknown platform."""
    from tools.deployment_operations_agent import DeploymentOperationsAgent
    agent = DeploymentOperationsAgent(llm_client=None, config={})
    
    result = await agent.execute({
        "platform": "unknown_platform",
        "project_path": "./test"
    })
    assert "error" in result


# ==================== AGENT DAG INTEGRATION ====================

def test_agent_dag_has_tool_agents():
    """AGENT_DAG contains new tool agents."""
    from agent_dag import AGENT_DAG
    
    tool_agents = [
        "Browser Tool Agent",
        "File Tool Agent",
        "API Tool Agent",
        "Database Tool Agent",
        "Deployment Tool Agent"
    ]
    
    for agent_name in tool_agents:
        assert agent_name in AGENT_DAG, f"Missing agent: {agent_name}"
        assert "depends_on" in AGENT_DAG[agent_name]
        assert "system_prompt" in AGENT_DAG[agent_name]
