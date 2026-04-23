'''
Clarification Agent: Detects ambiguity and asks intelligent follow-up questions.
Like when I need more info to give you the best help (like Copilot).
'''

import json
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agents.base_agent import AgentValidationError, BaseAgent
from agents.registry import AgentRegistry

logger = logging.getLogger(__name__)


class IntentSchema(BaseModel):
    goal: str = Field(..., description="The primary goal extracted from the user's prompt.")
    constraints: List[str] = Field(default_factory=list, description="List of constraints identified in the prompt.")
    risk_level: int = Field(..., ge=1, le=5, description="Assessed risk level of the task (1-5, 5 being highest).")
    required_tools: List[str] = Field(default_factory=list, description="List of tools identified as necessary for the task.")


@AgentRegistry.register
class ClarificationAgent(BaseAgent):
    '''
    Asks clarifying questions when request is ambiguous or incomplete.

    Input:
        - user_prompt: str (the original user request)
        - context: dict (optional context about workspace/previous messages)
        - previous_attempts: list (optional failed attempts)

    Output:
        - needs_clarification: bool
        - clarifying_questions: list of specific questions
        - assumptions_made: list of assumptions
        - confidence_score: float (0-1, how confident we are about the request)
        - intent_schema: IntentSchema (structured representation of the user's intent)
    '''

    def __init__(self, llm_client: Optional[Any] = None, config: Optional[Dict[str, Any]] = None, db: Optional[Any] = None):
        super().__init__(llm_client=llm_client, config=config, db=db)
        self.name = "ClarificationAgent"

    def validate_input(self, context: Dict[str, Any]) -> bool:
        super().validate_input(context)

        if "user_prompt" not in context:
            raise AgentValidationError(f"{self.name}: Missing required field 'user_prompt'")

        prompt = context["user_prompt"]
        if not isinstance(prompt, str) or len(prompt) < 3:
            raise AgentValidationError(f"{self.name}: user_prompt must be string with >3 chars")

        return True

    def validate_output(self, result: Dict[str, Any]) -> bool:
        super().validate_output(result)
        required = ["needs_clarification", "clarifying_questions", "confidence_score", "intent_schema"]
        for field in required:
            if field not in result:
                raise AgentValidationError(f"{self.name}: Missing output field '{field}'")

        if not isinstance(result["confidence_score"], (int, float)) or not (0 <= result["confidence_score"] <= 1):
            raise AgentValidationError(f"{self.name}: confidence_score must be 0-1")

        return True

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        '''Execute clarification analysis'''
        user_prompt = context["user_prompt"]
        workspace_info = context.get("context", {})
        previous_attempts = context.get("previous_attempts", [])

        try:
            # Analyze prompt for ambiguity
            ambiguity_score = self._assess_ambiguity(user_prompt)
            confidence = 1.0 - ambiguity_score

            # Extract what we understand
            understood_info = self._extract_understood_info(user_prompt)

            # Identify gaps
            missing_info = self._identify_missing_info(user_prompt, understood_info)

            # Generate targeted questions
            questions = self._generate_questions(missing_info, understood_info)

            # Track assumptions
            assumptions = self._identify_assumptions(user_prompt, understood_info)

            result = {
                "needs_clarification": ambiguity_score > 0.3,  # Threshold
                "confidence_score": confidence,
                "ambiguity_score": ambiguity_score,
                "understood": understood_info,
                "missing_info": missing_info,
                "clarifying_questions": questions,
                "assumptions_made": assumptions,
                "recommendation": self._get_recommendation(ambiguity_score, questions),
                "intent_schema": self._build_intent_schema(user_prompt, understood_info, ambiguity_score),
            }

            if self.performance:
                self.performance.track_execution(
                    self.name,
                    "success",
                    len(user_prompt),
                )

            return result

        except Exception as e:
            logger.error(f"{self.name} execution error: {str(e)}")
            if self.performance:
                self.performance.track_execution(self.name, "error", 0)
            raise

    def _assess_ambiguity(self, prompt: str) -> float:
        '''
        Score ambiguity from 0 (crystal clear) to 1 (completely ambiguous).
        '''
        score = 0.0

        # 1. Length heuristic - too short is usually vague
        if len(prompt) < 20:
            score += 0.3
        elif len(prompt) < 50:
            score += 0.15

        # 2. Specificity indicators
        vague_words = [
            "something",
            "thing",
            "stuff",
            "maybe",
            "probably",
            "sort of",
            "about",
            "basically",
            "like",
        ]
        vague_count = sum(1 for word in vague_words if word in prompt.lower())
        score += min(0.2, vague_count * 0.05)

        # 3. Question indicators (questions can be ambiguous too)
        if prompt.endswith("?"):
            # Questions can be clear or vague
            if self._count_specificity_keywords(prompt) < 2:
                score += 0.2

        # 4. Missing context indicators
        missing_context_phrases = [
            "this code",
            "that file",
            "the project",
            "it",
            "they",
        ]
        missing_context_count = sum(
            1 for phrase in missing_context_phrases if phrase in prompt.lower()
        )
        score += min(0.15, missing_context_count * 0.05)

        # 5. Multiple interpretations
        interpretable_words = ["build", "generate", "create", "fix", "improve"]
        multi_interp_count = sum(1 for word in interpretable_words if word in prompt.lower())
        if multi_interp_count > 1:
            score += 0.1

        return min(1.0, score)

    def _build_intent_schema(self, user_prompt: str, understood_info: Dict[str, Any], ambiguity_score: float) -> IntentSchema:
        goal = user_prompt # Simple for now, can be refined
        constraints = understood_info["constraints"]
        risk_level = self._derive_risk_level(ambiguity_score)
        required_tools = self._derive_required_tools(understood_info["actions"])

        return IntentSchema(
            goal=goal,
            constraints=constraints,
            risk_level=risk_level,
            required_tools=required_tools,
        )

    def _derive_risk_level(self, ambiguity_score: float) -> int:
        if ambiguity_score < 0.2:
            return 1
        elif ambiguity_score < 0.4:
            return 2
        elif ambiguity_score < 0.6:
            return 3
        elif ambiguity_score < 0.8:
            return 4
        else:
            return 5

    def _derive_required_tools(self, actions: List[str]) -> List[str]:
        tool_mapping = {
            "code_analysis": "code_analyzer",
            "code_review": "code_reviewer",
            "testing": "test_runner",
            "debugging": "debugger",
            "code_generation": "code_generator",
            "building": "builder",
            "deployment": "deployer",
            "refactoring": "refactor_tool",
            "optimization": "optimizer",
            "bug_fixing": "bug_fixer",
            "search": "search_tool",
            "execution": "executor",
        }
        return [tool_mapping[action] for action in actions if action in tool_mapping]

    def _extract_understood_info(self, prompt: str) -> Dict[str, Any]:
        '''Extract what we clearly understand from the prompt'''
        understood = {
            "actions": [],
            "targets": [],
            "constraints": [],
            "context": [],
        }

        prompt_lower = prompt.lower()

        # Detect action verbs
        action_keywords = {
            "analyze": "code_analysis",
            "review": "code_review",
            "test": "testing",
            "debug": "debugging",
            "generate": "code_generation",
            "build": "building",
            "deploy": "deployment",
            "refactor": "refactoring",
            "optimize": "optimization",
            "fix": "bug_fixing",
            "search": "search",
            "find": "search",
            "run": "execution",
        }

        for keyword, action in action_keywords.items():
            if keyword in prompt_lower:
                understood["actions"].append(action)

        # Detect targets
        target_keywords = {
            "code": "source_code",
            "function": "function",
            "class": "class",
            "module": "module",
            "api": "api",
            "endpoint": "endpoint",
            "database": "database",
            "test": "test",
            "frontend": "frontend",
            "backend": "backend",
        }

        for keyword, target in target_keywords.items():
            if keyword in prompt_lower:
                understood["targets"].append(target)

        # Detect constraints
        if "not" in prompt_lower or "don't" in prompt_lower:
            understood["constraints"].append("has_negation")
        if "must" in prompt_lower or "should" in prompt_lower:
            understood["constraints"].append("has_requirements")

        return understood

    def _identify_missing_info(self, prompt: str, understood: Dict[str, Any]) -> List[Dict[str, str]]:
        '''Identify what information we're missing'''
        missing = []

        # Check actions
        if not understood["actions"]:
            missing.append({
                "category": "action",
                "description": "What do you want to do?",
                "examples": "analyze, review, test, debug, generate, build, deploy...",
            })

        # Check targets
        if not understood["targets"]:
            missing.append({
                "category": "target",
                "description": "What should I work on?",
                "examples": "code, function, API, database, test file...",
            })

        # Context about scope
        if "this" in prompt or "that" in prompt or "the" in prompt:
            if len([w for w in prompt.split() if w in ["this", "that", "the"]]) > 2:
                missing.append({
                    "category": "context",
                    "description": "Can you specify which files or functions?",
                    "examples": "src/handler.ts, backend/auth.py, etc.",
                })

        # Specific requirements
        if "improve" in prompt.lower() or "better" in prompt.lower():
            missing.append({
                "category": "criteria",
                "description": "What criteria should I optimize for?",
                "examples": "performance, readability, security, maintainability...",
            })

        return missing

    def _generate_questions(self, missing_info: List[Dict[str, str]], understood: Dict[str, Any]) -> List[str]:
        '''Generate specific clarifying questions'''
        questions = []

        for item in missing_info:
            questions.append(item["description"])

        # Add context-specific questions
        if "code_analysis" in understood["actions"] and not understood["targets"]:
            questions.append("Is this about Python, JavaScript, or another language?")

        if "testing" in understood["actions"]:
            questions.append("Do you want unit tests, integration tests, or end-to-end tests?")

        if "optimization" in understood["actions"]:
            questions.append("Should I prioritize speed, memory, or code readability?")

        # Limit to 4-5 most important
        return questions[:5]

    def _identify_assumptions(self, prompt: str, understood: Dict[str, Any]) -> List[str]:
        '''Track assumptions we're making'''
        assumptions = []

        if len(prompt) < 30:
            assumptions.append("Assuming simple, focused task due to brief description")

        if not understood["constraints"]:
            assumptions.append("Assuming no special constraints or requirements")

        if understood["actions"] and not understood["targets"]:
            assumptions.append(f"Need context - will apply {understood['actions'][0]} to most likely target")

        if "this" in prompt and not understood["context"]:
            assumptions.append("'This' refers to current workspace/file (need more specifics)")

        return assumptions

    def _count_specificity_keywords(self, text: str) -> int:
        '''Count how many specific/concrete keywords are in the text'''
        specific_keywords = [
            "file",
            "class",
            "function",
            "method",
            "endpoint",
            "route",
            "line",
            "module",
            "package",
        ]
        return sum(1 for keyword in specific_keywords if keyword in text.lower())

    def _get_recommendation(self, ambiguity_score: float, questions: List[str]) -> str:
        '''Get recommendation on how to proceed'''
        if ambiguity_score < 0.2:
            return "Very clear request - proceed with execution immediately"
        elif ambiguity_score < 0.4:
            return f"Request is clear enough - proceed but note: {questions[0] if questions else 'none'}"
        elif ambiguity_score < 0.7:
            return f"Ask {len(questions)} clarifying question(s) before proceeding"
        else:
            return "Request is too ambiguous - need significant clarification before execution"
