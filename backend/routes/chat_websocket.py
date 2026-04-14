"""
WebSocket chat endpoint for real-time streaming interactions.
Handles agent execution with live updates flowing to the frontend.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
import asyncio
import json
import logging
from typing import Dict, Any

from services.brain_layer import BrainLayer
from services.conversation_manager import ContextManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["websocket"])

context_manager = ContextManager()
ws_manager = None


@router.websocket("/ws/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat with streaming agent responses.
    
    Flow:
    1. Client connects via WebSocket
    2. Client sends message
    3. Server routes to agents and streams updates back
    4. Client receives real-time progress updates
    """
    await websocket.accept()
    
    try:
        # Register connection
        if ws_manager:
            await ws_manager.connect(session_id, websocket)
            logger.info(f"WebSocket connected: {session_id}")

        while True:
            # Wait for message from client
            raw_message = await websocket.receive_text()
            
            try:
                message_data = json.loads(raw_message)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Invalid JSON format",
                    "timestamp": asyncio.get_event_loop().time(),
                })
                continue

            user_message = message_data.get("message", "")
            if not user_message:
                await websocket.send_json({
                    "type": "error",
                    "content": "Empty message",
                })
                continue

            # Stream processing of message
            await process_message_streaming(session_id, user_message, websocket)

    except WebSocketDisconnect:
        if ws_manager:
            await ws_manager.disconnect(session_id)
        logger.info(f"WebSocket disconnected: {session_id}")

    except Exception as e:
        logger.error(f"WebSocket error for {session_id}: {str(e)}")
        try:
            await websocket.send_json({
                "type": "error",
                "content": f"Server error: {str(e)}",
            })
        except Exception:
            pass
        if ws_manager:
            await ws_manager.disconnect(session_id)


async def process_message_streaming(session_id: str, user_message: str, websocket: WebSocket):
    """
    Process message and stream responses to the WebSocket client.
    This is where the magic happens - real-time agent execution feedback.
    """
    try:
        session = context_manager.get_session(session_id)
        if not session:
            session = context_manager.create_session(session_id)

        brain = BrainLayer()

        async def send_progress(event: Dict[str, Any]):
            await websocket.send_json({
                "type": event.get("type", "status"),
                "content": event.get("content", ""),
                "metadata": event.get("metadata", {}),
            })

        await websocket.send_json({
            "type": "status",
            "content": "I’m thinking through your request and choosing the smallest focused plan.",
            "metadata": {
                "session_id": session_id,
            },
        })

        brain_result = await brain.execute_request(
            session,
            user_message,
            progress_callback=send_progress,
        )

        if brain_result.get("status") == "clarification_required":
            await websocket.send_json({
                "type": "clarification",
                "content": brain_result.get("assistant_response"),
                "metadata": {
                    "reason": "needs_more_detail",
                },
            })
            return

        await websocket.send_json({
            "type": "final_response",
            "content": brain_result.get("assistant_response"),
            "metadata": {
                "selected_agents": brain_result.get("selected_agents"),
                "intent": brain_result.get("intent"),
                "status": brain_result.get("status"),
                "execution": brain_result.get("execution"),
            },
        })

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "content": f"Error: {str(e)}",
        })


@router.post("/ws/test")
async def websocket_test_page():
    """
    Serve an HTML page for testing WebSocket chat.
    Useful for quick testing without building full frontend.
    """
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>CrucibAI Chat Test</title>
        <style>
            body { font-family: monospace; max-width: 800px; margin: 50px auto; }
            .chat-container { border: 1px solid #ccc; height: 400px; overflow-y: auto; padding: 10px; background: #f5f5f5; margin-bottom: 20px; }
            .message { margin: 10px 0; padding: 8px; background: white; border-radius: 4px; }
            .message.user { background: #e3f2fd; }
            .message.system { background: #f3e5f5; font-style: italic; }
            .input-area { display: flex; gap: 10px; }
            input[type="text"] { flex: 1; padding: 10px; }
            button { padding: 10px 20px; background: #1976d2; color: white; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background: #1565c0; }
        </style>
    </head>
    <body>
        <h1>🧠 CrucibAI WebSocket Chat</h1>
        <div class="chat-container" id="messages"></div>
        <div class="input-area">
            <input type="text" id="messageInput" placeholder="Ask me anything..." autofocus/>
            <button onclick="sendMessage()">Send</button>
        </div>

        <script>
            const sessionId = 'session_' + Math.random().toString(36).substring(7);
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const ws = new WebSocket(protocol + '//' + window.location.host + '/api/chat/ws/' + sessionId);

            ws.onopen = () => {
                addMessage('System', 'Connected to CrucibAI Copilot', 'system');
            };

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                addMessage(msg.type.toUpperCase(), msg.content, msg.type);
            };

            ws.onerror = (error) => {
                addMessage('Error', 'WebSocket error: ' + error, 'error');
            };

            ws.onclose = () => {
                addMessage('System', 'Disconnected', 'system');
            };

            function sendMessage() {
                const input = document.getElementById('messageInput');
                const message = input.value.trim();
                
                if (!message) return;
                
                addMessage('You', message, 'user');
                
                ws.send(JSON.stringify({
                    type: 'message',
                    message: message,
                    timestamp: new Date().toISOString()
                }));
                
                input.value = '';
            }

            function addMessage(sender, text, type) {
                const messagesDiv = document.getElementById('messages');
                const msg = document.createElement('div');
                msg.className = 'message ' + type;
                msg.innerHTML = '<strong>' + sender + ':</strong> ' + escapeHtml(text);
                messagesDiv.appendChild(msg);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }

            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            document.getElementById('messageInput').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') sendMessage();
            });
        </script>
    </body>
    </html>
    """)
