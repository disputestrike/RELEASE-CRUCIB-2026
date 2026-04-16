"""
Conversational Chat API: Multi-turn endpoint with agent routing and context management.
Like Copilot - maintains conversation state, routes to appropriate agents, streams responses.
"""

from fastapi import APIRouter, WebSocket, HTTPException, Depends
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

from services.brain_layer import BrainLayer
from services.conversation_manager import ContextManager
from services.events import event_bus
from services.runtime.runtime_engine import runtime_engine
from services.semantic_router import SemanticRouter

# These would be imported from actual implementations
# from services.websocket_handler import WebSocketManager
context_manager = ContextManager()
semantic_router = SemanticRouter()

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Global managers (would be initialized in app startup)
ws_manager = None  # WebSocketManager()


@router.post("/message")
async def send_chat_message(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send message and get agent response.
    Entry point for conversational interactions like Copilot.
    
    Request:
        {
            "session_id": "session_123",
            "message": "analyze this code",
            "context": {...}  # optional additional context
        }
    
    Response:
        {
            "session_id": "session_123",
            "assistant_response": "...",
            "agents_used": [...],
            "intent": "code_analysis",
            "suggestions": [...]
        }
    """
    session_id = request.get("session_id")
    message = request.get("message")

    if not session_id or not message:
        raise HTTPException(status_code=400, detail="Missing session_id or message")

    project_id = (request.get("project_id") or f"chat-{session_id}").strip()

    try:
        # Get or create session
        session = context_manager.get_session(session_id)
        if not session:
            session = context_manager.create_session(session_id)

        runtime_out = await runtime_engine.start_task(
            session=session,
            session_id=session_id,
            project_id=project_id,
            user_message=message,
        )
        task = runtime_out.get("task") or {}
        brain_result = runtime_out.get("brain_result") or {}
        task_id = task.get("task_id")

        session.set_current_task(
            task_description=message,
            task_metadata={
                "task_id": task_id,
                "project_id": project_id,
            },
        )

        assistant_response = brain_result["assistant_response"]
        suggestions = brain_result.get("suggestions", [])
        selected_agents = brain_result.get("selected_agents", [])

        session.add_turn(
            message,
            assistant_response,
            metadata={
                "intent": brain_result.get("intent"),
                "intent_confidence": brain_result.get("intent_confidence"),
                "selected_agents": selected_agents,
                "status": brain_result.get("status"),
                "task_id": task_id,
                "project_id": project_id,
            },
        )

        return {
            "session_id": session_id,
            "project_id": project_id,
            "task_id": task_id,
            "task_status": task.get("status"),
            "assistant_response": assistant_response,
            "agents_used": selected_agents,
            "intent": brain_result.get("intent"),
            "suggestions": suggestions,
            "routing": brain_result.get("routing"),
            "status": brain_result.get("status"),
            "execution": brain_result.get("execution"),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        event_bus.emit(
            "chat.request.failed",
            {
                "session_id": session_id,
                "project_id": project_id,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/session/create")
async def create_session() -> Dict[str, Any]:
    """Create new chat session"""
    import uuid
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    session = context_manager.create_session(session_id)

    return {
        "session_id": session_id,
        "created_at": datetime.now().isoformat(),
    }


@router.get("/session/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """Get session info"""
    session = context_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "summary": session.get_summary(),
        "turn_count": len(session.turns),
    }


@router.post("/session/{session_id}/clear")
async def clear_session(session_id: str) -> Dict[str, str]:
    """Clear session history"""
    session = context_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.clear_history()
    return {"message": "Session cleared"}


@router.delete("/session/{session_id}")
async def delete_session(session_id: str) -> Dict[str, str]:
    """Delete session"""
    if context_manager.delete_session(session_id):
        return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/session/{session_id}/history")
async def get_session_history(session_id: str, format: str = "json") -> str:
    """Export session history"""
    session = context_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if format == "json":
        return session.get_history_json(include_metadata=True)
    elif format == "markdown":
        # Convert to markdown
        markdown = f"# Chat Session {session_id}\n\n"
        for turn in session.turns:
            markdown += f"**User:** {turn.user_input}\n\n"
            markdown += f"**Assistant:** {turn.agent_response}\n\n"
        return markdown
    else:
        raise HTTPException(status_code=400, detail="Invalid format")


@router.post("/suggest")
async def get_suggestions(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get smart suggestions based on current context.
    Like Copilot inline suggestions.
    """
    session_id = request.get("session_id")
    current_input = request.get("current_input", "")

    session = context_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Route current input to understand intent
        routing = semantic_router.route(current_input)

        # Generate contextual suggestions
        suggestions = []

        # Suggest based on detected intent
        if routing["intent"] == "code_analysis":
            suggestions = [
                "Analyze code structure",
                "Check for code quality issues",
                "Detect complexity metrics",
                "Find refactoring opportunities",
            ]
        elif routing["intent"] == "testing":
            suggestions = [
                "Run unit tests",
                "Generate test code",
                "Debug failing tests",
                "Check test coverage",
            ]
        elif routing["intent"] == "exploration":
            suggestions = [
                "Search workspace files",
                "Analyze project structure",
                "Find code patterns",
                "Locate specific functions",
            ]

        # Add context-aware suggestions
        if session.keywords:
            suggestions.append(f"Continue with: {session.keywords[-1]}")

        return {
            "session_id": session_id,
            "suggestions": suggestions[:5],  # Top 5
            "intent": routing["intent"],
        }

    except Exception as e:
        logger.error(f"Suggestion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/list")
async def list_available_agents() -> Dict[str, Any]:
    """List all available agents from the 240-agent DAG"""
    # This would query the actual agent registry
    return {
        "total_agents": 240,
        "categories": {
            "core": ["Planner", "Stack Selector", "Frontend Generation", "Backend Generation"],
            "security": ["Security Checker", "HIPAA Agent", "SOC2 Agent"],
            "ml": ["ML Framework Selector Agent", "ML Training Agent"],
            "blockchain": ["Smart Contract Agent", "Web3 Frontend Agent"],
            "tools": ["Terminal Agent", "File Tool Agent", "API Tool Agent"],
        },
    }


@router.post("/debug/routing")
async def debug_routing(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Debug semantic routing for a message.
    Useful for understanding why certain agents were selected.
    """
    message = request.get("message", "")

    routing = semantic_router.route(message)
    stats = semantic_router.export_routing_stats()

    return {
        "message": message,
        "detected_intent": routing["intent"],
        "intent_confidence": routing["intent_confidence"],
        "primary_agents": routing["primary_agents"],
        "secondary_agents": routing["secondary_agents"],
        "reasoning": routing["reasoning"],
        "routing_stats": stats,
    }


def _compile_response(agent_responses: list) -> str:
    """Compile agent responses into coherent assistant message"""
    if not agent_responses:
        return "No agents executed."

    response_parts = []

    for resp in agent_responses:
        if resp["success"]:
            output = resp.get("output", "")
            if isinstance(output, dict):
                # Extract key findings
                if "result" in output:
                    response_parts.append(str(output["result"]))
                elif "summary" in output:
                    response_parts.append(output["summary"])
                else:
                    response_parts.append(json.dumps(output, default=str)[:500])
            else:
                response_parts.append(str(output)[:500])
        else:
            response_parts.append(f"Agent {resp['agent']} failed: {resp.get('error', 'Unknown error')}")

    return "\n\n".join(response_parts)


def _generate_suggestions(routing: Dict[str, Any], responses: list) -> list:
    """Generate next-step suggestions based on what was just done"""
    suggestions = []

    # Suggest based on intent
    intent = routing.get("intent")

    if intent == "code_analysis" and responses and responses[0].get("success"):
        suggestions = [
            "Refactor the problematic code",
            "Generate unit tests",
            "Check security issues",
        ]
    elif intent == "testing":
        suggestions = [
            "Debug the failing test",
            "Run entire test suite",
            "Check code coverage",
        ]
    elif intent == "execution":
        suggestions = [
            "Deploy to production",
            "Run performance tests",
            "Check deployment status",
        ]

    return suggestions[:3]  # Return top 3 suggestions
