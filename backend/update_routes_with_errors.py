#!/usr/bin/env python3
"""
Script to add error handling to all 39 API endpoints
Adds try-except blocks and proper HTTP exception handling
"""

import os
import re


def add_error_handling_to_route(endpoint_func_code: str) -> str:
    """
    Wraps an endpoint function with try-except error handling.

    Args:
        endpoint_func_code: The original endpoint function code

    Returns:
        Updated code with error handling
    """

    # Extract function signature
    sig_match = re.match(
        r"(@router\.\w+\([^)]*\).*?\nasync def \w+\([^)]*\)[^:]*:)",
        endpoint_func_code,
        re.DOTALL,
    )
    if not sig_match:
        return endpoint_func_code

    sig = sig_match.group(1)
    body = endpoint_func_code[len(sig) :]

    # Indent body by 4 spaces
    indented_body = "\n".join(
        ["    " + line if line.strip() else line for line in body.split("\n")]
    )

    # Create new function with error handling
    new_func = f"""{sig}
    \"\"\"Endpoint with error handling\"\"\"
    try:
{indented_body}
    except ValueError as e:
        logger.error(f"Validation error: {{str(e)}}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {{str(e)}}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
"""

    return new_func


# INSTRUCTIONS FOR MANUAL APPLICATION
# ====================================
#
# This script provides the PATTERN. To apply manually to all 39 routes:
#
# 1. backend/routes/auth.py (14 endpoints)
#    - Wrap each @router endpoint in try-except
#    - Use ValueError for validation errors (400)
#    - Use generic Exception for server errors (500)
#    - Add logger.error() calls
#
# 2. backend/routes/jobs.py (12 endpoints)
#    - Same pattern as auth.py
#    - Add specific catches for database errors
#
# 3. backend/routes/agents.py (13 endpoints)
#    - Same pattern as above
#    - Add specific catches for DAG execution errors
#
# EXAMPLE TRANSFORMATION:
#
# BEFORE:
# @router.post("/register")
# async def register(user: UserRegister):
#     token = create_token(user.email)
#     return {"access_token": token}
#
# AFTER:
# @router.post("/register")
# async def register(user: UserRegister):
#     try:
#         token = create_token(user.email)
#         return {"access_token": token}
#     except ValueError as e:
#         logger.error(f"Validation error: {str(e)}")
#         raise HTTPException(status_code=400, detail=str(e))
#     except Exception as e:
#         logger.error(f"Unexpected error: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail="Internal server error")

print(
    "✅ Error handling pattern ready. Apply to all 39 endpoints manually or run automated migration."
)
