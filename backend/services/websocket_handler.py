"""
WebSocket Handler: Real-time streaming of agent execution, tool calls, and responses.
Provides live updates like Copilot chat streaming.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamMessage:
    """Message sent over WebSocket stream"""

    MESSAGE_TYPES = {
        "agent_start": "Agent execution started",
        "agent_progress": "Agent processing",
        "agent_complete": "Agent completed",
        "tool_call": "Tool being called",
        "tool_result": "Tool result received",
        "error": "Error occurred",
        "suggestion": "Suggestion/recommendation",
        "clarification_needed": "Need user input",
        "status": "Status update",
        "reasoning": "Agent reasoning/explanation",
    }

    def __init__(self, message_type: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.type = message_type
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = datetime.now()

    def to_json(self) -> str:
        """Serialize to JSON for WebSocket transmission"""
        return json.dumps({
            "type": self.type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        })

    @staticmethod
    def from_json(data: str) -> "StreamMessage":
        """Deserialize from JSON"""
        parsed = json.loads(data)
        return StreamMessage(
            message_type=parsed["type"],
            content=parsed["content"],
            metadata=parsed.get("metadata", {}),
        )


class StreamingExecutor:
    """Wraps agent/tool execution with streaming capabilities"""

    def __init__(self, send_message_callback: Callable):
        """
        Initialize streaming executor.

        Args:
            send_message_callback: Async function(message: StreamMessage) to send updates
        """
        self.send_message = send_message_callback

    async def stream_agent_execution(
        self, agent_name: str, context: Dict[str, Any], execute_fn: Callable
    ) -> Dict[str, Any]:
        """
        Execute agent while streaming progress updates.

        Args:
            agent_name: Name of agent
            context: Execution context
            execute_fn: Async function that executes the agent
        """
        # Send start message
        await self.send_message(StreamMessage(
            message_type="agent_start",
            content=f"Starting agent: {agent_name}",
            metadata={"agent": agent_name},
        ))

        try:
            # Send reasoning/intent
            intent = context.get("user_prompt", "")[:100]
            await self.send_message(StreamMessage(
                message_type="reasoning",
                content=f"Processing request: {intent}",
                metadata={"step": "analysis"},
            ))

            # Execute agent
            await self.send_message(StreamMessage(
                message_type="agent_progress",
                content="Agent execution in progress...",
                metadata={"agent": agent_name, "status": "running"},
            ))

            result = await execute_fn(context)

            # Send completion
            await self.send_message(StreamMessage(
                message_type="agent_complete",
                content=f"Agent {agent_name} completed successfully",
                metadata={
                    "agent": agent_name,
                    "success": True,
                    "result_keys": list(result.keys()) if isinstance(result, dict) else [],
                },
            ))

            return result

        except Exception as e:
            # Send error
            await self.send_message(StreamMessage(
                message_type="error",
                content=f"Agent {agent_name} error: {str(e)}",
                metadata={"agent": agent_name, "error_type": type(e).__name__},
            ))
            raise

    async def stream_tool_execution(
        self, tool_name: str, input_params: Dict[str, Any], execute_fn: Callable
    ) -> Dict[str, Any]:
        """
        Execute tool while streaming updates.

        Args:
            tool_name: Name of tool
            input_params: Tool parameters
            execute_fn: Async function that executes the tool
        """
        # Send tool call
        await self.send_message(StreamMessage(
            message_type="tool_call",
            content=f"Calling tool: {tool_name}",
            metadata={
                "tool": tool_name,
                "params": str(input_params)[:100],
            },
        ))

        try:
            result = await execute_fn(input_params)

            # Stream partial results if available
            if isinstance(result, dict):
                for key, value in result.items():
                    if key != "data":  # Skip large data
                        await self.send_message(StreamMessage(
                            message_type="tool_result",
                            content=f"Tool result - {key}: {str(value)[:200]}",
                            metadata={"tool": tool_name, "result_key": key},
                        ))

            return result

        except Exception as e:
            await self.send_message(StreamMessage(
                message_type="error",
                content=f"Tool {tool_name} error: {str(e)}",
                metadata={"tool": tool_name, "error_type": type(e).__name__},
            ))
            raise

    async def stream_multi_agent_execution(
        self, agents: list, execute_fn: Callable
    ) -> Dict[str, Any]:
        """
        Execute multiple agents while streaming progress.

        Args:
            agents: List of agent configs
            execute_fn: Async function that executes agents
        """
        await self.send_message(StreamMessage(
            message_type="status",
            content=f"Executing {len(agents)} agents in sequence...",
            metadata={"total_agents": len(agents)},
        ))

        for i, agent_config in enumerate(agents):
            agent_name = agent_config.get("agent", "UnknownAgent")

            await self.send_message(StreamMessage(
                message_type="status",
                content=f"Agent {i + 1}/{len(agents)}: {agent_name}",
                metadata={
                    "current": i + 1,
                    "total": len(agents),
                    "agent": agent_name,
                },
            ))

        result = await execute_fn(agents)

        await self.send_message(StreamMessage(
            message_type="status",
            content=f"All {len(agents)} agents completed",
            metadata={"total_agents": len(agents), "success": True},
        ))

        return result


class WebSocketManager:
    """Manages WebSocket connections and message routing"""

    def __init__(self):
        self.connections: Dict[str, Any] = {}  # session_id -> websocket connection
        self.streaming_executors: Dict[str, StreamingExecutor] = {}

    async def connect(self, session_id: str, websocket: Any):
        """Register new WebSocket connection"""
        self.connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")

        # Create streaming executor for this session
        async def send_to_ws(message: StreamMessage):
            try:
                await websocket.send_text(message.to_json())
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {str(e)}")

        self.streaming_executors[session_id] = StreamingExecutor(send_to_ws)

    async def disconnect(self, session_id: str):
        """Deregister WebSocket connection"""
        if session_id in self.connections:
            del self.connections[session_id]
            if session_id in self.streaming_executors:
                del self.streaming_executors[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")

    async def broadcast_message(self, message: StreamMessage):
        """Send message to all connected clients"""
        for session_id, ws in list(self.connections.items()):
            try:
                await ws.send_text(message.to_json())
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {str(e)}")

    async def send_to_session(self, session_id: str, message: StreamMessage):
        """Send message to specific session"""
        if session_id in self.connections:
            try:
                await self.connections[session_id].send_text(message.to_json())
            except Exception as e:
                logger.error(f"Error sending to {session_id}: {str(e)}")

    def get_streaming_executor(self, session_id: str) -> Optional[StreamingExecutor]:
        """Get streaming executor for session"""
        return self.streaming_executors.get(session_id)

    async def send_clarification_needed(self, session_id: str, questions: list):
        """Send clarification request to user"""
        content = "I need clarification:\n" + "\n".join([f"- {q}" for q in questions])
        message = StreamMessage(
            message_type="clarification_needed",
            content=content,
            metadata={"questions_count": len(questions)},
        )
        await self.send_to_session(session_id, message)

    async def send_suggestion(self, session_id: str, suggestion: str, metadata: Optional[Dict] = None):
        """Send suggestion to user"""
        message = StreamMessage(
            message_type="suggestion",
            content=suggestion,
            metadata=metadata or {},
        )
        await self.send_to_session(session_id, message)

    def get_active_sessions(self) -> list:
        """Get list of active session IDs"""
        return list(self.connections.keys())

    def get_session_count(self) -> int:
        """Get number of active connections"""
        return len(self.connections)
