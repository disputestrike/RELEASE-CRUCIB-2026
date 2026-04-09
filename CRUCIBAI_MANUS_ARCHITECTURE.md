# CrucibAI: Manus-Style Architecture Roadmap

## 🧠 PHASE 1: ADD THINKING (OPTION B - MANUS HYBRID)

### What Manus Does:
```
1. PLAN phase: Heavy thinking (2-3 LLM calls to reason through problem)
2. EXECUTE phase: Follow plan, no re-thinking per step
3. OBSERVE phase: Check result, re-think ONLY on failure
4. PERSIST: Save plan to file so all agents see the reasoning
```

### Implementation for CrucibAI:

#### Step 1: Create PlannerAgent with Thinking
```python
# backend/agents/crucibai_planner_with_thinking.py

class CrucibAIPlannerWithThinking:
    """
    Manus-style planner that:
    1. Analyzes goal deeply
    2. Creates step-by-step plan
    3. Saves to plan.md in workspace
    4. Each agent follows the plan
    """
    
    async def create_plan_with_thinking(self, goal: str):
        # THINK: Analyze the goal
        analysis = await self.llm.generate(f"""
        You are the strategic planner for a code generation system.
        
        User wants: {goal}
        
        THINK DEEPLY:
        1. What is the user REALLY asking for?
        2. What components are needed?
        3. What's the correct build order?
        4. What dependencies exist between steps?
        5. What could go wrong at each step?
        6. How will we verify each step succeeded?
        7. What's the rollback plan?
        
        Output your analysis as structured thinking.
        """, 
        model="claude-opus-4-1",  # Use best model for thinking
        max_tokens=2000
        )
        
        # PLAN: Generate detailed steps
        plan = await self.llm.generate(f"""
        Based on this analysis of what needs to be built:
        {analysis}
        
        Create a detailed, sequential build plan.
        
        Format:
        ## Build Plan
        
        ### Step 1: [Name]
        **Agent**: [Which agent will do this]
        **Dependencies**: [What must be done first]
        **Success Criteria**: [How to verify]
        **Risk**: [What could go wrong]
        **Rollback**: [If it fails, what to do]
        
        ### Step 2: ...
        ...
        
        **Total Steps**: N
        """,
        model="claude-opus-4-1",
        max_tokens=3000
        )
        
        # PERSIST: Save to workspace
        self.write_file("plan.md", plan)
        self.write_file("analysis.md", analysis)
        
        return {
            "analysis": analysis,
            "plan": plan,
            "saved_to": ["plan.md", "analysis.md"]
        }
```

#### Step 2: Modify ExecutorWithThinking
```python
# backend/orchestration/executor_with_thinking.py

async def execute_with_plan_and_thinking(job_id, goal, workspace_path):
    """
    Execute following Manus pattern:
    ANALYZE → PLAN → EXECUTE → OBSERVE → RECOVER
    """
    
    # STEP 1: PLAN (with thinking)
    planner = CrucibAIPlannerWithThinking()
    plan_result = await planner.create_plan_with_thinking(goal)
    
    plan_steps = parse_plan_md(plan_result["plan"])
    current_step = 0
    
    # STEP 2: EXECUTE each step
    for step_num, step in enumerate(plan_steps):
        current_step = step_num
        
        # Update plan: mark as in progress
        update_plan_md(workspace_path, step_num, "IN_PROGRESS")
        
        try:
            # Execute the step
            result = await execute_step(
                step_name=step["name"],
                agent_name=step["agent"],
                dependencies=step["dependencies"],
                workspace_path=workspace_path,
                context={
                    "plan": plan_steps,
                    "current_step": step_num,
                    "analysis": plan_result["analysis"]
                }
            )
            
            # OBSERVE: Check if successful
            if result["status"] == "SUCCESS":
                update_plan_md(workspace_path, step_num, "DONE")
                
            elif result["status"] == "FAILURE":
                # THINK about failure (option B - only re-think on error)
                error_analysis = await self.llm.generate(f"""
                Step {step_num} ({step['name']}) failed.
                
                Error: {result['error']}
                
                Think about:
                1. Why did this fail?
                2. Is it a real blocker or recoverable?
                3. What's the fix?
                4. Should we retry or skip?
                5. Does the plan need updating?
                """,
                max_tokens=1500
                )
                
                # Decide: retry, skip, or fail
                recovery = await decide_recovery(error_analysis, step)
                
                if recovery["action"] == "RETRY":
                    result = await execute_step_with_fix(step, recovery["fix"])
                    update_plan_md(workspace_path, step_num, "DONE_WITH_FIX")
                elif recovery["action"] == "SKIP":
                    update_plan_md(workspace_path, step_num, "SKIPPED")
                else:  # FAIL
                    update_plan_md(workspace_path, step_num, "FAILED")
                    raise RuntimeError(f"Step {step_num} unrecoverable: {result['error']}")
        
        except Exception as e:
            update_plan_md(workspace_path, step_num, "ERROR")
            raise
    
    return {
        "status": "SUCCESS",
        "steps_completed": len(plan_steps),
        "plan_file": "plan.md"
    }
```

