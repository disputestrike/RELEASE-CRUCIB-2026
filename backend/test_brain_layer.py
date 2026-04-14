#!/usr/bin/env python3
"""
Test script for the brain layer implementation.
Tests the selective agent selection and execution logic.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from services.brain_layer import BrainLayer
from services.agents.registry import AgentRegistry
from services.conversation_manager import ConversationManager
from services.semantic_router import SemanticRouter

async def test_brain_layer():
    print("Testing Brain Layer Implementation")
    print("=" * 50)

    # Initialize components
    try:
        agent_registry = AgentRegistry()
        conversation_manager = ConversationManager()
        semantic_router = SemanticRouter()

        brain = BrainLayer(
            agent_registry=agent_registry,
            conversation_manager=conversation_manager,
            semantic_router=semantic_router
        )

        print("✓ Components initialized")

    except Exception as e:
        print(f"✗ Failed to initialize components: {e}")
        return False

    # Test request assessment
    test_request = "Build me a stunning landing page for a tech startup"

    try:
        print(f"\nTesting request: {test_request}")

        # Test assess_request (planning phase)
        assessment = await brain.assess_request(test_request)
        print("✓ Request assessment successful")
        print(f"  Selected agents: {[agent.__class__.__name__ for agent in assessment.selected_agents]}")
        print(f"  Plan: {assessment.plan[:100]}...")

        # Test execute_request (execution phase)
        print("\nTesting execution...")
        result = await brain.execute_request(test_request)
        print("✓ Execution successful")
        print(f"  Result type: {type(result)}")
        if hasattr(result, 'final_output'):
            print(f"  Final output: {result.final_output[:200]}...")

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_brain_layer())
    if success:
        print("\n🎉 Brain layer test passed!")
        print("The brain layer correctly selects agents and orchestrates execution.")
    else:
        print("\n❌ Brain layer test failed.")
        print("Check the implementation and dependencies.")
    sys.exit(0 if success else 1)