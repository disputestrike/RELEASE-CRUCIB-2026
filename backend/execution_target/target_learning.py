"""
Target Learning System
Tracks user choices and outcomes to improve auto-selection over time
"""

import json
from datetime import datetime
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class TargetLearningSystem:
    """
    Learns from user choices to improve confidence scores
    """
    
    def __init__(self):
        self.choice_history = []
        self.confidence_adjustments = {}
    
    def record_choice(
        self,
        job_id: str,
        user_request: str,
        suggested_target: str,
        user_choice: str,
        suggested_confidence: float,
        outcome: str  # "success", "failure", "partial"
    ) -> None:
        """
        Record a user choice and its outcome
        
        Args:
            job_id: Job ID
            user_request: Original user request
            suggested_target: What the system suggested
            user_choice: What the user actually chose
            suggested_confidence: Confidence score of suggestion
            outcome: Result of the choice
        """
        
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "job_id": job_id,
            "user_request": user_request,
            "suggested_target": suggested_target,
            "user_choice": user_choice,
            "suggested_confidence": suggested_confidence,
            "outcome": outcome,
            "correct": suggested_target == user_choice and outcome == "success"
        }
        
        self.choice_history.append(record)
        logger.info(f"Recorded choice: {user_choice} (suggestion: {suggested_target}, outcome: {outcome})")
        
        # Update confidence adjustments
        self._update_confidence_adjustments()
    
    def _update_confidence_adjustments(self) -> None:
        """
        Analyze choice history and adjust confidence scores
        """
        
        if len(self.choice_history) < 5:
            return  # Need minimum sample size
        
        # Group by suggested target
        by_target = {}
        for record in self.choice_history[-50:]:  # Last 50 choices
            target = record["suggested_target"]
            if target not in by_target:
                by_target[target] = {"correct": 0, "total": 0}
            
            by_target[target]["total"] += 1
            if record["correct"]:
                by_target[target]["correct"] += 1
        
        # Calculate adjustments
        for target, stats in by_target.items():
            accuracy = stats["correct"] / stats["total"]
            adjustment = (accuracy - 0.5) * 20  # Range: -10 to +10
            self.confidence_adjustments[target] = round(adjustment, 1)
            
            logger.info(f"Target {target}: {stats['correct']}/{stats['total']} correct (adjustment: {adjustment:+.1f})")
    
    def get_confidence_adjustment(self, target: str) -> float:
        """Get confidence adjustment for a target"""
        return self.confidence_adjustments.get(target, 0.0)
    
    def get_learning_stats(self) -> Dict:
        """Get overall learning statistics"""
        
        if not self.choice_history:
            return {
                "total_choices": 0,
                "accuracy": 0,
                "target_accuracies": {}
            }
        
        total = len(self.choice_history)
        correct = sum(1 for r in self.choice_history if r["correct"])
        
        # Per-target accuracy
        by_target = {}
        for record in self.choice_history:
            target = record["suggested_target"]
            if target not in by_target:
                by_target[target] = {"correct": 0, "total": 0}
            by_target[target]["total"] += 1
            if record["correct"]:
                by_target[target]["correct"] += 1
        
        target_accuracies = {
            target: (stats["correct"] / stats["total"]) * 100
            for target, stats in by_target.items()
        }
        
        return {
            "total_choices": total,
            "accuracy": (correct / total) * 100,
            "target_accuracies": target_accuracies,
            "confidence_adjustments": self.confidence_adjustments
        }