---

## 🚀 PHASE 2: PARALLEL PROCESSING

### Current State (Sequential within phases):
```
Phase 1: Planner (1 agent)
Phase 2: Requirements + Stack (7 agents in parallel) ✓
Phase 3: Core Generation (8 agents in parallel) ✓
Phase 4: Enhancement (19 agents in parallel) ✓
Phase 5: Expansion (77 agents, but batched) ✗ BOTTLENECK
Phase 6: Quality Gates (50 agents, but batched) ✗ BOTTLENECK
```

### Target State (True Parallel):
```
After PLAN phase:
- All agents that have satisfied dependencies run SIMULTANEOUSLY
- Shared workspace with atomic file operations
- Real-time coordination via events
```

### Implementation:

#### Step 1: AsyncIO-based Parallel Executor
```python
# backend/orchestration/parallel_executor.py

async def execute_agents_in_parallel(
    selected_agents: List[str],
    workspace_path: str,
    shared_context: Dict
):
    """
    Run all agents that have satisfied dependencies in parallel.
    Use asyncio.gather for true concurrency.
    """
    
    # Build dependency graph
    dag = AGENT_DAG
    ready_agents = []
    pending_agents = set(selected_agents)
    completed_agents = set()
    
    while pending_agents:
        # Find agents with satisfied dependencies
        for agent_name in pending_agents:
            deps = dag[agent_name].get("depends_on", [])
            if all(d in completed_agents for d in deps):
                ready_agents.append(agent_name)
        
        pending_agents -= set(ready_agents)
        
        # Run all ready agents in PARALLEL
        if ready_agents:
            tasks = [
                execute_agent_async(
                    agent_name,
                    workspace_path,
                    shared_context,
                    completed_agents
                )
                for agent_name in ready_agents
            ]
            
            # Wait for ALL to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for agent_name, result in zip(ready_agents, results):
                if isinstance(result, Exception):
                    # Handle agent failure
                    shared_context["failures"][agent_name] = str(result)
                else:
                    completed_agents.add(agent_name)
                    shared_context["completions"][agent_name] = result
            
            ready_agents = []
    
    return {
        "completed": len(completed_agents),
        "total": len(selected_agents),
        "failures": shared_context["failures"],
        "results": shared_context["completions"]
    }

async def execute_agent_async(
    agent_name: str,
    workspace_path: str,
    shared_context: Dict,
    completed_deps: set
):
    """Execute single agent asynchronously."""
    agent_config = AGENT_DAG[agent_name]
    
    # Build agent with context
    agent = build_agent_from_config(
        agent_config,
        workspace_path,
        shared_context
    )
    
    # Execute with timeout
    result = await asyncio.wait_for(
        agent.execute(shared_context),
        timeout=60  # 60 second timeout per agent
    )
    
    return result
```

#### Step 2: Atomic File Operations (avoid conflicts)
```python
# backend/orchestration/atomic_workspace.py

class AtomicWorkspace:
    """
    Thread-safe workspace operations so multiple agents
    can write simultaneously without conflicts.
    """
    
    def __init__(self, workspace_path: str):
        self.path = workspace_path
        self.lock = asyncio.Lock()
        self.file_versions = {}
    
    async def write_file_atomic(self, file_path: str, content: str, agent_name: str):
        """
        Write file atomically:
        1. Write to temp file
        2. Lock
        3. Merge or overwrite
        4. Unlock
        """
        async with self.lock:
            temp_path = f"{file_path}.tmp.{agent_name}"
            
            # Write temp
            with open(temp_path, 'w') as f:
                f.write(content)
            
            # Check for conflicts
            if os.path.exists(file_path):
                existing = read_file(file_path)
                # Try to merge if both modified same file
                if can_merge(existing, content):
                    merged = merge_contents(existing, content)
                    with open(file_path, 'w') as f:
                        f.write(merged)
                else:
                    # Last write wins (could add versioning)
                    os.rename(temp_path, file_path)
            else:
                os.rename(temp_path, file_path)
    
    async def read_file_atomic(self, file_path: str):
        """Read latest version of file."""
        async with self.lock:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    return f.read()
            return None
```

#### Step 3: Coordinate via Event Bus
```python
# backend/orchestration/parallel_coordination.py

class ParallelCoordinator:
    """Coordinate parallel agents via event bus."""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.event_bus = EventBus()
        self.agent_states = {}
    
    async def register_agent(self, agent_name: str):
        """Register agent as starting."""
        await self.event_bus.publish(f"agent.start.{agent_name}", {
            "job": self.job_id,
            "agent": agent_name,
            "timestamp": time.time()
        })
    
    async def notify_agent_complete(self, agent_name: str, result: Dict):
        """Notify other agents when one completes."""
        await self.event_bus.publish(f"agent.complete.{agent_name}", {
            "job": self.job_id,
            "agent": agent_name,
            "result": result
        })
    
    async def wait_for_agent(self, agent_name: str, depends_on: List[str]):
        """Agent waits for its dependencies."""
        for dep in depends_on:
            await self.event_bus.subscribe_until(
                f"agent.complete.{dep}",
                timeout=300
            )
```

