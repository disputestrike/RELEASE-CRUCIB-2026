"""
Comprehensive test suite for CrucibAI agent system with recursive learning.
Tests Cerebras API, learning system, and agent orchestration.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

# Import systems to test
from agent_recursive_learning import AgentMemory, PerformanceTracker, AdaptiveStrategy, ExecutionStatus
from llm_cerebras import CerebrasClient, invoke_cerebras
from agents.base_agent import BaseAgent, AgentValidationError
from agent_orchestrator import AgentOrchestrator, AgentTask


# Mock database for testing
class MockDB:
    """Mock database for testing"""
    def __init__(self):
        self.collections = {}
    
    def __getitem__(self, collection_name):
        if collection_name not in self.collections:
            self.collections[collection_name] = MockCollection()
        return self.collections[collection_name]


class MockCollection:
    """Mock collection for testing"""
    def __init__(self):
        self.data = []
        self.id_counter = 0
    
    async def insert_one(self, doc):
        self.id_counter += 1
        doc["_id"] = str(self.id_counter)
        self.data.append(doc)
        return doc
    
    async def find_one(self, query):
        for doc in self.data:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None
    
    def _matches(self, doc, query):
        for k, v in query.items():
            if isinstance(v, dict):
                if "$gte" in v and not (doc.get(k, 0) >= v["$gte"]):
                    return False
            elif doc.get(k) != v:
                return False
        return True

    def find(self, query):
        return MockCursor([d for d in self.data if self._matches(d, query)])
    
    async def update_one(self, query, update):
        for doc in self.data:
            if all(doc.get(k) == v for k, v in query.items()):
                if "$set" in update:
                    doc.update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        doc[k] = doc.get(k, 0) + v
                return {"modified_count": 1}
        return {"modified_count": 0}
    
    async def delete_one(self, query):
        for i, doc in enumerate(self.data):
            if all(doc.get(k) == v for k, v in query.items()):
                self.data.pop(i)
                return {"deleted_count": 1}
        return {"deleted_count": 0}
    
    async def count_documents(self, query):
        return sum(1 for d in self.data if all(d.get(k) == v for k, v in query.items()))


class MockCursor:
    """Mock cursor for testing"""
    def __init__(self, data):
        self.data = data
        self.sort_order = None
        self.skip_count = 0
        self.limit_count = None
    
    def sort(self, field, direction):
        self.sort_order = (field, direction)
        return self
    
    def skip(self, count):
        self.skip_count = count
        return self
    
    def limit(self, count):
        self.limit_count = count
        return self
    
    async def to_list(self, length):
        data = self.data
        if self.sort_order:
            field, direction = self.sort_order
            data = sorted(data, key=lambda x: x.get(field, 0), reverse=(direction == -1))
        data = data[self.skip_count:]
        if self.limit_count:
            data = data[:self.limit_count]
        return data


# Test cases
class TestAgentMemory:
    """Test agent memory and learning system"""
    
    @pytest.mark.asyncio
    async def test_record_execution(self):
        """Test recording agent execution"""
        db = MockDB()
        memory = AgentMemory(db)
        
        execution_id = await memory.record_execution(
            agent_name="TestAgent",
            input_data={"task": "test"},
            output={"result": "success"},
            status=ExecutionStatus.SUCCESS,
            duration_ms=100.5,
            error=None
        )
        
        assert execution_id is not None
        
        # Verify it was stored
        stored = await db["agent_memory"].find_one({"_id": execution_id})
        assert stored is not None
        assert stored["agent_name"] == "TestAgent"
        assert stored["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_extract_patterns(self):
        """Test pattern extraction from execution history"""
        db = MockDB()
        memory = AgentMemory(db)
        
        # Record multiple executions
        for i in range(5):
            await memory.record_execution(
                agent_name="TestAgent",
                input_data={"task": f"test_{i}"},
                output={"result": "success"},
                status=ExecutionStatus.SUCCESS,
                duration_ms=100 + i * 10,
                error=None
            )
        
        # Extract patterns
        patterns = await memory.extract_patterns("TestAgent")
        
        assert patterns["agent_name"] == "TestAgent"
        assert patterns["total_executions"] == 5
        assert patterns["success_rate"] == 100.0
        assert patterns["average_duration_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_learning(self):
        """Test storing and retrieving learnings"""
        db = MockDB()
        memory = AgentMemory(db)
        
        # Store a learning
        await memory.store_learning(
            agent_name="TestAgent",
            learning_type="optimization",
            content={"strategy": "parallel_execution"},
            confidence=0.9
        )
        
        # Retrieve learnings
        learnings = await memory.get_learnings("TestAgent", min_confidence=0.8)
        
        assert len(learnings) > 0
        assert learnings[0]["learning_type"] == "optimization"
        assert learnings[0]["confidence"] == 0.9


class TestPerformanceTracker:
    """Test performance tracking system"""
    
    @pytest.mark.asyncio
    async def test_record_metric(self):
        """Test recording performance metrics"""
        db = MockDB()
        tracker = PerformanceTracker(db)
        
        await tracker.record_metric(
            agent_name="TestAgent",
            metric_name="execution_time_ms",
            value=150.5
        )
        
        # Verify it was stored
        metrics = await db["agent_performance"].find({"agent_name": "TestAgent"}).to_list(10)
        assert len(metrics) > 0
        assert metrics[0]["value"] == 150.5
    
    @pytest.mark.asyncio
    async def test_metrics_summary(self):
        """Test getting metrics summary"""
        db = MockDB()
        tracker = PerformanceTracker(db)
        
        # Record multiple metrics
        for i in range(5):
            await tracker.record_metric(
                agent_name="TestAgent",
                metric_name="execution_time_ms",
                value=100 + i * 10
            )
        
        # Get summary
        summary = await tracker.get_metrics_summary(
            agent_name="TestAgent",
            metric_name="execution_time_ms"
        )
        
        assert summary["count"] == 5
        assert summary["min"] == 100
        assert summary["max"] == 140
        assert 110 < summary["avg"] < 130


class TestCerebrasIntegration:
    """Test Cerebras API integration"""
    
    @pytest.mark.asyncio
    async def test_cerebras_client_initialization(self):
        """Test Cerebras client initialization"""
        with patch.dict('os.environ', {'CEREBRAS_API_KEY': 'test-key'}):
            client = CerebrasClient()
            assert client.api_key == 'test-key'
            await client.close()
    
    @pytest.mark.asyncio
    async def test_cerebras_client_missing_key(self):
        """Test Cerebras client with missing API key"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError):
                CerebrasClient()


