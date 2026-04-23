"""
Simple integration test for Cerebras API and agent system.
Tests actual API connectivity and basic agent functionality.
"""

import asyncio
import os
from llm_cerebras import invoke_cerebras, CerebrasClient


async def test_cerebras_api():
    """Test Cerebras API connectivity"""
    print("\n" + "="*70)
    print("CEREBRAS API INTEGRATION TEST")
    print("="*70)
    
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        print("❌ CEREBRAS_API_KEY not set")
        return False
    
    try:
        print("\n🧪 Testing Cerebras API...")
        
        response = await invoke_cerebras(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is 2+2? Answer in one sentence."}
            ],
            max_tokens=50,
            temperature=0.7
        )
        
        content = response["choices"][0]["message"]["content"]
        tokens = response.get("usage", {})
        
        print(f"✅ Cerebras API: WORKING")
        print(f"   Response: {content}")
        print(f"   Tokens - Input: {tokens.get('prompt_tokens', 0)}, Output: {tokens.get('completion_tokens', 0)}")
        
        return True
    
    except Exception as e:
        print(f"❌ Cerebras API: FAILED")
        print(f"   Error: {str(e)[:200]}")
        return False


async def test_cerebras_streaming():
    """Test Cerebras streaming API"""
    print("\n" + "="*70)
    print("CEREBRAS STREAMING TEST")
    print("="*70)
    
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        print("❌ CEREBRAS_API_KEY not set")
        return False
    
    try:
        print("\n🧪 Testing Cerebras streaming...")
        
        client = CerebrasClient(api_key)
        
        print("   Response: ", end="", flush=True)
        async for chunk in client.chat_completion_stream(
            messages=[
                {"role": "user", "content": "Say 'Streaming works!' in one sentence."}
            ],
            max_tokens=50
        ):
            print(chunk, end="", flush=True)
        
        print("\n✅ Cerebras streaming: WORKING")
        
        await client.close()
        return True
    
    except Exception as e:
        print(f"\n❌ Cerebras streaming: FAILED")
        print(f"   Error: {str(e)[:200]}")
        return False


async def test_agent_with_cerebras():
    """Test agent using Cerebras"""
    print("\n" + "="*70)
    print("AGENT WITH CEREBRAS TEST")
    print("="*70)
    
    try:
        from agents.base_agent import BaseAgent
        
        print("\n🧪 Testing agent with Cerebras...")
        
        class TestAgent(BaseAgent):
            async def execute(self, context):
                # Use Cerebras to generate a response
                prompt = context.get("prompt", "What is AI?")
                
                response, tokens = await self.call_llm(
                    user_prompt=prompt,
                    system_prompt="You are a helpful AI assistant.",
                    model="cerebras",
                    max_tokens=100
                )
                
                return {
                    "response": response,
                    "tokens_used": tokens,
                    "model": "cerebras"
                }
        
        agent = TestAgent()
        
        result = await agent.execute({"prompt": "What is machine learning? Answer in one sentence."})
        
        print(f"✅ Agent with Cerebras: WORKING")
        print(f"   Response: {result['response'][:100]}...")
        print(f"   Tokens: {result['tokens_used']}")
        
        return True
    
    except Exception as e:
        print(f"❌ Agent with Cerebras: FAILED")
        print(f"   Error: {str(e)[:200]}")
        return False


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("CRUCIBAI AGENT SYSTEM INTEGRATION TESTS")
    print("="*70)
    
    results = []
    
    # Test Cerebras API
    results.append(("Cerebras API", await test_cerebras_api()))
    
    # Test Cerebras streaming
    results.append(("Cerebras Streaming", await test_cerebras_streaming()))
    
    # Test agent with Cerebras
    results.append(("Agent with Cerebras", await test_agent_with_cerebras()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