---

## 🔥 PHASE 3: FIX PREVIEW + SECURITY

### Current Issue:
- Preview verifier failing on generated code
- Security agent not catching issues before they break preview

### Solution:

#### Step 1: Add PreviewValidator Agent with Thinking
```python
# backend/agents/preview_validator_agent.py

class PreviewValidatorAgent:
    """
    Think about what COULD break in preview,
    then validate before preview attempts to run.
    """
    
    async def execute(self, context):
        generated_app = context["generated_app"]
        
        # THINK: What could break?
        thinking = await self.llm.generate(f"""
        Looking at this generated React app:
        {generated_app['package_json']}
        {generated_app['vite_config']}
        {generated_app['src_main'][:500]}...
        
        What could prevent this from:
        1. Building with vite?
        2. Running in the browser?
        3. Rendering without errors?
        
        Think about:
        - Missing dependencies
        - Import path issues
        - Invalid JSX
        - Missing exports
        - Circular dependencies
        """,
        max_tokens=2000
        )
        
        # VALIDATE based on thinking
        checks = [
            self.validate_package_json(generated_app),
            self.validate_vite_config(generated_app),
            self.validate_imports(generated_app),
            self.validate_jsx_syntax(generated_app),
            self.validate_dependencies_exist(generated_app),
        ]
        
        results = await asyncio.gather(*checks)
        
        # Return findings + fixes
        return {
            "status": "SUCCESS" if all(r["pass"] for r in results) else "ISSUES_FOUND",
            "thinking": thinking,
            "validations": results,
            "suggested_fixes": self.generate_fixes(results)
        }
```

#### Step 2: Security Agent that Validates First
```python
# backend/agents/security_validator_agent.py

class SecurityValidatorAgent:
    """
    Catch security issues BEFORE preview runs.
    """
    
    async def execute(self, context):
        # THINK: What are the security risks?
        risks = await self.llm.generate(f"""
        Analyze this code for security issues:
        
        {context['backend_code'][:1000]}
        {context['frontend_code'][:1000]}
        
        Check for:
        1. SQL injection vulnerabilities
        2. XSS issues
        3. CSRF protection
        4. Authentication bypasses
        5. Exposed secrets
        6. Path traversal
        7. Rate limiting
        """,
        max_tokens=2000
        )
        
        # VALIDATE
        security_checks = [
            self.scan_for_secrets(context),
            self.check_sql_safety(context),
            self.check_xss_vectors(context),
            self.check_auth_bypass(context),
        ]
        
        results = await asyncio.gather(*security_checks)
        
        # Block if critical
        critical = [r for r in results if r["severity"] == "CRITICAL"]
        
        return {
            "status": "BLOCKED" if critical else "PASS",
            "issues": results,
            "critical_count": len(critical),
            "suggestions": self.suggest_fixes(results)
        }
```

---

## 📋 IMPLEMENTATION CHECKLIST

### Week 1: Planning + Thinking
- [ ] Create `CrucibAIPlannerWithThinking` class
- [ ] Integrate into planner.py routing
- [ ] Test: Verify plan.md is created and readable
- [ ] Test: Verify agents can read and follow the plan

### Week 2: Parallel Processing
- [ ] Create `ParallelExecutor` with asyncio
- [ ] Create `AtomicWorkspace` for safe concurrent writes
- [ ] Create `ParallelCoordinator` for event bus
- [ ] Test: Run 10 agents in parallel, verify no file conflicts

### Week 3: Preview + Security
- [ ] Create `PreviewValidatorAgent` with thinking
- [ ] Create `SecurityValidatorAgent` with thinking
- [ ] Wire into DAG with HIGH priority
- [ ] Test: Run preview, verify it catches issues before failure

### Week 4: Integration + Testing
- [ ] End-to-end test: Create plan → Execute parallel → Validate → Preview
- [ ] Load test: 50 agents in parallel
- [ ] Failure test: Agent fails, plan updates, continue
- [ ] Performance benchmark: Time to 88/88

---

## 🎯 EXPECTED OUTCOME

Before:
```
Sequential execution, 237 agents, 83/88 achieved, preview fails
```

After:
```
Plan-based execution with thinking, 237 agents running in parallel,
88/88 achieved, preview catches issues before they break
```

Cost increase: ~20% more LLM calls (thinking on plan + errors only)
Speed gain: ~3-5x (parallel agents instead of sequential phases)
Quality gain: Thinking prevents downstream failures
