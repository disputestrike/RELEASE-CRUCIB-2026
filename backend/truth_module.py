"""Truth module for adversarial self-critique"""
import json
import os
from typing import Dict, List

async def truth_check(
    project_id: str,
    build_output: dict,
    llm_caller
) -> dict:
    """Adversarial self-critique on build output"""
    
    prompt = f"""You are an adversarial reviewer. Examine this build output and identify:

1. Placeholder functions that don't actually implement logic
2. Imports that reference non-existent modules  
3. API endpoints that return hardcoded data instead of database queries
4. Claims in comments that don't match the code
5. Frontend calls to backend endpoints that don't exist
6. Missing error handling
7. Security vulnerabilities
8. Type mismatches between frontend and backend

Build output:
{json.dumps(build_output, indent=2)[:50000]}

Respond with JSON:
{{
    "honest_score": 0-100,
    "issues": [
        {{"type": "placeholder|missing|hardcoded|mismatch|security", "location": "file:line", "description": "..."}}
    ],
    "verdict": "PASS" or "FAIL",
    "recommendations": ["..."]
}}
"""
    
    try:
        response = await llm_caller(
            message=prompt,
            system_message="You are a critical code reviewer focused on honesty and accuracy.",
            session_id=f"truth_check_{project_id}",
            model_chain="pro"
        )
        
        # Parse JSON response
        result = json.loads(response)
        return {
            "success": True,
            "honest_score": result.get("honest_score", 0),
            "issues": result.get("issues", []),
            "verdict": result.get("verdict", "UNKNOWN"),
            "recommendations": result.get("recommendations", [])
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": "Failed to parse LLM response",
            "honest_score": 0,
            "verdict": "FAIL"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "honest_score": 0,
            "verdict": "FAIL"
        }

async def verify_code_honesty(
    code_content: str,
    file_path: str,
    llm_caller
) -> dict:
    """Verify that code claims match implementation"""
    
    prompt = f"""Review this code for honesty. Check if:
1. Comments accurately describe what the code does
2. Function names match their behavior
3. Error messages are truthful
4. No hardcoded values masquerade as dynamic

File: {file_path}
Code:
{code_content[:5000]}

Respond with JSON:
{{
    "is_honest": true/false,
    "issues": ["..."],
    "confidence": 0-100
}}
"""
    
    try:
        response = await llm_caller(
            message=prompt,
            system_message="You are a code honesty auditor.",
            session_id=f"honesty_{file_path}",
            model_chain="pro"
        )
        
        result = json.loads(response)
        return {
            "success": True,
            "is_honest": result.get("is_honest", False),
            "issues": result.get("issues", []),
            "confidence": result.get("confidence", 0)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
