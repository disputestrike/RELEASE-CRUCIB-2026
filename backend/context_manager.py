"""
Context Manager: Intelligent context handling with smart summarization.
"""

import logging
from typing import Dict, Any, List
import json

logger = logging.getLogger(__name__)

# Increased from 2000 to 5000 for better context preservation
MAX_CONTEXT_CHARS = 5000
KEY_INFO_CHARS = 1000  # Reserve for key information


class ContextManager:
    """Manages context between agents with smart summarization."""
    
    @staticmethod
    def extract_key_info(output: str, agent_name: str) -> str:
        """
        Extract key information from agent output.
        
        Returns: Summarized key information
        """
        if not output:
            return ""
        
        # Agent-specific key extraction
        if agent_name == "Planner":
            # Extract task list
            lines = output.split('\n')
            tasks = [l for l in lines if l.strip() and l[0].isdigit()]
            return '\n'.join(tasks[:7])  # Max 7 tasks
        
        elif agent_name == "Stack Selector":
            # Extract tech stack
            try:
                data = json.loads(output)
                summary = f"Frontend: {data.get('frontend', {}).get('framework', 'N/A')}\n"
                summary += f"Backend: {data.get('backend', {}).get('framework', 'N/A')}\n"
                summary += f"Database: {data.get('database', {}).get('type', 'N/A')}"
                return summary
            except:
                return output[:KEY_INFO_CHARS]
        
        elif agent_name == "Design Agent":
            # Extract design system colors
            try:
                data = json.loads(output)
                colors = data.get('design_system', {}).get('colors', {})
                summary = "Design Colors:\n"
                for color_name, color_value in list(colors.items())[:5]:
                    summary += f"  {color_name}: {color_value}\n"
                return summary
            except:
                return output[:KEY_INFO_CHARS]
        
        elif agent_name in ["Frontend Generation", "Backend Generation"]:
            # Extract first 500 chars of code
            lines = output.split('\n')
            code_lines = [l for l in lines if l.strip()][:10]
            return '\n'.join(code_lines)
        
        elif agent_name == "Database Agent":
            # Extract table names
            lines = output.split('\n')
            tables = [l for l in lines if 'CREATE TABLE' in l]
            return '\n'.join(tables[:5])
        
        else:
            # Default: first KEY_INFO_CHARS
            return output[:KEY_INFO_CHARS]
    
    @staticmethod
    def build_context_for_agent(
        agent_name: str,
        previous_outputs: Dict[str, Any],
        project_prompt: str
    ) -> str:
        """
        Build context string for an agent from previous outputs.
        
        Returns: Context string with smart summarization
        """
        parts = []
        current_chars = 0
        
        # Always include project prompt
        parts.append(f"Project Request:\n{project_prompt[:500]}")
        current_chars += len(project_prompt[:500])
        
        # Add relevant previous outputs based on agent
        if agent_name in ["Frontend Generation", "Backend Generation", "Database Agent"]:
            if "Stack Selector" in previous_outputs:
                output = previous_outputs["Stack Selector"].get("output", "")
                if output and current_chars < MAX_CONTEXT_CHARS:
                    key_info = ContextManager.extract_key_info(output, "Stack Selector")
                    parts.append(f"\nTech Stack Selected:\n{key_info}")
                    current_chars += len(key_info)
        
        if agent_name in ["Security Checker", "UX Auditor", "Performance Analyzer"]:
            if "Frontend Generation" in previous_outputs:
                output = previous_outputs["Frontend Generation"].get("output", "")
                if output and current_chars < MAX_CONTEXT_CHARS:
                    key_info = ContextManager.extract_key_info(output, "Frontend Generation")
                    parts.append(f"\nGenerated Frontend (excerpt):\n{key_info}")
                    current_chars += len(key_info)
        
        if agent_name in ["Image Generation", "Layout Agent"]:
            if "Design Agent" in previous_outputs:
                output = previous_outputs["Design Agent"].get("output", "")
                if output and current_chars < MAX_CONTEXT_CHARS:
                    key_info = ContextManager.extract_key_info(output, "Design Agent")
                    parts.append(f"\nDesign Specifications:\n{key_info}")
                    current_chars += len(key_info)
        
        if agent_name == "Layout Agent":
            if "Image Generation" in previous_outputs:
                output = previous_outputs["Image Generation"].get("output", "")
                if output and current_chars < MAX_CONTEXT_CHARS:
                    parts.append(f"\nImage Prompts Generated:\n{output[:500]}")
                    current_chars += len(output[:500])
        
        if agent_name == "Test Generation":
            if "Backend Generation" in previous_outputs:
                output = previous_outputs["Backend Generation"].get("output", "")
                if output and current_chars < MAX_CONTEXT_CHARS:
                    key_info = ContextManager.extract_key_info(output, "Backend Generation")
                    parts.append(f"\nBackend Code to Test:\n{key_info}")
                    current_chars += len(key_info)
        
        # Ensure we don't exceed max context
        context = '\n'.join(parts)
        if len(context) > MAX_CONTEXT_CHARS:
            context = context[:MAX_CONTEXT_CHARS] + "\n... (context truncated)"
        
        return context
    
    @staticmethod
    def summarize_output(output: str, max_length: int = 500) -> str:
        """
        Summarize agent output for storage/display.
        
        Returns: Summarized output
        """
        if len(output) <= max_length:
            return output
        
        # Try to keep complete lines
        lines = output.split('\n')
        summary = []
        current_length = 0
        
        for line in lines:
            if current_length + len(line) + 1 <= max_length:
                summary.append(line)
                current_length += len(line) + 1
            else:
                break
        
        return '\n'.join(summary) + f"\n... ({len(output) - current_length} chars truncated)"
    
    @staticmethod
    def get_context_stats(previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get statistics about context usage.
        
        Returns: {
            "total_outputs": int,
            "total_chars": int,
            "avg_output_size": int,
            "largest_output": str,
            "largest_output_size": int
        }
        """
        total_outputs = len(previous_outputs)
        total_chars = 0
        largest_output = None
        largest_size = 0
        
        for agent_name, output_data in previous_outputs.items():
            output = output_data.get("output", "")
            output_size = len(output)
            total_chars += output_size
            
            if output_size > largest_size:
                largest_size = output_size
                largest_output = agent_name
        
        return {
            "total_outputs": total_outputs,
            "total_chars": total_chars,
            "avg_output_size": total_chars // total_outputs if total_outputs > 0 else 0,
            "largest_output": largest_output,
            "largest_output_size": largest_size,
            "max_context_available": MAX_CONTEXT_CHARS
        }
