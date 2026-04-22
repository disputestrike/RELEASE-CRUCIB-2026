"""
output_validator.py — Validate generated output against specifications
"""

import logging
from typing import Any, Dict, List, Optional

from backend.services.intent_extractor import IntentExtractor

logger = logging.getLogger(__name__)


class OutputValidator:
    """Validate generated code against user specifications."""
    
    @staticmethod
    async def validate_against_spec(
        generated_code: str,
        specification: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate that generated code matches the original specification.
        
        Args:
            generated_code: The generated code to validate
            specification: The project specification from build start
        
        Returns:
            Validation report
        """
        if not specification:
            return {
                "is_valid": True,
                "reason": "No specification to validate against",
                "constraints_met": [],
                "constraints_violated": [],
                "confidence": 0.0,
            }
        
        constraints = specification.get("constraints", {})
        
        # Use IntentExtractor to validate code against constraints
        validation = await IntentExtractor.validate_code_matches_intent(
            generated_code,
            constraints,
        )
        
        # Add metadata
        validation["specification_id"] = specification.get("id")
        validation["timestamp"] = specification.get("timestamp")
        validation["original_prompt"] = specification.get("original_prompt", "")
        
        return validation
    
    @staticmethod
    async def generate_validation_report(
        project_id: str,
        validation_result: Dict[str, Any],
    ) -> str:
        """Generate a human-readable validation report."""
        
        is_valid = validation_result.get("is_valid", False)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        
        report_lines = [
            f"Validation Report for {project_id}",
            f"Status: {status}",
            f"Confidence: {validation_result.get('confidence', 0):.1%}",
            "",
        ]
        
        if validation_result.get("constraints_met"):
            report_lines.append("✅ Constraints Met:")
            for constraint in validation_result.get("constraints_met", []):
                report_lines.append(f"  • {constraint}")
            report_lines.append("")
        
        if validation_result.get("constraints_violated"):
            report_lines.append("❌ Constraints Violated:")
            for constraint in validation_result.get("constraints_violated", []):
                report_lines.append(f"  • {constraint}")
            report_lines.append("")
        
        if validation_result.get("reason"):
            report_lines.append(f"Note: {validation_result['reason']}")
        
        return "\n".join(report_lines)
