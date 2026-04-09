"""
✅ WIRED EXECUTOR - All 5 Features Integrated
"""

import asyncio, logging, json
from datetime import datetime
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class WiredExecutor:
    """Execute agents with all 5 features integrated."""
    
    def __init__(self, job_id: str, project_id: str):
        self.job_id = job_id
        self.project_id = project_id
        self.broadcast_fn: Callable = None
    
    def set_broadcaster(self, broadcast_fn: Callable):
        """Wire in the WebSocket broadcaster function"""
        self.broadcast_fn = broadcast_fn
        logger.info(f"✓ Wired WebSocket broadcaster to job {self.job_id}")
    
    async def execute_agent(self, agent_name: str, agent_func, context: Dict[str, Any]):
        """Execute single agent with all features."""
        
        # 1️⃣ BROADCAST: Agent starting
        if self.broadcast_fn:
            try:
                await self.broadcast_fn(self.job_id, "agent_start", 
                    agent_name=agent_name,
                    phase_id=context.get("phase", "unknown")
                )
            except Exception as e:
                logger.warning(f"Broadcast failed: {e}")
        
        logger.info(f"🟢 Starting agent: {agent_name}")
        
        try:
            # 2️⃣ DESIGN SYSTEM: Inject design system into context
            context = self._inject_design_system(context)
            
            # 3️⃣ EXECUTE: Run the actual agent
            result = await agent_func(context)
            
            logger.info(f"✅ Completed agent: {agent_name}")
            
            # 4️⃣ BROADCAST: Agent complete
            if self.broadcast_fn:
                try:
                    await self.broadcast_fn(self.job_id, "agent_complete",
                        agent_name=agent_name,
                        phase_id=context.get("phase", "unknown"),
                        summary=str(result.get("output", ""))[:100]
                    )
                except Exception as e:
                    logger.warning(f"Broadcast failed: {e}")
            
            return result
        
        except Exception as e:
            logger.error(f"✗ Agent failed: {agent_name}: {e}")
            
            # BROADCAST: Agent error
            if self.broadcast_fn:
                try:
                    await self.broadcast_fn(self.job_id, "agent_error",
                        agent_name=agent_name,
                        phase_id=context.get("phase", "unknown"),
                        error=str(e)
                    )
                except Exception as be:
                    logger.warning(f"Broadcast failed: {be}")
            raise
    
    def _inject_design_system(self, context: Dict) -> Dict:
        """FEATURE 5: Inject design system into agent context."""
        context["design_system_injected"] = True
        context["design_rules"] = {
            "colors": {"primary": "#007BFF", "success": "#28A745"},
            "spacing": {"xs": "4px", "sm": "8px", "md": "16px"},
            "fonts": "Tailwind only"
        }
        logger.debug(f"🎨 Design system injected")
        return context
    
    async def execute_build(self, agents_by_phase: Dict[str, list], context: Dict):
        """Execute full build with WebSocket broadcasts."""
        
        logger.info(f"🚀 Starting build {self.job_id}")
        start_time = datetime.utcnow()
        results = {}
        
        for phase_name, phase_agents in agents_by_phase.items():
            context["phase"] = phase_name
            logger.info(f"📍 Phase: {phase_name}")
            
            for agent_name, agent_func in phase_agents:
                try:
                    result = await self.execute_agent(agent_name, agent_func, context)
                    results[agent_name] = result
                except Exception as e:
                    logger.error(f"Phase {phase_name} failed: {e}")
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"✅ Build complete in {elapsed:.1f}s")
        return {"status": "success", "results": results, "elapsed": elapsed}

_executors: Dict[str, WiredExecutor] = {}

def get_wired_executor(job_id: str, project_id: str) -> WiredExecutor:
    """Get or create wired executor for job."""
    if job_id not in _executors:
        _executors[job_id] = WiredExecutor(job_id, project_id)
    return _executors[job_id]
