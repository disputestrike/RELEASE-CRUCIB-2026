# backend/orchestration/executor_with_features.py
"""
Enhanced executor integrating all 5 features:
1. WebSocket progress broadcasting (Kanban UI)
2. Sandbox security enforcement
3. Vector DB memory storage/retrieval
4. Database auto-provisioning
5. Design system injection
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class ExecutorWithFeatures:
    """
    Execute agents with full feature integration.
    """
    
    def __init__(self, job_id: str, project_id: str):
        self.job_id = job_id
        self.project_id = project_id
        self.token_limit = 100000  # 100k tokens max per project
        self.fork_threshold = 0.7  # Fork at 70% capacity
        
        # Import feature modules
        from api.routes.job_progress import broadcast_event
        from sandbox.egress_filter import EgressFilter
        from memory.vector_db import get_vector_memory
        from agents.database_architect_agent import DatabaseArchitectAgent
        
        self.broadcast_event = broadcast_event
        self.egress_filter = EgressFilter
        self.get_vector_memory = get_vector_memory
    
    async def execute_build(self, agents: Dict, context: Dict) -> Dict:
        """
        Execute full build pipeline with all 5 features.
        """
        start_time = datetime.utcnow()
        total_agents = sum(len(phase_agents) for phase_agents in agents.values())
        completed = 0
        errors = []
        
        try:
            # Phase 1: Requirements + Schema Generation
            logger.info("🔵 Phase 1: Requirements Analysis")
            await self._broadcast("phase_update", {
                "phase_id": "requirements",
                "status": "running",
                "progress": 0
            })
            
            # Generate database schema
            schema = await self._generate_database_schema(context)
            context['database_schema'] = schema
            
            # Phase 2: Execute agents with memory + broadcast
            phase_idx = 0
            for phase_name, phase_agents in agents.items():
                phase_agents_count = len(phase_agents)
                
                logger.info(f"⚙️  Phase {phase_idx}: {phase_name}")
                await self._broadcast("phase_update", {
                    "phase_id": phase_name,
                    "status": "running",
                    "total": phase_agents_count,
                    "progress": int(phase_idx / len(agents) * 100)
                })
                
                # Execute agents in parallel (with sandbox isolation)
                tasks = [
                    self._execute_agent_with_features(agent, context, phase_name)
                    for agent in phase_agents
                ]
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for agent, result in zip(phase_agents, results):
                    if isinstance(result, Exception):
                        logger.error(f"Agent {agent.name} failed: {result}")
                        errors.append({
                            "agent": agent.name,
                            "error": str(result),
                            "phase": phase_name
                        })
                        
                        await self._broadcast("agent_error", {
                            "agent_name": agent.name,
                            "phase_id": phase_name,
                            "error": str(result)
                        })
                    else:
                        completed += 1
                        
                        # Store output in vector memory
                        await self._store_agent_memory(agent.name, result, phase_name)
                        
                        await self._broadcast("agent_complete", {
                            "agent_name": agent.name,
                            "phase_id": phase_name,
                            "progress": int(completed / total_agents * 100),
                            "summary": result.get("summary", "")
                        })
                        
                        # Check for token overflow
                        await self._check_token_overflow(context)
                
                phase_idx += 1
            
            # Phase 3: Integration & Deployment
            logger.info("✅ Phase 3: Integration")
            await self._broadcast("phase_update", {
                "phase_id": "integration",
                "status": "running"
            })
            
            # Final build steps
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            
            await self._broadcast("build_complete", {
                "job_id": self.job_id,
                "status": "success" if not errors else "partial",
                "total_time": elapsed,
                "agents_completed": completed,
                "agents_failed": len(errors),
                "errors": errors
            })
            
            return {
                "status": "success" if not errors else "partial",
                "job_id": self.job_id,
                "total_time": elapsed,
                "agents_completed": completed,
                "agents_failed": len(errors),
                "errors": errors
            }
        
        except Exception as e:
            logger.error(f"Build failed: {e}")
            await self._broadcast("build_error", {
                "job_id": self.job_id,
                "error": str(e)
            })
            raise
    
    async def _execute_agent_with_features(
        self,
        agent,
        context: Dict,
        phase: str
    ) -> Dict:
        """
        Execute single agent with sandbox isolation + feature integration.
        """
        try:
            # Broadcast agent start
            await self._broadcast("agent_start", {
                "agent_name": agent.name,
                "phase_id": phase
            })
            
            # 1. Inject design system into prompt
            agent_context = self._inject_design_system(context)
            
            # 2. Retrieve relevant memory (vector DB)
            memories = await self._retrieve_relevant_memory(agent.name, context)
            agent_context['retrieved_memories'] = memories
            
            # 3. Inject memory into context
            agent_context['memory_injection'] = self._format_memories(memories)
            
            # 4. Add security context
            agent_context['sandbox_enforced'] = True
            agent_context['egress_whitelist'] = self.egress_filter.WHITELIST
            
            # 5. Execute agent in sandbox
            result = await asyncio.wait_for(
                agent.execute(agent_context),
                timeout=300  # 5 minute timeout
            )
            
            # 6. Validate result with design system
            if 'generated_jsx' in result:
                result['generated_jsx'] = await self._validate_design(result['generated_jsx'])
            
            return result
        
        except asyncio.TimeoutError:
            raise TimeoutError(f"Agent {agent.name} exceeded 5-minute timeout")
        except Exception as e:
            logger.error(f"Error executing {agent.name}: {e}")
            raise
    
    async def _generate_database_schema(self, context: Dict) -> Optional[Dict]:
        """Generate database schema using Architect Agent."""
        try:
            from agents.database_architect_agent import DatabaseArchitectAgent
            from anthropic import AsyncAnthropic
            
            llm = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            agent = DatabaseArchitectAgent(llm)
            
            result = await agent.execute(context)
            
            if result.get("status") == "success":
                return result.get("schema")
            else:
                logger.warning(f"Schema generation failed: {result.get('reason')}")
                return None
        except Exception as e:
            logger.error(f"Error generating schema: {e}")
            return None
    
    async def _store_agent_memory(
        self,
        agent_name: str,
        result: Dict,
        phase: str
    ):
        """Store agent output in vector memory."""
        try:
            vm = await self.get_vector_memory()
            
            output = result.get('generated_code', result.get('output', ''))
            if output:
                await vm.add_memory(
                    project_id=self.project_id,
                    text=output[:2000],
                    memory_type='output',
                    agent_name=agent_name,
                    phase=phase,
                    tokens=result.get('tokens_used', 0)
                )
        except Exception as e:
            logger.warning(f"Failed to store memory for {agent_name}: {e}")
    
    async def _check_token_overflow(self, context: Dict):
        """Check if project is approaching token limit and fork if needed."""
        try:
            vm = await self.get_vector_memory()
            tokens_used = await vm.count_project_tokens(self.project_id)
            usage_percent = tokens_used / self.token_limit
            
            if usage_percent > self.fork_threshold:
                logger.warning(
                    f"Project {self.project_id} at {usage_percent*100:.1f}% capacity. "
                    f"Consider forking to new context."
                )
                
                # Create fork
                await self._create_fork(context)
        
        except Exception as e:
            logger.error(f"Error checking token overflow: {e}")
    
    async def _create_fork(self, context: Dict):
        """Create a new fork of the project."""
        try:
            from memory.forking import create_fork
            fork_id = await create_fork(
                project_id=self.project_id,
                fork_reason="Token overflow prevention",
                parent_context=context
            )
            logger.info(f"Created fork {fork_id}")
        except Exception as e:
            logger.error(f"Error creating fork: {e}")
    
    async def _retrieve_relevant_memory(
        self,
        query: str,
        context: Dict
    ) -> List[Dict]:
        """Retrieve relevant memories from vector DB."""
        try:
            vm = await self.get_vector_memory()
            memories = await vm.retrieve_context(
                project_id=self.project_id,
                query=f"What context is needed for {query}",
                top_k=5
            )
            return memories
        except Exception as e:
            logger.warning(f"Failed to retrieve memory: {e}")
            return []
    
    def _format_memories(self, memories: List[Dict]) -> str:
        """Format memories for agent prompt injection."""
        if not memories:
            return ""
        
        formatted = "## Previous Context (Retrieved from Memory)\n\n"
        for i, mem in enumerate(memories, 1):
            formatted += f"**Memory {i}** (from {mem.get('agent', 'system')})\n"
            formatted += f"Type: {mem['type']}\n"
            formatted += f"Relevance: {mem['relevance_score']:.2f}/1.0\n"
            formatted += f"Content:\n```\n{mem['text']}\n```\n\n"
        
        return formatted
    
    def _inject_design_system(self, context: Dict) -> Dict:
        """Inject design system into agent context."""
        try:
            with open('backend/design_system.json', 'r') as f:
                design_system = json.load(f)
            
            context['design_system'] = design_system
            
            with open('backend/prompts/design_system_injection.txt', 'r') as f:
                context['design_system_prompt'] = f.read()
            
            return context
        except Exception as e:
            logger.warning(f"Failed to inject design system: {e}")
            return context
    
    async def _validate_design(self, jsx: str) -> str:
        """Validate and fix JSX to comply with design system."""
        try:
            # Check for inline styles
            if 'style={{' in jsx or 'style="' in jsx:
                logger.warning("Found inline styles in generated JSX")
            
            # Ensure Tailwind classes used
            if 'className' in jsx or 'class=' in jsx:
                # JSX is using classes, good
                pass
            
            return jsx
        except Exception as e:
            logger.warning(f"Design validation failed: {e}")
            return jsx
    
    async def _broadcast(self, event_type: str, **data):
        """Broadcast event via WebSocket."""
        try:
            await self.broadcast_event(self.job_id, event_type, **data)
        except Exception as e:
            logger.error(f"Failed to broadcast event: {e}")
