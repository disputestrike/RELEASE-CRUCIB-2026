"""
Unit tests for FrontendAgent and BackendAgent.
Tests LLM integration and output validation.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))


async def test_frontend_agent():
    """Test FrontendAgent code generation."""
    print("\n" + "="*60)
    print("TEST: FrontendAgent")
    print("="*60)
    
    try:
        from backend.agents.frontend_agent import FrontendAgent
        
        agent = FrontendAgent()
        context = {
            "user_prompt": "Create a simple React landing page with header, hero section, and footer. Use TailwindCSS for styling.",
        }
        
        print(f"✓ FrontendAgent instantiated")
        print(f"✓ Running execute() with context...")
        
        result = await agent.execute(context)
        
        # Validation checks
        assert "files" in result, "Missing 'files' in output"
        assert isinstance(result["files"], dict), "files must be dict"
        assert "package.json" in result["files"], "Missing package.json"
        assert "structure" in result, "Missing 'structure'"
        assert "setup_instructions" in result, "Missing 'setup_instructions'"
        
        # Code quality checks
        files = result["files"]
        total_size = sum(len(str(c)) for c in files.values())
        
        assert total_size > 500, f"Generated code too small: {total_size} chars"
        
        # Check for real React code
        app_code = files.get("src/App.tsx", "") or files.get("src/App.jsx", "")
        assert "import" in app_code or "React" in str(files), "No React imports found"
        
        print(f"✓ Generated {len(files)} files")
        print(f"✓ Total code size: {total_size} characters")
        print(f"✓ Files: {', '.join(files.keys())[:100]}...")
        print(f"\n✅ FrontendAgent TEST PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ FrontendAgent TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_backend_agent():
    """Test BackendAgent code generation."""
    print("\n" + "="*60)
    print("TEST: BackendAgent")
    print("="*60)
    
    try:
        from backend.agents.backend_agent import BackendAgent
        
        agent = BackendAgent()
        context = {
            "user_prompt": "Create a FastAPI backend with user management. Include endpoints for listing users, creating users, and getting user by ID. Use PostgreSQL.",
        }
        
        print(f"✓ BackendAgent instantiated")
        print(f"✓ Running execute() with context...")
        
        result = await agent.execute(context)
        
        # Validation checks
        assert "files" in result, "Missing 'files' in output"
        assert isinstance(result["files"], dict), "files must be dict"
        assert "api_spec" in result, "Missing 'api_spec'"
        assert "setup_instructions" in result, "Missing 'setup_instructions'"
        assert "endpoints" in result["api_spec"], "Missing endpoints in api_spec"
        
        # Code quality checks
        files = result["files"]
        total_size = sum(len(str(c)) for c in files.values())
        
        assert total_size > 500, f"Generated code too small: {total_size} chars"
        
        # Check for real FastAPI code
        main_code = files.get("main.py", "")
        assert "FastAPI" in main_code or "fastapi" in main_code, "No FastAPI imports found"
        
        endpoints = result["api_spec"]["endpoints"]
        assert len(endpoints) > 0, "No API endpoints generated"
        
        print(f"✓ Generated {len(files)} files")
        print(f"✓ Total code size: {total_size} characters")
        print(f"✓ API Endpoints: {len(endpoints)}")
        print(f"✓ Files: {', '.join(files.keys())[:100]}...")
        print(f"\n✅ BackendAgent TEST PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ BackendAgent TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_handler_integration():
    """Test handler integration with agents."""
    print("\n" + "="*60)
    print("TEST: Handler Integration")
    print("="*60)
    
    try:
        import tempfile
        import shutil
        from backend.orchestration.executor import handle_frontend_generate, handle_backend_route
        
        # Create temp workspace
        tmpdir = tempfile.mkdtemp()
        print(f"✓ Created temp workspace: {tmpdir}")
        
        # Test frontend handler
        step = {"step_key": "frontend.scaffold", "id": "test1"}
        job = {
            "id": "job123",
            "goal": "Build a simple dashboard with charts and user profile section",
        }
        
        print(f"✓ Testing frontend handler...")
        result = await handle_frontend_generate(step, job, tmpdir)
        
        assert result["output_files"], "Frontend handler produced no files"
        print(f"✓ Frontend handler output: {len(result['output_files'])} files")
        
        # Test backend handler
        step = {"step_key": "backend.routes", "id": "test2"}
        print(f"✓ Testing backend handler...")
        result = await handle_backend_route(step, job, tmpdir)
        
        assert result["output_files"], "Backend handler produced no files"
        print(f"✓ Backend handler output: {len(result['output_files'])} files")
        
        # Cleanup
        shutil.rmtree(tmpdir)
        print(f"✓ Cleaned up temp workspace")
        print(f"\n✅ Handler Integration TEST PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Handler Integration TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "🧪 RUNNING CHECKPOINT 4: UNIT TESTS")
    print("="*60)
    
    results = {}
    
    # Run tests
    results["FrontendAgent"] = await test_frontend_agent()
    results["BackendAgent"] = await test_backend_agent()
    results["Handlers"] = await test_handler_integration()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n" + "🎉 ALL TESTS PASSED - READY FOR INTEGRATION")
    else:
        print("\n" + "⚠️ SOME TESTS FAILED - FIX REQUIRED")
    
    return all_passed


if __name__ == "__main__":
    passed = asyncio.run(main())
    sys.exit(0 if passed else 1)
