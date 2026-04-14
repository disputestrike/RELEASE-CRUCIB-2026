"""
Context Manager: Manages conversation state, multi-turn interactions, and memory.
Implements sliding window memory, conversation history, and context enrichment.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConversationTurn:
    """Represents a single user-agent exchange"""

    def __init__(self, user_input: str, agent_response: str, metadata: Optional[Dict[str, Any]] = None):
        self.user_input = user_input
        self.agent_response = agent_response
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
        self.tokens_used = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user": self.user_input,
            "response": self.agent_response,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "tokens_used": self.tokens_used,
        }


class ContextManager:
    """
    Manages conversation context, memory, and multi-turn interactions.
    Like I do: maintains conversation state, remembers previous exchanges,
    and enriches new requests with relevant history.
    """

    def __init__(self, max_history: int = 20, max_context_tokens: int = 4000, db: Optional[Any] = None):
        """
        Initialize context manager.

        Args:
            max_history: Maximum number of turns to keep in memory
            max_context_tokens: Maximum tokens to include in context window
            db: Optional database for persistence
        """
        self.max_history = max_history
        self.max_context_tokens = max_context_tokens
        self.db = db
        self.sessions: Dict[str, "ConversationSession"] = {}

    def create_session(self, session_id: str, user_id: str = "anonymous") -> "ConversationSession":
        """Create new conversation session"""
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            max_history=self.max_history,
            max_context_tokens=self.max_context_tokens,
        )
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional["ConversationSession"]:
        """Retrieve existing session"""
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False


class ConversationSession:
    """Single conversation session with memory and context"""

    def __init__(
        self,
        session_id: str,
        user_id: str = "anonymous",
        max_history: int = 20,
        max_context_tokens: int = 4000,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.turns: List[ConversationTurn] = []
        self.max_history = max_history
        self.max_context_tokens = max_context_tokens
        self.metadata = {}
        self.keywords: List[str] = []  # Track important concepts
        self.current_task = None

    def add_turn(self, user_input: str, agent_response: str, metadata: Optional[Dict[str, Any]] = None):
        """Add exchange to conversation history"""
        turn = ConversationTurn(user_input, agent_response, metadata)
        self.turns.append(turn)
        self.last_activity = datetime.now()

        # Maintain max history size
        if len(self.turns) > self.max_history:
            self.turns = self.turns[-self.max_history:]

        # Extract keywords
        self._extract_keywords(user_input)

    def get_context_window(self, max_tokens: Optional[int] = None) -> str:
        """
        Get sliding window of conversation context.
        Includes recent exchanges that fit within token budget.
        """
        max_tokens = max_tokens or self.max_context_tokens
        context_parts = []
        current_tokens = 0

        # Include from most recent backwards
        for turn in reversed(self.turns):
            turn_text = f"User: {turn.user_input}\nAssistant: {turn.agent_response}"
            turn_tokens = len(turn_text.split())  # Rough estimate

            if current_tokens + turn_tokens <= max_tokens:
                context_parts.insert(0, turn_text)
                current_tokens += turn_tokens
            else:
                break

        return "\n\n".join(context_parts)

    def get_relevant_history(self, query: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """
        Find relevant past exchanges using keyword matching.
        Like semantic search but using simple keywords.
        """
        query_words = query.lower().split()
        scored_turns = []

        for turn in self.turns:
            score = 0
            text = (turn.user_input + " " + turn.agent_response).lower()

            for word in query_words:
                if word in text:
                    score += 1

            if score > 0:
                scored_turns.append((turn, score))

        # Sort by relevance score, desc
        scored_turns.sort(key=lambda x: x[1], reverse=True)
        return [turn.to_dict() for turn, _ in scored_turns[:max_results]]

    def set_current_task(self, task_description: str, task_metadata: Optional[Dict[str, Any]] = None):
        """Set current task being worked on"""
        self.current_task = {
            "description": task_description,
            "started_at": datetime.now(),
            "metadata": task_metadata or {},
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of session"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "turn_count": len(self.turns),
            "keywords": self.keywords,
            "current_task": self.current_task,
            "duration_seconds": (datetime.now() - self.created_at).total_seconds(),
        }

    def get_history_json(self, include_metadata: bool = False) -> str:
        """Export conversation history as JSON"""
        turns_data = []
        for turn in self.turns:
            turn_dict = {
                "user": turn.user_input,
                "assistant": turn.agent_response,
                "timestamp": turn.timestamp.isoformat(),
            }
            if include_metadata:
                turn_dict["metadata"] = turn.metadata
                turn_dict["tokens_used"] = turn.tokens_used

            turns_data.append(turn_dict)

        return json.dumps({
            "session_id": self.session_id,
            "user_id": self.user_id,
            "turns": turns_data,
            "summary": self.get_summary(),
        }, indent=2)

    def clear_history(self):
        """Clear conversation history (keep metadata)"""
        self.turns.clear()
        self.last_activity = datetime.now()

    def _extract_keywords(self, text: str):
        """Extract important keywords from user input"""
        # Simple keyword extraction (can be enhanced with NLP)
        stop_words = {"the", "a", "an", "and", "or", "but", "is", "are", "be", "have", "do", "will", "can"}
        words = text.lower().split()
        new_keywords = [w for w in words if len(w) > 3 and w not in stop_words]

        for keyword in new_keywords:
            if keyword not in self.keywords:
                self.keywords.append(keyword)

        # Keep only last 20 keywords
        self.keywords = self.keywords[-20:]

    def get_context_enrichment(self) -> Dict[str, Any]:
        """
        Get enriched context for new agent request.
        Like how I maintain awareness of conversation state.
        """
        return {
            "session_id": self.session_id,
            "turn_number": len(self.turns),
            "recent_context": self.get_context_window(),
            "relevant_history": self.get_relevant_history(""),  # Empty query returns all recent
            "keywords": self.keywords,
            "current_task": self.current_task,
            "session_duration_seconds": (datetime.now() - self.created_at).total_seconds(),
        }


class ContextEnricher:
    """Enriches agent requests with conversation context"""

    @staticmethod
    def enrich_request(context: Dict[str, Any], session: Optional[ConversationSession]) -> Dict[str, Any]:
        """Add session context to agent request"""
        if not session:
            return context

        enriched = context.copy()
        enriched["conversation_context"] = session.get_context_enrichment()

        # Add relevant history as references
        if session.turns:
            enriched["previous_exchanges"] = session.get_relevant_history(
                context.get("user_prompt", "")
            )

        # Add session keywords as hints
        if session.keywords:
            enriched["detected_topics"] = session.keywords

        return enriched

    @staticmethod
    def extract_clarifying_questions(context: Dict[str, Any], session: Optional[ConversationSession]) -> List[str]:
        """Identify what needs clarification from context"""
        questions = []

        # If request is too vague
        if "user_prompt" in context:
            prompt = context["user_prompt"]
            if len(prompt) < 20:
                questions.append("Could you provide more details about what you're trying to achieve?")

        # If no relevant history found
        if session and len(session.turns) > 0 and not session.get_relevant_history(context.get("user_prompt", "")):
            questions.append("Is this related to your previous work, or a completely new task?")

        # If current task not set
        if session and not session.current_task:
            questions.append("What's the main objective you're working on?")

        return questions
