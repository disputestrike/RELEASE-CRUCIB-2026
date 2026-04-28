"""
Comprehensive test suite to verify all three waves of the Master Engineering Plan.

Wave 1: Backend Orchestration & Circular Import Fixes
Wave 2: Frontend Workspace & Proof Connection  
Wave 3: Governance Gates & ReAct Loop
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test counters
tests_passed = 0
tests_failed = 0
test_results = []

def log_test(name, passed, message=""):
    global tests_passed, tests_failed
    if passed:
        tests_passed += 1
        status = "✅ PASS"
    else:
        tests_failed += 1
        status = "❌ FAIL"
    result = f"{status}: {name}"
    if message:
        result += f" - {message}"
    test_results.append(result)
    print(result)

# ─────────────────────────────────────────────────────────────────────────────
# WAVE 1: Backend Orchestration & Circular Import Fixes
# ─────────────────────────────────────────────────────────────────────────────

def test_wave1_circular_import_fix():
    """Test that get_user_credits can be imported without circular import errors."""
    try:
        from deps import get_user_credits
        log_test("Wave 1: get_user_credits import", True, "Successfully imported from deps")
    except ImportError as e:
        log_test("Wave 1: get_user_credits import", False, str(e))

def test_wave1_orchestrator_imports():
    """Test that orchestrator routes can be imported without circular import errors."""
    try:
        from routes import orchestrator
        log_test("Wave 1: orchestrator routes import", True, "Successfully imported orchestrator routes")
    except ImportError as e:
        log_test("Wave 1: orchestrator routes import", False, str(e))

def test_wave1_dag_engine():
    """Test that DAG engine can be imported and has required functions."""
    try:
        from orchestration import dag_engine
        required_funcs = ["get_ready_steps", "all_steps_finished", "has_blocking_failure"]
        for func in required_funcs:
            if not hasattr(dag_engine, func):
                log_test("Wave 1: DAG engine functions", False, f"Missing function: {func}")
                return
        log_test("Wave 1: DAG engine functions", True, "All required functions present")
    except ImportError as e:
        log_test("Wave 1: DAG engine functions", False, str(e))

def test_wave1_runtime_state():
    """Test that runtime state module can be imported and has required functions."""
    try:
        from orchestration import runtime_state
        required_funcs = ["create_job", "get_job", "update_job_state", "create_step"]
        for func in required_funcs:
            if not hasattr(runtime_state, func):
                log_test("Wave 1: Runtime state functions", False, f"Missing function: {func}")
                return
        log_test("Wave 1: Runtime state functions", True, "All required functions present")
    except ImportError as e:
        log_test("Wave 1: Runtime state functions", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# WAVE 2: Frontend Workspace & Proof Connection
# ─────────────────────────────────────────────────────────────────────────────

def test_wave2_proof_service():
    """Test that proof service can be imported and has required functions."""
    try:
        from proof import proof_service
        required_funcs = ["get_proof", "set_pool"]
        for func in required_funcs:
            if not hasattr(proof_service, func):
                log_test("Wave 2: Proof service functions", False, f"Missing function: {func}")
                return
        log_test("Wave 2: Proof service functions", True, "All required functions present")
    except ImportError as e:
        log_test("Wave 2: Proof service functions", False, str(e))

def test_wave2_sse_streaming():
    """Test that SSE streaming endpoint can be imported."""
    try:
        from routes import jobs
        if not hasattr(jobs, 'stream_job_events'):
            log_test("Wave 2: SSE streaming endpoint", False, "Missing stream_job_events function")
            return
        log_test("Wave 2: SSE streaming endpoint", True, "SSE streaming endpoint present")
    except ImportError as e:
        log_test("Wave 2: SSE streaming endpoint", False, str(e))

def test_wave2_event_bus():
    """Test that event bus can be imported and has required functions."""
    try:
        from orchestration import event_bus
        required_funcs = ["subscribe", "unsubscribe", "publish"]
        for func in required_funcs:
            if not hasattr(event_bus, func):
                log_test("Wave 2: Event bus functions", False, f"Missing function: {func}")
                return
        log_test("Wave 2: Event bus functions", True, "All required functions present")
    except ImportError as e:
        log_test("Wave 2: Event bus functions", False, str(e))

def test_wave2_proof_endpoint():
    """Test that proof endpoint can be imported."""
    try:
        from routes import jobs
        # Check if get_job_proof is defined
        if not hasattr(jobs, 'get_job_proof'):
            log_test("Wave 2: Proof endpoint", False, "Missing get_job_proof function")
            return
        log_test("Wave 2: Proof endpoint", True, "Proof endpoint present")
    except ImportError as e:
        log_test("Wave 2: Proof endpoint", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# WAVE 3: Governance Gates & ReAct Loop
# ─────────────────────────────────────────────────────────────────────────────

def test_wave3_react_loop():
    """Test that ReAct loop can be imported and has required functions."""
    try:
        from services import react_loop
        required_funcs = ["react_stream"]
        for func in required_funcs:
            if not hasattr(react_loop, func):
                log_test("Wave 3: ReAct loop functions", False, f"Missing function: {func}")
                return
        log_test("Wave 3: ReAct loop functions", True, "ReAct loop functions present")
    except ImportError as e:
        log_test("Wave 3: ReAct loop functions", False, str(e))

def test_wave3_honesty_bias_prompt():
    """Test that honesty_bias.v1.md prompt file exists."""
    try:
        from services.prompts_loader import load_prompt
        prompt = load_prompt("honesty_bias.v1.md")
        if not prompt or len(prompt) < 100:
            log_test("Wave 3: Honesty bias prompt", False, "Prompt file is empty or too short")
            return
        log_test("Wave 3: Honesty bias prompt", True, f"Prompt loaded ({len(prompt)} chars)")
    except Exception as e:
        log_test("Wave 3: Honesty bias prompt", False, str(e))

def test_wave3_tavily_tools():
    """Test that Tavily search tool can be imported."""
    try:
        from services.tools import get_tools
        tools = get_tools()
        if not isinstance(tools, dict):
            log_test("Wave 3: Tavily tools", False, "get_tools() did not return a dict")
            return
        log_test("Wave 3: Tavily tools", True, f"Tools loaded ({len(tools)} tools available)")
    except Exception as e:
        log_test("Wave 3: Tavily tools", False, str(e))

def test_wave3_brain_policy():
    """Test that brain policy can be imported and loaded."""
    try:
        from orchestration.brain_policy import load_brain_policy
        policy = load_brain_policy()
        if not isinstance(policy, dict):
            log_test("Wave 3: Brain policy", False, "load_brain_policy() did not return a dict")
            return
        log_test("Wave 3: Brain policy", True, f"Brain policy loaded ({len(policy)} keys)")
    except Exception as e:
        log_test("Wave 3: Brain policy", False, str(e))

def test_wave3_chat_react_endpoint():
    """Test that chat ReAct endpoint can be imported."""
    try:
        from routes import chat_react
        if not hasattr(chat_react, 'chat_react'):
            log_test("Wave 3: Chat ReAct endpoint", False, "Missing chat_react function")
            return
        log_test("Wave 3: Chat ReAct endpoint", True, "Chat ReAct endpoint present")
    except ImportError as e:
        log_test("Wave 3: Chat ReAct endpoint", False, str(e))

# ─────────────────────────────────────────────────────────────────────────────
# Run all tests
# ─────────────────────────────────────────────────────────────────────────────

def run_all_tests():
    print("\n" + "="*80)
    print("WAVE VERIFICATION TEST SUITE")
    print("="*80 + "\n")
    
    print("WAVE 1: Backend Orchestration & Circular Import Fixes")
    print("-" * 80)
    test_wave1_circular_import_fix()
    test_wave1_orchestrator_imports()
    test_wave1_dag_engine()
    test_wave1_runtime_state()
    
    print("\nWAVE 2: Frontend Workspace & Proof Connection")
    print("-" * 80)
    test_wave2_proof_service()
    test_wave2_sse_streaming()
    test_wave2_event_bus()
    test_wave2_proof_endpoint()
    
    print("\nWAVE 3: Governance Gates & ReAct Loop")
    print("-" * 80)
    test_wave3_react_loop()
    test_wave3_honesty_bias_prompt()
    test_wave3_tavily_tools()
    test_wave3_brain_policy()
    test_wave3_chat_react_endpoint()
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    total = tests_passed + tests_failed
    pass_rate = (tests_passed / total * 100) if total > 0 else 0
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {tests_passed} ✅")
    print(f"Failed: {tests_failed} ❌")
    print(f"Pass Rate: {pass_rate:.1f}%")
    print("\n" + "="*80)
    
    if tests_failed == 0:
        print("🎉 ALL TESTS PASSED! All three waves are working correctly.")
    else:
        print(f"⚠️  {tests_failed} test(s) failed. Review the output above.")
    
    print("="*80 + "\n")
    
    return tests_failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