class TestBaseAgent:
    """Test base agent with learning integration"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initialization"""
        db = MockDB()
        
        class TestAgent(BaseAgent):
            async def execute(self, context):
                return {"status": "ok"}
        
        agent = TestAgent(db=db)
        
        assert agent.name == "TestAgent"
        assert agent.memory is not None
        assert agent.performance is not None
        assert agent.strategy is not None
    
    @pytest.mark.asyncio
    async def test_agent_execution_with_learning(self):
        """Test agent execution records learning"""
        db = MockDB()
        
        class TestAgent(BaseAgent):
            async def execute(self, context):
                return {"result": "success", "data": context.get("input")}
        
        agent = TestAgent(db=db)
        
        result = await agent.run({"input": "test_data"})
        
        assert result["result"] == "success"
        assert result["data"] == "test_data"
        
        # Verify learning was recorded
        executions = await db["agent_memory"].find({"agent_name": "TestAgent"}).to_list(10)
        assert len(executions) > 0
    
    @pytest.mark.asyncio
    async def test_agent_validation_error(self):
        """Test agent validation error handling"""
        db = MockDB()
        
        class StrictAgent(BaseAgent):
            def validate_input(self, context):
                if "required_field" not in context:
                    raise AgentValidationError("Missing required_field")
                return True
            
            async def execute(self, context):
                return {"status": "ok"}
        
        agent = StrictAgent(db=db)
        
        with pytest.raises(AgentValidationError):
            await agent.run({"other_field": "value"})


class TestAgentOrchestrator:
    """Test agent orchestration"""
    
    @pytest.mark.asyncio
    async def test_task_dependency_resolution(self):
        """Test task dependency resolution"""
        db = MockDB()
        
        # Create mock agents
        agents = {
            "Agent1": Mock(),
            "Agent2": Mock(),
        }
        
        orchestrator = AgentOrchestrator(db, agents)
        
        # Create tasks with dependencies
        task1 = AgentTask("task1", "Agent1", {"input": "data1"})
        task2 = AgentTask("task2", "Agent2", {"input": "data2"}, depends_on=["task1"])
        
        # Verify dependency tracking
        assert task1.depends_on == []
        assert task2.depends_on == ["task1"]
    
    @pytest.mark.asyncio
    async def test_workflow_execution_order(self):
        """Test workflow execution respects dependencies"""
        db = MockDB()
        
        execution_order = []
        
        class TrackingAgent(BaseAgent):
            def __init__(self, agent_id):
                super().__init__(db=db)
                self.agent_id = agent_id
            
            async def execute(self, context):
                execution_order.append(self.agent_id)
                await asyncio.sleep(0.01)
                return {"status": "ok"}
        
        agents = {
            "Agent1": TrackingAgent("A1"),
            "Agent2": TrackingAgent("A2"),
        }
        
        orchestrator = AgentOrchestrator(db, agents)
        
        # Create tasks
        task1 = AgentTask("task1", "Agent1", {})
        task2 = AgentTask("task2", "Agent2", {}, depends_on=["task1"])
        
        # Execute workflow
        result = await orchestrator.execute_workflow([task1, task2], parallel=False)
        
        # Verify execution order
        assert result["status"] == "success"
        assert execution_order == ["A1", "A2"]


class TestIntegration:
    """Integration tests for complete system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_agent_learning(self):
        """Test complete agent learning cycle"""
        db = MockDB()
        
        class SmartAgent(BaseAgent):
            async def execute(self, context):
                # Simulate some work
                await asyncio.sleep(0.01)
                return {"result": "success", "tokens": 150}
        
        agent = SmartAgent(db=db)
        
        # Run multiple times
        for i in range(3):
            result = await agent.run({"task": f"task_{i}"})
            assert result["result"] == "success"
        
        # Extract patterns
        patterns = await agent.memory.extract_patterns("SmartAgent")
        
        assert patterns["total_executions"] == 3
        assert patterns["success_rate"] == 100.0
        
        # Store learning
        await agent.memory.store_learning(
            agent_name="SmartAgent",
            learning_type="optimization",
            content={"parallelization": True},
            confidence=0.95
        )
        
        # Retrieve learning
        learnings = await agent.memory.get_learnings("SmartAgent")
        assert len(learnings) > 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
